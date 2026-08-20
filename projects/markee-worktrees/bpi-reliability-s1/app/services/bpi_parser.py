"""BPI PDF parser — extracts lifecycle events from the Boletim da Propriedade Industrial.

The BPI is published daily by INPI Portugal. This module supports:

- downloading the most recent bulletin PDF;
- text extraction via ``pdfplumber`` with a ``pymupdf`` (fitz) fallback;
- normalisation of events: publication, grant, provisional refusal, opposition,
  renewal, lapse, transfer and change of name;
- provenance: every event carries its page number, a source excerpt and an
  extraction confidence score;
- archival of the bulletin PDF into ``core.documents`` (checksum-deduplicated).
"""
from __future__ import annotations

import hashlib
import io
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import fitz  # pymupdf
import httpx
import pdfplumber
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document
from app.services.confidence import score_bpi_event

logger = logging.getLogger(__name__)

BPI_BASE_URL = "https://inpi.justica.gov.pt/en-gb/Industrial-Property-Bulletin"
BPI_LISTING_URL = (
    "https://inpi.justica.gov.pt/en-gb/Industrial-Property-Bulletin/Daily-bulletins"
)


@dataclass
class BPIEvent:
    """A normalised event extracted from a BPI PDF."""

    event_type: str
    event_date: date | None
    application_number: str
    description: str
    source: str = "BPI"
    raw_text: str = ""
    # Provenance inside the bulletin.
    page_number: int | None = None
    source_excerpt: str = ""
    # Extraction confidence in [0, 1].
    confidence_score: float = 1.0


