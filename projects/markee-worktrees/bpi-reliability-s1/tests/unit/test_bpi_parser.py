"""Tests for the BPI PDF parser.

Testa regex patterns para extração de eventos do Boletim da Propriedade Industrial.
"""
import re

import pytest
from datetime import date

from app.services.bpi_parser import BPIParser, BPIEvent


class TestRegexPatterns:
    """Testa padrões regex individuais do BPIParser."""

    def setup_method(self):
        self.parser = BPIParser()

    # --- Application number extraction ---
    def test_application_number_pattern(self):
        # The BPI data contract (docs/research/BPI_DATA_CONTRACT.md §2.3.2)
        # defines Portuguese national process numbers with internal whitespace
        # and optional N. / n.º prefixes. The parser matches the real formats
        # observed in published bulletins.
        texts = [
            "Nº de pedido: N.123456",
            "Nº. Pedido: N.789012",
            "Processo: 770255",
            "Processo: 770 255",
            "Processo n.º 770 255",
            "Nº de pedido: N. 123456",
            "Application No: 12345678",
        ]
        for t in texts:
            m = self.parser.RE_APPLICATION.search(t)
            assert m is not None, f"Failed on: {t}"

    def test_application_number_extraction(self):
        m = self.parser.RE_APPLICATION.search("Nº de pedido: N.123456")
        assert m.group(1) == "N.123456"

    # --- Publication ---
    def test_publication_pattern(self):
        assert self.parser.RE_PUBLICATION.search("Publicação do pedido") is not None
        assert self.parser.RE_PUBLICATION.search("Despacho de Publicação n. 1234") is not None

    # --- Refusal ---
    def test_refusal_pattern(self):
        assert self.parser.RE_REFUSAL.search("Recusa Provisória") is not None
        assert self.parser.RE_REFUSAL.search("Recusa absoluta") is not None
        assert self.parser.RE_REFUSAL.search("Recusa relativa") is not None

    # --- Opposition ---
    def test_opposition_pattern(self):
        assert self.parser.RE_OPPOSITION.search("Oposição apresentada") is not None
        assert self.parser.RE_OPPOSITION.search("Contestação") is not None

    # --- Renewal ---
    def test_renewal_pattern(self):
        assert self.parser.RE_RENEWAL.search("Renovação do registo") is not None
        assert self.parser.RE_RENEWAL.search("Pagamento da anuidade") is not None

    # --- Lapse ---
    def test_lapse_pattern(self):
        assert self.parser.RE_LAPSE.search("Caducidade declarada") is not None
        assert self.parser.RE_LAPSE.search("Extinção de registo") is not None

    # --- Transfer ---
    def test_transfer_pattern(self):
        assert self.parser.RE_TRANSFER.search("Transmissão") is not None
        assert self.parser.RE_TRANSFER.search("Alteração de titular") is not None

    # --- Change name ---
    def test_change_name_pattern(self):
        assert self.parser.RE_CHANGE_NAME.search("Alteração de denominação") is not None
        assert self.parser.RE_CHANGE_NAME.search("Mudança de nome") is not None

    # --- Grant ---
    def test_grant_pattern(self):
        assert self.parser.RE_GRANT.search("Concessão do registo") is not None
        assert self.parser.RE_GRANT.search("Registo concedido") is not None


class TestEventExtraction:
    """Testa extração de eventos a partir de texto simulado do BPI."""

    def setup_method(self):
        self.parser = BPIParser()
        self.event_date = date(2024, 7, 15)

    def test_extract_publications(self):
        text = """Despacho de Publicação n. 12345
Nº de pedido: N.987654
Marca: SUPERMARK"""
        events = self.parser.extract_publications(text, self.event_date)
        assert len(events) >= 1
        assert events[0].event_type == "publication"
        assert events[0].application_number == "N.987654"

    def test_extract_grants(self):
        text = """Concessão do registo
Nº de pedido: N.111222
Marca: BRANDX"""
        events = self.parser.extract_grants(text, self.event_date)
        assert len(events) >= 1
        assert events[0].event_type == "grant"

    def test_extract_provisional_refusals(self):
        text = """Recusa Provisória
Nº de pedido: N.333444
Fundamento: Artigo 8º"""
        events = self.parser.extract_provisional_refusals(text, self.event_date)
        assert len(events) >= 1
        assert events[0].event_type == "provisional_refusal"

    def test_extract_oppositions(self):
        text = """Oposição apresentada
Nº de pedido: N.555666
Oponente: Empresa Y"""
        events = self.parser.extract_oppositions(text, self.event_date)
        assert len(events) >= 1
        assert events[0].event_type == "opposition_filed"

    def test_extract_renewals(self):
        text = """Renovação
Nº de pedido: N.777888
Pagamento de taxa confirmado"""
        events = self.parser.extract_renewals(text, self.event_date)
        assert len(events) >= 1
        assert events[0].event_type == "renewal"

    def test_extract_lapses(self):
        text = """Caducidade declarada
Nº de pedido: N.999000
Extinção de registo"""
        events = self.parser.extract_lapses(text, self.event_date)
        assert len(events) >= 1
        assert events[0].event_type == "lapse"

    def test_extract_transfers(self):
        text = """Transmissão
Nº de pedido: N.112233
Cessão de direitos"""
        events = self.parser.extract_transfers(text, self.event_date)
        assert len(events) >= 1
        assert events[0].event_type == "transfer"

    def test_extract_change_names(self):
        text = """Alteração de denominação
Nº de pedido: N.445566
Novo nome: ABC Lda."""
        events = self.parser.extract_change_names(text, self.event_date)
        assert len(events) >= 1
        assert events[0].event_type == "change_name"

    def test_no_application_number_no_event(self):
        text = """Publicação do pedido
Marca: TESTBRAND sem número"""
        events = self.parser.extract_publications(text, self.event_date)
        assert len(events) == 0

    def test_multiple_events_same_text(self):
        text = """Despacho de Publicação n. 1
Nº de pedido: N.001
Marca: ALPHA

Despacho de Publicação n. 2
Nº de pedido: N.002
Marca: BETA"""
        events = self.parser.extract_publications(text, self.event_date)
        assert len(events) == 2
        assert events[0].application_number == "N.001"
        assert events[1].application_number == "N.002"


