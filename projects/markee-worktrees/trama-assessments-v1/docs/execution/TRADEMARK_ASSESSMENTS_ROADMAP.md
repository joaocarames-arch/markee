# Trademark Assessments — Phased Roadmap

Status: Phase 0 + Phase 1 delivered (this slice). Later phases are planned.

A "Trama-style" free trademark check for markee: the user submits a mark name,
a jurisdiction and a short business description, and receives a structured,
branded assessment report (verdict, risk level, distinctiveness,
recommended Nice classes, identical/similar candidates, recommendations and a
legal disclaimer). The first slice is intentionally **stateless** — nothing is
persisted — and **fail-soft** — missing external data (EUIPO credentials, an
empty database) degrades gracefully instead of breaking the feature.

## Phases

### Phase 0 — Safe foundation and feature flag
- Isolated worktree/branch `feat/trademark-assessments-v1`.
- This roadmap document + the report contract + the legal disclaimer.
- Tests for the report schema and the basic scoring heuristics.

### Phase 1 — Free Trademark Check MVP (this slice)
- Stateless assessment API: `POST /api/v1/assessments`.
- Simple, deterministic heuristics: distinctiveness + Nice class recommendation
  (35/42/45 and common business descriptions) + risk scoring.
- Similarity via the existing `SimilarityEngine` when a database is reachable;
  otherwise safe empty candidates with an explicit provenance flag.
- Dashboard page with the check form, a Trama-like (markee-branded) report view,
  a print/PDF affordance and a professional disclaimer.

### Phase 2 — Real data connectors and scrapers
- EUIPO / TMview client integration where existing config allows.
- INPI BPI downloader/parser for lifecycle events (not primary similarity).
- Source freshness / provenance states; background scheduled checks via Celery.
- No credential hard dependency — missing credentials must degrade safely.

### Phase 3 — Persistent reports and automations
- Persist assessments under a user/account; periodic regeneration.
- Email/Telegram alert hooks; watchlist conversion from a report.
- Audit / provenance snapshots.

### Phase 4 — Advanced similarity and risk engine
- Portuguese phonetic engine, class-overlap scoring, exact/near match detection.
- Opposition window / deadline risk; holder/applicant risk weighting.

### Phase 5 — Professional PDF / white-label
- Server-side PDF export if browser print is not enough.
- White-label template for IP professionals; multi-client report archive.
- Share links with expiry.

### Phase 6 — Release hardening
- Docs, observability, smoke reports; immutable image build.
- Candidate deploy; public desktop/mobile browser QA; rollback evidence.

## Report contract (Phase 1)

`POST /api/v1/assessments` — request body:

| Field                  | Type            | Required | Notes                                      |
|------------------------|-----------------|----------|--------------------------------------------|
| `mark_name`            | string          | yes      | 1–255 chars, the proposed trademark.       |
| `jurisdiction`         | string          | no       | `EU`/`EUIPO`/`PT`/`INPI`; default `EU`.    |
| `business_description` | string          | no       | Free text describing goods/services.       |
| `nice_classes`         | list[int] (1–45)| no       | Optional applicant-provided classes.       |

Response body (`AssessmentReport`):

```jsonc
{
  "mark_name": "string",
  "jurisdiction": "EU",
  "business_description": "string",
  "verdict": "eligible | eligible_with_risk | not_recommended",
  "verdict_label": "Elegível para registo",          // PT-PT
  "risk_level": "low | medium | high",
  "distinctiveness": {
    "level": "fully_met | partially_met | not_met",
    "score": 0.0,                                     // 0–100
    "rationale": "string"                             // PT-PT
  },
  "recommended_classes": [
    { "class_number": 35, "title_pt": "string", "reason": "string" }
  ],
  "identical_match": false,
  "candidates": [
    {
      "word_mark": "string",
      "jurisdiction": "EU",
      "similarity": 62.0,                             // 0–100
      "similarity_band": "low | medium | high",
      "source": "string"
    }
  ],
  "candidates_provenance": "database | unavailable | sample",
  "opposition_risk": { "level": "low | medium | high", "rationale": "string" },
  "recommendations": ["string"],                       // PT-PT
  "disclaimers": ["string"],                            // PT-PT
  "created_at": "2026-08-01T00:00:00+00:00"
}
```

### Provenance states for `candidates`
- `database` — candidates came from the live trademark database via
  `SimilarityEngine`.
- `unavailable` — the database/external source could not be reached; candidates
  are an empty list and the report says so explicitly.
- `sample` — reserved for demonstration data (not used by default).

## Legal disclaimer (canonical PT-PT text)

The report is **not** legal advice. Every generated report must carry these
disclaimers (single source of truth: `app/services/assessment.py::DISCLAIMERS`):

1. Esta avaliação é gerada automaticamente e tem caráter meramente informativo;
   não constitui aconselhamento jurídico nem garante o registo da marca.
2. A análise de anterioridades pode estar incompleta ou desatualizada e depende
   da disponibilidade das bases de dados do EUIPO e do INPI no momento da
   consulta.
3. Para uma decisão de registo, recomenda-se a validação por um Agente Oficial
   da Propriedade Industrial ou advogado especializado.
</invoke>