class BPIParser:
    """Parse daily BPI PDFs into structured lifecycle events."""

    # Regex patterns for the Portuguese BPI sections.
    #
    # The application-number pattern is whitespace-tolerant because INPI
    # publishes PT process numbers with internal whitespace inside the digit
    # block (``Processo: 770 255``, ``N.º 770 255``) and with an ``n.º`` /
    # ``nº`` abbreviation prefix (``Processo n.º 770 255``). The captured
    # group therefore matches an optional ``N.`` prefix and an optional
    # ``n.º`` separator, followed by one or more whitespace-separated digit
    # groups. The capture is normalised in
    # :meth:`_normalise_application_number` to the canonical whitespace-free
    # form documented in ``docs/research/BPI_DATA_CONTRACT.md``
    # (``process_number='770255'``).
    RE_APPLICATION = re.compile(
        r"(?:N[º°]\s*de\s*pedido|N[º°]\.?\s*Pedido|Application\s*No|Processo)"
        r"(?:\s+n\.[º°]?\s*)?[\s:]*((?:N\.\s*)?\d+(?:\s+\d+)*)",
        re.IGNORECASE,
    )
    RE_PUBLICATION = re.compile(
        r"(?:Publicação|Despacho\s*de\s*Publicação|Publicação\s*do\s*pedido|Despacho\s*n\.?\s*\d+)",
        re.IGNORECASE,
    )
    RE_REFUSAL = re.compile(
        r"(?:Recusa\s*[Pp]rovisória|Recusa|Recusa\s*absoluta|Recusa\s*relativa)",
        re.IGNORECASE,
    )
    RE_OPPOSITION = re.compile(
        r"(?:Oposição|Contestação|Oposição\s*apresentada)",
        re.IGNORECASE,
    )
    RE_RENEWAL = re.compile(
        r"(?:Renovação|Pagamento\s*da\s*anuidade|Pagamento\s*de\s*taxa)",
        re.IGNORECASE,
    )
    RE_LAPSE = re.compile(
        r"(?:Caducidade|Extinção|Caducidade\s*declarada|Extinção\s*de\s*registo)",
        re.IGNORECASE,
    )
    RE_TRANSFER = re.compile(
        r"(?:Transmissão|Cessão|Alteração\s*de\s*titular)",
        re.IGNORECASE,
    )
    RE_CHANGE_NAME = re.compile(
        r"(?:Alteração\s*de\s*denominação|Mudança\s*de\s*nome|Alteração\s*de\s*nome)",
        re.IGNORECASE,
    )
    RE_GRANT = re.compile(
        r"(?:Concessão|Registo\s*concedido|Concessão\s*do\s*registo)",
        re.IGNORECASE,
    )

    # (pattern, event_type) pairs applied to every page.
    _SECTION_PATTERNS: tuple[tuple[str, str], ...] = (
        ("RE_PUBLICATION", "publication"),
        ("RE_GRANT", "grant"),
        ("RE_REFUSAL", "provisional_refusal"),
        ("RE_OPPOSITION", "opposition_filed"),
        ("RE_RENEWAL", "renewal"),
        ("RE_LAPSE", "lapse"),
        ("RE_TRANSFER", "transfer"),
        ("RE_CHANGE_NAME", "change_name"),
    )

    def parse_pdf(
        self, pdf_path: Path | str | bytes, event_date: date | None = None
    ) -> list[BPIEvent]:
        """Parse a single BPI PDF into a list of events.

        Events carry the page they were found on, the surrounding text excerpt
        and a confidence score.

        Args:
            pdf_path: A filesystem path, or the raw PDF bytes.
            event_date: The bulletin date (defaults to today).

        Returns:
            A list of extracted :class:`BPIEvent` objects. An empty list is
            returned when the PDF yields too little text (e.g. a scanned image).
        """
        if isinstance(pdf_path, (str, Path)):
            pages = self._extract_pages(str(pdf_path))
        else:
            pages = self._extract_pages_from_bytes(pdf_path)

        total_text = "\n".join(pages)
        if not total_text or len(total_text.strip()) < 50:
            logger.warning("BPI PDF produced very little text — possible scan/image PDF")
            return []

        if event_date is None:
            event_date = datetime.now().date()

        events: list[BPIEvent] = []
        for page_index, page_text in enumerate(pages, start=1):
            if not page_text.strip():
                continue
            for pattern_name, event_type in self._SECTION_PATTERNS:
                events.extend(
                    self._extract_events(
                        page_text,
                        event_date,
                        getattr(self, pattern_name),
                        event_type,
                        page_number=page_index,
                    )
                )
        return events

    def _extract_pages(self, pdf_path: str) -> list[str]:
        """Extract per-page text from a PDF file, with a pymupdf fallback.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            One string per page (empty list if extraction fails entirely).
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return [page.extract_text() or "" for page in pdf.pages]
        except Exception:
            logger.warning("pdfplumber failed, trying pymupdf fallback")
            try:
                doc = fitz.open(pdf_path)
                pages = [page.get_text() for page in doc]
                doc.close()
                return pages
            except Exception:
                logger.exception("Both PDF extractors failed")
                return []

    def _extract_pages_from_bytes(self, pdf_bytes: bytes) -> list[str]:
        """Extract per-page text from raw PDF bytes with layered fallbacks.

        Order: ``pdfplumber`` → ``pymupdf`` → UTF-8 decode. The final decode
        step lets callers feed already-extracted plain text through the parser
        (treated as a single page).

        Args:
            pdf_bytes: The raw bytes.

        Returns:
            One string per page (empty list if all strategies fail).
        """
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                return [page.extract_text() or "" for page in pdf.pages]
        except Exception:
            try:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                pages = [page.get_text() for page in doc]
                doc.close()
                return pages
            except Exception:
                logger.warning(
                    "Both PDF extractors failed for bytes; treating as plain text"
                )
                try:
                    return [pdf_bytes.decode("utf-8", errors="ignore")]
                except Exception:
                    logger.exception("Plain text fallback also failed")
                    return []

    def _extract_text(self, pdf_path: str) -> str:
        """Extract the full text of a PDF file (all pages concatenated)."""
        return "\n".join(self._extract_pages(pdf_path))

    def _extract_text_from_bytes(self, pdf_bytes: bytes) -> str:
        """Extract the full text from raw PDF bytes (all pages concatenated)."""
        return "\n".join(self._extract_pages_from_bytes(pdf_bytes))

    @staticmethod
    def _normalise_application_number(raw: str) -> str:
        """Return the canonical form of a captured BPI application number.

        The BPI publishes Portuguese process numbers with optional internal
        whitespace (``770 255``) and an optional ``N.`` prefix. Downstream
        ingestion matches this value against ``Trademark.application_number``,
        so the parser emits the canonical whitespace-stripped form here (the
        same canonicalisation used by the BPI data contract:
        ``process_number='770255'`` for a raw ``N.º 770 255``).
        """
        if not raw:
            return ""
        return re.sub(r"\s+", "", raw)

    def _extract_events(
        self,
        text: str,
        event_date: date,
        pattern: re.Pattern[str],
        event_type: str,
        page_number: int | None = None,
    ) -> list[BPIEvent]:
        """Find section headers matching ``pattern`` and attach nearby app numbers.

        For each matching line, the following few lines are scanned for an
        application number; a :class:`BPIEvent` is emitted only when one is found.

        Args:
            text: The bulletin (or single-page) text.
            event_date: The bulletin date.
            pattern: The section-header pattern to match.
            event_type: The event type label to assign.
            page_number: The 1-based page the text came from, when known.

        Returns:
            The extracted events, each scored for confidence.
        """
        events: list[BPIEvent] = []
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if not pattern.search(line):
                continue
            app_num = ""
            context_lines: list[str] = []
            for j in range(i, min(i + 8, len(lines))):
                context_lines.append(lines[j])
                match = self.RE_APPLICATION.search(lines[j])
                if match and not app_num:
                    app_num = self._normalise_application_number(match.group(1))
            if app_num:
                excerpt = " | ".join(context_lines).strip()[:1000]
                events.append(
                    BPIEvent(
                        event_type=event_type,
                        event_date=event_date,
                        application_number=app_num,
                        description=excerpt[:500],
                        raw_text=line[:300],
                        page_number=page_number,
                        source_excerpt=excerpt,
                        confidence_score=score_bpi_event(
                            event_type,
                            app_num,
                            excerpt,
                            has_event_date=event_date is not None,
                        ),
                    )
                )
        return events

    def extract_publications(self, text: str, event_date: date) -> list[BPIEvent]:
        """Extract publication events."""
        return self._extract_events(text, event_date, self.RE_PUBLICATION, "publication")

    def extract_grants(self, text: str, event_date: date) -> list[BPIEvent]:
        """Extract grant events."""
        return self._extract_events(text, event_date, self.RE_GRANT, "grant")

    def extract_oppositions(self, text: str, event_date: date) -> list[BPIEvent]:
        """Extract opposition events."""
        return self._extract_events(
            text, event_date, self.RE_OPPOSITION, "opposition_filed"
        )

    def extract_renewals(self, text: str, event_date: date) -> list[BPIEvent]:
        """Extract renewal events."""
        return self._extract_events(text, event_date, self.RE_RENEWAL, "renewal")

    def extract_provisional_refusals(self, text: str, event_date: date) -> list[BPIEvent]:
        """Extract provisional refusal events."""
        return self._extract_events(
            text, event_date, self.RE_REFUSAL, "provisional_refusal"
        )

    def extract_lapses(self, text: str, event_date: date) -> list[BPIEvent]:
        """Extract lapse/expiry events."""
        return self._extract_events(text, event_date, self.RE_LAPSE, "lapse")

    def extract_transfers(self, text: str, event_date: date) -> list[BPIEvent]:
        """Extract transfer/assignment events."""
        return self._extract_events(text, event_date, self.RE_TRANSFER, "transfer")

    def extract_change_names(self, text: str, event_date: date) -> list[BPIEvent]:
        """Extract change-of-name events."""
        return self._extract_events(text, event_date, self.RE_CHANGE_NAME, "change_name")

    async def store_document(
        self,
        session: AsyncSession,
        pdf_bytes: bytes,
        *,
        source_url: str | None = None,
        publication_date: date | None = None,
        document_type: str = "bpi_bulletin",
        storage_dir: str | Path | None = None,
    ) -> Document:
        """Archive a bulletin PDF in ``core.documents`` (checksum-deduplicated).

        The file is written under ``storage_dir`` named by publication date and
        content hash; re-storing the same bytes returns the existing row.

        Args:
            session: An active async session (rows are flushed, not committed).
            pdf_bytes: The raw PDF content.
            source_url: The URL the PDF was downloaded from.
            publication_date: The bulletin's publication date.
            document_type: The document type label.
            storage_dir: Target directory (defaults to settings.DOCUMENT_STORAGE_DIR).

        Returns:
            The existing or newly created :class:`Document` row.
        """
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()

        existing = (
            await session.execute(
                select(Document).where(
                    Document.file_hash == file_hash,
                    Document.document_type == document_type,
                )
            )
        ).scalars().first()
        if existing is not None:
            return existing

        directory = Path(storage_dir or settings.DOCUMENT_STORAGE_DIR)
        directory.mkdir(parents=True, exist_ok=True)
        date_part = (publication_date or datetime.now().date()).isoformat()
        file_path = directory / f"bpi_{date_part}_{file_hash[:12]}.pdf"
        if not file_path.exists():
            file_path.write_bytes(pdf_bytes)

        page_count: int | None = None
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count = doc.page_count
            doc.close()
        except Exception:  # noqa: BLE001 - metadata only, never fatal
            logger.warning("Could not read page count for stored BPI document")

        document = Document(
            document_type=document_type,
            source_url=source_url,
            storage_path=str(file_path),
            file_hash=file_hash,
            publication_date=publication_date,
            language="pt",
            meta={"size_bytes": len(pdf_bytes), "pages": page_count},
        )
        session.add(document)
        await session.flush()
        return document

    async def download_latest(self, target_date: date | None = None) -> bytes:
        """Download the BPI PDF for a given date.

        INPI publishes bulletins under a few URL patterns; each candidate is
        tried in turn. Returns empty bytes when nothing can be downloaded so
        callers can skip gracefully rather than crash.

        Args:
            target_date: The bulletin date to download (defaults to today).

        Returns:
            The PDF content bytes, or ``b""`` on failure.
        """
        if target_date is None:
            target_date = datetime.now().date()

        year, month, day = target_date.year, target_date.month, target_date.day
        urls_to_try = [
            f"{BPI_BASE_URL}/download/{year}/{month:02d}/{day:02d}/bpi.pdf",
            f"{BPI_BASE_URL}/download/{year}/{month:02d}/bpi_{day:02d}.pdf",
        ]

        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            for url in urls_to_try:
                try:
                    response = await client.get(url)
                except httpx.HTTPError:
                    continue
                content_type = response.headers.get("content-type", "")
                if response.status_code == 200 and content_type.startswith(
                    "application/pdf"
                ):
                    logger.info("Downloaded BPI PDF from %s", url)
                    return response.content

        logger.warning("Could not download BPI PDF for %s; returning placeholder", target_date)
        return b""

    def download_url_for(self, target_date: date) -> str:
        """Return the primary download URL candidate for a bulletin date."""
        return (
            f"{BPI_BASE_URL}/download/{target_date.year}/"
            f"{target_date.month:02d}/{target_date.day:02d}/bpi.pdf"
        )