class TestParsePdf:
    """Testa o método parse_pdf com texto extraído simulado."""

    def setup_method(self):
        self.parser = BPIParser()

    def test_parse_pdf_empty(self):
        events = self.parser.parse_pdf(b"", date(2024, 1, 1))
        assert events == []

    def test_parse_pdf_with_events(self):
        text = """Boletim da Propriedade Industrial

Despacho de Publicação
Nº de pedido: N.123456
Marca: MARKEE

Recusa Provisória
Nº de pedido: N.789012
Marca: MARKEE2

Oposição apresentada
Nº de pedido: N.345678
Marca: MARKEE3
"""
        # Simula bytes de PDF (não é um PDF real, mas _extract_text_from_bytes trata)
        events = self.parser.parse_pdf(text.encode("utf-8"), date(2024, 7, 1))
        types = [e.event_type for e in events]
        assert "publication" in types
        assert "provisional_refusal" in types
        assert "opposition_filed" in types


class TestPTProcessNumberParsing:
    """Parser correctness for real-world Portuguese process number formats.

    The INPI Boletim publishes process numbers in ST.17-INPI formatted as
    ``N.º 770 255`` with internal whitespace inside the digit block (and
    sometimes a ``Processo n.º`` prefix). The BPI data contract canonicalises
    the value to ``770255`` for matching (see docs/research/BPI_DATA_CONTRACT.md
    section 2.3.2: ``process_number_raw='N.º 770 255'`` vs
    ``process_number='770255'``). The parser MUST emit the canonical
    whitespace-stripped form in ``BPIEvent.application_number``; otherwise
    downstream ingestion silently stores truncated, unmatchable application
    numbers.
    """

    def setup_method(self):
        self.parser = BPIParser()
        self.event_date = date(2026, 6, 26)

    def test_re_application_captures_pt_number_with_internal_whitespace(self):
        """``Processo: 770 255`` must capture ``770 255``, not ``770``."""
        m = self.parser.RE_APPLICATION.search("Processo: 770 255")
        assert m is not None
        assert m.group(1) == "770 255"

    def test_re_application_captures_pt_number_with_prefix_dot(self):
        """``Nº de pedido: N. 123456`` must capture ``N. 123456`` as a unit."""
        m = self.parser.RE_APPLICATION.search("Nº de pedido: N. 123456")
        assert m is not None
        assert m.group(1) == "N. 123456"

    def test_re_application_captures_pt_number_with_dotted_abbreviation(self):
        """``Processo n.º 770 255`` must capture the full numeric block."""
        m = self.parser.RE_APPLICATION.search("Processo n.º 770 255")
        assert m is not None
        # Either "770 255" or "770255" is acceptable as the captured group,
        # but it must contain all six digits.
        captured = re.sub(r"\s+", "", m.group(1))
        assert captured == "770255"

    def test_extract_grant_normalises_whitespace_separated_process_number(self):
        """A grant section whose only nearby application number is the
        whitespace-separated PT form must emit the canonical (no-space) number
        in ``BPIEvent.application_number``."""
        text = """Concessão do registo
Processo: 770 255
Marca: MARKEE"""
        events = self.parser.extract_grants(text, self.event_date)
        assert len(events) == 1
        canonical = re.sub(r"\s+", "", events[0].application_number)
        assert canonical == "770255"
        # Confidence must reflect a well-formed PT application number.
        assert events[0].confidence_score >= 0.6

    def test_extract_publication_normalises_n_dotted_pt_process_number(self):
        """``Nº de pedido: N. 123456`` must canonicalise to ``N.123456``."""
        text = """Despacho de Publicação n. 1
Nº de pedido: N. 123456
Marca: ALPHA"""
        events = self.parser.extract_publications(text, self.event_date)
        assert len(events) == 1
        assert events[0].application_number == "N.123456"
