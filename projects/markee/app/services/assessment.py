"""Stateless trademark assessment service.

Produces a Trama-style "free check" report from three deterministic heuristics
— distinctiveness, Nice class recommendation and opposition-risk — plus an
optional similarity pass (wired by the API layer, not here). The logic in this
module is pure: no database, network or FastAPI dependency, so it is trivially
unit-testable and safe to run when external data sources are unavailable.

All code and comments are in English; every user-facing string is European
Portuguese (PT-PT).
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# ── Vocabulary types ────────────────────────────────────────────────────────
DistinctivenessLevel = Literal["fully_met", "partially_met", "not_met"]
RiskLevel = Literal["low", "medium", "high"]
Verdict = Literal["eligible", "eligible_with_risk", "not_recommended"]
Provenance = Literal["database", "unavailable", "sample"]
SimilarityBand = Literal["low", "medium", "high"]


# ── Canonical legal disclaimer (single source of truth) ─────────────────────
DISCLAIMERS: list[str] = [
    "Esta avaliação é gerada automaticamente e tem caráter meramente "
    "informativo; não constitui aconselhamento jurídico nem garante o registo "
    "da marca.",
    "A análise de anterioridades pode estar incompleta ou desatualizada e "
    "depende da disponibilidade das bases de dados do EUIPO e do INPI no "
    "momento da consulta.",
    "Para uma decisão de registo, recomenda-se a validação por um Agente "
    "Oficial da Propriedade Industrial ou advogado especializado.",
]


# ── Nice classification catalogue used by the recommender ───────────────────
# class_number -> (PT title, keyword tokens). Keywords are matched against the
# accent-folded tokens of the business description (whole-token match) or, for
# multi-word keywords, as a substring of the folded text.
NICE_CLASS_TITLES: dict[int, str] = {
    3: "Cosméticos e produtos de higiene",
    5: "Produtos farmacêuticos",
    9: "Software, aparelhos e equipamento informático",
    25: "Vestuário, calçado e chapelaria",
    29: "Alimentos de origem animal e conservas",
    30: "Café, chá, padaria e produtos alimentares",
    35: "Publicidade, gestão de negócios e comércio eletrónico",
    36: "Serviços financeiros e de seguros",
    41: "Educação, formação e entretenimento",
    42: "Serviços científicos e tecnológicos; I&D; SaaS",
    43: "Serviços de restauração e alojamento",
    44: "Serviços médicos, de saúde e de beleza",
    45: "Serviços jurídicos e de segurança",
}

_CLASS_KEYWORDS: dict[int, tuple[str, ...]] = {
    3: ("cosmetico", "cosmeticos", "perfume", "perfumaria", "higiene", "sabonete"),
    5: ("farmaceutico", "farmacia", "medicamento", "suplemento", "vitaminas"),
    9: (
        "software",
        "aplicacao",
        "aplicacoes",
        "app",
        "informatica",
        "hardware",
        "mobile",
        "jogo",
        "jogos",
        "tecnologia",
        "eletronica",
    ),
    25: ("roupa", "vestuario", "moda", "calcado", "sapatos", "chapelaria", "textil"),
    29: ("conservas", "carne", "peixe", "laticinios", "enchidos"),
    30: ("cafe", "cha", "padaria", "pastelaria", "chocolate", "bolos", "pao"),
    35: (
        "loja",
        "lojas",
        "ecommerce",
        "comercio",
        "comercio eletronico",
        "venda",
        "vendas",
        "retalho",
        "publicidade",
        "marketing",
        "negocio",
        "negocios",
        "consultoria",
        "gestao",
        "marketplace",
    ),
    36: (
        "seguros",
        "financas",
        "financeiro",
        "banco",
        "banca",
        "investimento",
        "fintech",
        "pagamentos",
        "credito",
    ),
    41: (
        "educacao",
        "formacao",
        "cursos",
        "ensino",
        "entretenimento",
        "eventos",
        "escola",
    ),
    42: (
        "saas",
        "software",
        "desenvolvimento",
        "tecnologia",
        "cloud",
        "nuvem",
        "dados",
        "plataforma",
        "engenharia",
        "investigacao",
        "design",
        "web",
    ),
    43: (
        "restaurante",
        "restauracao",
        "cafe",
        "bar",
        "hotel",
        "alojamento",
        "catering",
        "comida",
    ),
    44: ("clinica", "saude", "medico", "estetica", "beleza", "spa", "dentista"),
    45: (
        "juridico",
        "juridicos",
        "advocacia",
        "advogado",
        "legal",
        "seguranca",
        "direito",
    ),
}

# The default fallback class when no signal is found — Trama defaults to 35
# ("Advisory services for business management").
_DEFAULT_CLASS = 35

# Generic / descriptive tokens that carry little distinctiveness on their own.
_GENERIC_TERMS: frozenset[str] = frozenset(
    {
        "loja",
        "shop",
        "store",
        "online",
        "web",
        "tech",
        "digital",
        "group",
        "grupo",
        "company",
        "empresa",
        "servico",
        "servicos",
        "services",
        "solucoes",
        "solutions",
        "consultoria",
        "consulting",
        "market",
        "marketing",
        "cloud",
        "data",
        "software",
        "app",
        "studio",
        "design",
        "media",
        "global",
        "express",
        "pro",
        "plus",
        "premium",
        "center",
        "centro",
        "clinica",
        "cafe",
        "restaurante",
        "bar",
        "hotel",
        "seguros",
        "banco",
        "finance",
        "financas",
        "the",
        "and",
        "de",
        "da",
        "do",
        "e",
    }
)


def _fold(value: str) -> str:
    """Lowercase and strip accents (NFD + drop combining marks)."""
    lowered = value.lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _tokens(value: str) -> list[str]:
    """Return the folded alphanumeric word tokens of ``value``."""
    return re.findall(r"[a-z0-9]+", _fold(value))


# ── Pydantic contract models ────────────────────────────────────────────────
class DistinctivenessResult(BaseModel):
    """Distinctiveness component of the report."""

    level: DistinctivenessLevel
    score: float = Field(ge=0.0, le=100.0)
    rationale: str


class ClassRecommendation(BaseModel):
    """A single recommended Nice class."""

    class_number: int = Field(ge=1, le=45)
    title_pt: str
    reason: str


class CandidateMatch(BaseModel):
    """A prior mark surfaced by the similarity pass."""

    word_mark: str
    jurisdiction: str
    similarity: float = Field(ge=0.0, le=100.0)
    similarity_band: SimilarityBand
    source: str


class OppositionRisk(BaseModel):
    """Opposition / office-action risk component."""

    level: RiskLevel
    rationale: str


class AssessmentRequest(BaseModel):
    """Input for a free trademark check."""

    mark_name: str = Field(min_length=1, max_length=255)
    jurisdiction: str = Field(default="EU", max_length=16)
    business_description: str = Field(default="", max_length=2000)
    nice_classes: list[int] | None = None

    @field_validator("mark_name")
    @classmethod
    def _non_blank_mark(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("mark_name must not be blank")
        return value.strip()

    @field_validator("nice_classes")
    @classmethod
    def _valid_classes(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        for number in value:
            if not 1 <= number <= 45:
                raise ValueError("nice_classes must be between 1 and 45")
        return value


class AssessmentReport(BaseModel):
    """The full assessment report — the published response contract."""

    mark_name: str
    jurisdiction: str
    business_description: str
    verdict: Verdict
    verdict_label: str
    risk_level: RiskLevel
    distinctiveness: DistinctivenessResult
    recommended_classes: list[ClassRecommendation]
    identical_match: bool
    candidates: list[CandidateMatch]
    candidates_provenance: Provenance
    opposition_risk: OppositionRisk
    recommendations: list[str]
    disclaimers: list[str]
    created_at: datetime


# ── Heuristics ──────────────────────────────────────────────────────────────
def assess_distinctiveness(
    mark_name: str, business_description: str = ""
) -> DistinctivenessResult:
    """Estimate how distinctive a mark is (deterministic heuristic).

    Signals, all penalising an initial score of 100:

    - the share of tokens that are generic/descriptive terms;
    - tokens that literally describe the declared goods/services;
    - very short marks (acronyms) are inherently weaker.

    Args:
        mark_name: The proposed trademark.
        business_description: Optional description of the goods/services.

    Returns:
        A :class:`DistinctivenessResult` with a level, a 0–100 score and a
        Portuguese rationale.
    """
    tokens = _tokens(mark_name)
    if not tokens:
        return DistinctivenessResult(
            level="not_met",
            score=0.0,
            rationale="A marca indicada está vazia ou não contém carateres válidos.",
        )

    generic = [t for t in tokens if t in _GENERIC_TERMS]
    generic_ratio = len(generic) / len(tokens)

    desc_tokens = set(_tokens(business_description))
    descriptive_hits = [t for t in tokens if t in desc_tokens]
    descriptive_ratio = len(descriptive_hits) / len(tokens)

    score = 100.0
    score -= 55.0 * generic_ratio
    score -= 20.0 * descriptive_ratio

    compact = "".join(tokens)
    if len(compact) <= 2:
        score -= 40.0
    elif len(compact) <= 3:
        score -= 15.0

    score = max(0.0, min(100.0, score))

    if score >= 70.0:
        level: DistinctivenessLevel = "fully_met"
        rationale = (
            "A marca apresenta caráter distintivo suficiente para diferenciar "
            "os produtos/serviços na perspetiva do consumidor."
        )
    elif score >= 40.0:
        level = "partially_met"
        rationale = (
            "A marca contém elementos genéricos ou descritivos que podem "
            "reduzir o seu caráter distintivo; pondere reforçar a componente "
            "distintiva."
        )
    else:
        level = "not_met"
        rationale = (
            "A marca é maioritariamente genérica ou descritiva da atividade, o "
            "que dificulta o registo por falta de caráter distintivo."
        )

    return DistinctivenessResult(level=level, score=round(score, 1), rationale=rationale)


def _keyword_matches(keyword: str, tokens: set[str], folded_text: str) -> bool:
    """Whole-token match for single words; substring for multi-word keywords."""
    if " " in keyword:
        return keyword in folded_text
    return keyword in tokens


def recommend_nice_classes(
    business_description: str, provided: list[int] | None = None
) -> list[ClassRecommendation]:
    """Recommend Nice classes from a business description (heuristic).

    Covers classes 35/42/45 and other common business descriptions, and always
    preserves any classes explicitly provided by the applicant. Never returns
    an empty list — falls back to class 35 when there is no signal.

    Args:
        business_description: Free-text description of goods/services.
        provided: Optional applicant-supplied Nice classes to preserve.

    Returns:
        A list of :class:`ClassRecommendation`, sorted by class number.
    """
    folded_text = _fold(business_description)
    tokens = set(_tokens(business_description))
    recs: dict[int, ClassRecommendation] = {}

    for class_number, keywords in _CLASS_KEYWORDS.items():
        matched = [
            kw for kw in keywords if _keyword_matches(kw, tokens, folded_text)
        ]
        if matched:
            recs[class_number] = ClassRecommendation(
                class_number=class_number,
                title_pt=NICE_CLASS_TITLES.get(class_number, f"Classe {class_number}"),
                reason=(
                    "Sugerida pela descrição da atividade "
                    f"(termo «{matched[0]}»)."
                ),
            )

    for class_number in provided or []:
        if not 1 <= class_number <= 45:
            continue
        if class_number in recs:
            recs[class_number].reason += " Também indicada pelo requerente."
        else:
            recs[class_number] = ClassRecommendation(
                class_number=class_number,
                title_pt=NICE_CLASS_TITLES.get(class_number, f"Classe {class_number}"),
                reason="Indicada pelo requerente.",
            )

    if not recs:
        recs[_DEFAULT_CLASS] = ClassRecommendation(
            class_number=_DEFAULT_CLASS,
            title_pt=NICE_CLASS_TITLES[_DEFAULT_CLASS],
            reason=(
                "Classe genérica de negócio recomendada por defeito na ausência "
                "de descrição específica."
            ),
        )

    return [recs[number] for number in sorted(recs)]


def similarity_band(score: float) -> SimilarityBand:
    """Map a 0–100 similarity score into a coarse band."""
    if score >= 85.0:
        return "high"
    if score >= 70.0:
        return "medium"
    return "low"


def assess_opposition_risk(
    distinctiveness_level: DistinctivenessLevel,
    candidates: list[CandidateMatch],
    identical_match: bool,
) -> OppositionRisk:
    """Derive opposition / office-action risk from distinctiveness + candidates.

    Args:
        distinctiveness_level: The distinctiveness verdict.
        candidates: Prior marks surfaced by the similarity pass.
        identical_match: Whether an identical prior mark exists.

    Returns:
        An :class:`OppositionRisk` with a level and a Portuguese rationale.
    """
    has_high = any(c.similarity >= 85.0 for c in candidates)
    has_medium = any(c.similarity >= 70.0 for c in candidates)

    if identical_match or has_high or distinctiveness_level == "not_met":
        level: RiskLevel = "high"
        rationale = (
            "Existe uma marca idêntica ou muito semelhante, ou a marca tem "
            "baixo caráter distintivo, o que aumenta o risco de oposição ou de "
            "recusa pelo instituto."
        )
    elif has_medium or distinctiveness_level == "partially_met":
        level = "medium"
        rationale = (
            "Foram identificadas semelhanças moderadas com marcas anteriores; "
            "existe algum risco de oposição consoante a sobreposição de "
            "classes e de mercado."
        )
    else:
        level = "low"
        rationale = (
            "Não foram identificadas anterioridades relevantes; o risco de "
            "oposição é baixo devido à distintividade da marca."
        )

    return OppositionRisk(level=level, rationale=rationale)


def determine_verdict(
    distinctiveness_level: DistinctivenessLevel,
    risk_level: RiskLevel,
    identical_match: bool,
) -> tuple[Verdict, str]:
    """Combine distinctiveness and risk into an overall verdict + PT label."""
    if identical_match or distinctiveness_level == "not_met" or risk_level == "high":
        return "not_recommended", "Registo não recomendado"
    if risk_level == "medium" or distinctiveness_level == "partially_met":
        return "eligible_with_risk", "Elegível com reservas"
    return "eligible", "Elegível para registo"


def _build_recommendations(
    distinctiveness: DistinctivenessResult,
    recommended_classes: list[ClassRecommendation],
    candidates: list[CandidateMatch],
    identical_match: bool,
    risk_level: RiskLevel,
    provenance: Provenance,
) -> list[str]:
    """Assemble the PT-PT recommendation bullets shown on the report."""
    recs: list[str] = []

    class_list = ", ".join(str(c.class_number) for c in recommended_classes)
    if class_list:
        recs.append(
            f"Considere registar a marca nas classes de Nice {class_list}, de "
            "acordo com a atividade descrita."
        )

    if distinctiveness.level != "fully_met":
        recs.append(
            "Reforce a componente distintiva da marca (por exemplo, um elemento "
            "verbal inventado ou um elemento figurativo) para reduzir o risco de "
            "recusa."
        )

    if identical_match:
        recs.append(
            "Foi encontrada uma marca idêntica; recomenda-se uma análise "
            "jurídica aprofundada antes de avançar com o pedido."
        )
    elif risk_level in {"medium", "high"}:
        recs.append(
            "Existem marcas semelhantes anteriores; avalie a sobreposição de "
            "classes e de mercado para estimar o risco de confusão."
        )
    else:
        recs.append(
            "Em média, apenas cerca de 5% dos pedidos enfrentam oposição; o "
            "registo é recomendável, sobretudo se já opera sob esta marca."
        )

    if provenance == "unavailable":
        recs.append(
            "A pesquisa de anterioridades não pôde ser concluída neste momento; "
            "repita a verificação para uma análise completa antes de decidir."
        )

    return recs


def build_report(
    request: AssessmentRequest,
    candidates: list[CandidateMatch],
    provenance: Provenance,
    created_at: datetime | None = None,
) -> AssessmentReport:
    """Assemble the full assessment report from a request + candidate list.

    Args:
        request: The validated assessment request.
        candidates: Prior marks from the similarity pass (may be empty).
        provenance: Where the candidates came from (``database`` /
            ``unavailable`` / ``sample``).
        created_at: Optional timestamp; defaults to ``datetime.now(UTC)``.

    Returns:
        A fully populated :class:`AssessmentReport`.
    """
    distinctiveness = assess_distinctiveness(
        request.mark_name, request.business_description
    )
    recommended_classes = recommend_nice_classes(
        request.business_description, request.nice_classes
    )

    folded_mark = _fold(request.mark_name)
    identical_match = any(_fold(c.word_mark) == folded_mark for c in candidates)

    opposition_risk = assess_opposition_risk(
        distinctiveness.level, candidates, identical_match
    )
    verdict, verdict_label = determine_verdict(
        distinctiveness.level, opposition_risk.level, identical_match
    )
    recommendations = _build_recommendations(
        distinctiveness,
        recommended_classes,
        candidates,
        identical_match,
        opposition_risk.level,
        provenance,
    )

    return AssessmentReport(
        mark_name=request.mark_name,
        jurisdiction=request.jurisdiction,
        business_description=request.business_description,
        verdict=verdict,
        verdict_label=verdict_label,
        risk_level=opposition_risk.level,
        distinctiveness=distinctiveness,
        recommended_classes=recommended_classes,
        identical_match=identical_match,
        candidates=candidates,
        candidates_provenance=provenance,
        opposition_risk=opposition_risk,
        recommendations=recommendations,
        disclaimers=list(DISCLAIMERS),
        created_at=created_at or datetime.now(timezone.utc),
    )
