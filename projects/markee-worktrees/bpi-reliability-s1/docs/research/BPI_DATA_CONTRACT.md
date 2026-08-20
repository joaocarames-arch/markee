# BPI data contract — Markee

Data: 2026-07-24
Âmbito: contrato campo a campo para dados derivados dos Boletins da Propriedade Industrial portugueses.

## 1. Princípios

1. O PDF oficial é a unidade raw imutável.
2. Cada evento normalizado preserva provenance suficiente: URL, SHA-256, boletim, página, secção, excerto, parser_version e confidence.
3. BPI é fonte prioritária para publicação/prova/prazos PT; EUIPO/TMview é fonte prioritária para snapshot bibliográfico e pesquisa/similaridade.
4. Nada é fundido por nome/sinal isolado.
5. Dados pessoais são minimizados; contactos e listas de procuradores não entram no MVP.

## 2. Entidades contratuais

### 2.1 `BpiBulletinRaw`

Representa o PDF oficial arquivado.

| Campo | Tipo | Null | Exemplo | Provenance/confidence | Dedupe/reconciliação | Notas |
|---|---|---:|---|---|---|---|
| `id` | uuid | não | `018f...` | sistema | PK | Identificador interno. |
| `source` | enum | não | `inpi_bpi` | fixo | parte de índices | Só `inpi_bpi`. |
| `publication_date` | date | não | `2026-06-26` | link oficial + cabeçalho PDF | unique lógico com version | Data publicada no texto do link; validar contra PDF. |
| `bulletin_number` | string | sim até extração | `2026/06/26` | cabeçalho PDF | reconciliação prova | Deve concordar com `publication_date`. |
| `source_url` | url | não | `https://inpi.justica.gov.pt/LinkClick.aspx?...` | página oficial | não tratar token como permanente | URL usado no download. |
| `listing_url` | url | sim | `.../pageNumber/0/beginDate/...` | discovery | auditoria | Onde foi descoberto. |
| `retrieved_at` | timestamptz | não | `2026-07-24T17:11:25Z` | HTTP client | replay | Momento de obtenção. |
| `http_status` | int | não | `200` | HTTP | qualidade | Esperado 200. |
| `http_headers` | json | não | `{Content-Type: application/pdf}` | HTTP | auditoria | Omitir cookies; guardar headers úteis. |
| `content_type` | string | não | `application/pdf` | HTTP | validação | Quarantine se diferente. |
| `content_disposition_filename` | string | sim | `2026-06-26.pdf` | HTTP | validação cruzada | Confirmado nas amostras. |
| `file_size_bytes` | int | não | `1312177` | bytes recebidos | drift/custo | Deve bater com Content-Length se existir. |
| `sha256` | hex string(64) | não | `d030966f...` | conteúdo binário | dedupe forte | Hash do PDF original. |
| `storage_path` | string | não | `raw/bpi/2026/06/2026-06-26.d030...pdf` | sistema | disaster recovery | Não sobrescrever. |
| `archive_version` | int | não | `1` | sistema | versionamento | Incrementa se mesma data tiver hash diferente. |
| `supersedes_bulletin_id` | uuid | sim | null | sistema/review | versionamento | Só após confirmação de republicação. |
| `page_count` | int | sim até extração | `71` | PyMuPDF | validação | Guardar após extraction. |
| `text_char_count` | int | sim | `135063` | PyMuPDF | qualidade | Métrica global. |
| `image_count` | int | sim | `44` | PyMuPDF | OCR trigger | Métrica global. |
| `created_at` | timestamptz | não | `...` | sistema | auditoria | |

Validações:

- `sha256` obrigatório antes de parsing.
- `content_type == application/pdf`.
- `publication_date` deve concordar com filename e `bulletin_number` quando disponíveis; conflito vai para review.

### 2.2 `BpiPageExtraction`

Representa extração por página.

| Campo | Tipo | Null | Exemplo | Provenance/confidence | Dedupe/reconciliação | Notas |
|---|---|---:|---|---|---|---|
| `id` | uuid | não | `...` | sistema | PK | |
| `bulletin_id` | uuid | não | `...` | FK raw | unique com page/parser | |
| `bulletin_sha256` | hex string | não | `d030...` | raw | replay | Copiado para isolamento. |
| `page_number` | int | não | `14` | PyMuPDF | unique | 1-based. |
| `page_count` | int | não | `71` | PyMuPDF/cabeçalho | validação | |
| `header_bulletin_number` | string | sim | `2026/06/26` | texto página | qualidade | |
| `header_page_label` | string | sim | `14 de 71` | texto página | qualidade | |
| `extraction_method` | enum | não | `pymupdf_text` | extractor | confidence | `pymupdf_text`, `pdfplumber_table`, `ocr`. |
| `page_text` | text | sim | `BOLETIM...` | extractor | hash | Texto completo por página. |
| `page_text_hash` | hex string | sim | `...` | sistema | dedupe | Hash do texto normalizado. |
| `blocks` | json | sim | `[{bbox, text}]` | PyMuPDF | layout drift | Guardar se custo aceitável. |
| `tables` | json | sim | `[[...]]` | pdfplumber | parser tabular | Só para páginas candidatas. |
| `image_count` | int | não | `2` | PyMuPDF | OCR trigger | |
| `text_char_count` | int | não | `1830` | sistema | OCR trigger | |
| `ocr_required` | bool | não | `false` | regra | review | True se página relevante sem texto. |
| `section_candidates` | string[] | sim | `["Pedidos"]` | segmenter | confidence | Cabeçalhos detectados. |
| `layout_signature` | string | sim | `sha256:...` | sistema | drift | Hash de cabeçalhos/blocos. |
| `parser_version` | string | não | `bpi_extractor_v1` | código | replay | |
| `created_at` | timestamptz | não | `...` | sistema | auditoria | |

### 2.3 `BpiMarkEventNormalized`

Evento pronto para `events.lifecycle_events` e para os serviços de deadlines/alertas.

#### 2.3.1 Identidade e provenance

| Campo | Tipo | Null | Exemplo | Confidence | Dedupe/reconciliação | Notas |
|---|---|---:|---|---:|---|---|
| `id` | uuid | não | `...` | 1.00 | PK | Interno. |
| `source` | enum | não | `bpi_pdf` | 1.00 | filtro | Valor fixo. |
| `jurisdiction` | enum | não | `PT` | 1.00 | matching | Valor fixo para marca nacional PT. |
| `event_type` | enum YAML | não | `refusal_published` | 0.80-1.00 | dedupe | Tem de existir em `bpi_event_taxonomy.yaml`. |
| `priority` | enum | não | `P0` | 1.00 | operação | Herdado da taxonomia. |
| `bulletin_id` | uuid | não | `...` | 1.00 | FK raw | |
| `bulletin_sha256` | hex string | não | `d030...` | 1.00 | dedupe | Prova do PDF. |
| `bulletin_url` | url | não | `https://inpi...` | 1.00 | provenance | Link oficial usado. |
| `bulletin_number` | string | não | `2026/06/26` | 0.90-1.00 | dedupe | Cabeçalho PDF; se só derivado da data, confidence menor. |
| `publication_date` | date | não | `2026-06-26` | 0.95-1.00 | dedupe/deadline | Fonte do prazo PT. |
| `page_number` | int | não | `34` | 0.95-1.00 | dedupe | Página onde o ato aparece. |
| `section_path` | string | não | `REGISTO NACIONAL DE MARCAS > Recusas` | 0.70-1.00 | dedupe | Segmentação hierárquica. |
| `st17_code` | string | sim | `FC` | 0.50-0.90 | taxonomia | Nem sempre ligado diretamente à linha. |
| `raw_text_excerpt` | text | não | `Processo ... arts. ...` | n/a | hash | 500-2000 chars; minimizar dados quando possível. |
| `raw_text_hash` | hex string | não | `...` | 1.00 | dedupe | Hash do excerto normalizado. |
| `parser_name` | string | não | `bpi_mark_parser` | 1.00 | replay | |
| `parser_version` | string | não | `bpi_parser_v1` | 1.00 | replay | |
| `dedupe_key` | string | não | `sha256:...` | 1.00 | unique lógico | Ver secção 4. |
| `parse_confidence` | decimal | não | `0.91` | n/a | auto/review | 0..1. |
| `field_confidence` | json | não | `{process_number:0.99}` | n/a | review | Campo a campo. |
| `quarantine_status` | enum | não | `accepted` | n/a | operação | `accepted`, `review_required`, `quarantined`. |
| `quarantine_reason` | string | sim | `missing_act_date` | n/a | operação | Obrigatório se quarantined. |

#### 2.3.2 Identificadores de marca

| Campo | Tipo | Null | Exemplo | Confidence | Dedupe/reconciliação | Notas |
|---|---|---:|---|---:|---|---|
| `process_number_raw` | string | sim | `N.º 770 255` | 0.95 | audit | Como aparece. |
| `process_number` | string | sim | `770255` | 0.95 | matching forte | Usar para `application_number` quando aplicável. |
| `application_number` | string | sim | `770255` | 0.95 | matching forte | Em pedidos/recusas. |
| `registration_number` | string | sim | `190596` | 0.90 | matching forte | Em renovações/caducidades. |
| `related_process_numbers` | string[] | sim | `["682074"]` | 0.60-0.90 | review | Processos judiciais/relacionados não são marca principal. |
| `trademark_id` | uuid | sim | `...` | reconciliação | FK core | Null se ainda não reconciliado. |
| `reconciliation_status` | enum | não | `matched` | n/a | operação | `matched`, `unmatched`, `conflict`, `review_required`. |
| `match_strength` | enum | sim | `strong_application_number` | n/a | operação | Ver secção 5. |

#### 2.3.3 Datas e prazos

| Campo | Tipo | Null | Exemplo | Confidence | Dedupe/reconciliação | Notas |
|---|---|---:|---|---:|---|---|
| `application_date` | date | sim | `2026-06-02` | 0.95 | core snapshot | Campo `(220)` ou tabela. |
| `registration_date` | date | sim | `2026-06-22` | 0.90 | core snapshot | Concessão/caducidade. |
| `decision_date` | date | sim | `2026-06-22` | 0.90 | lifecycle | Data do despacho/decisão. |
| `dispatch_date` | date | sim | `2026-06-22` | 0.90 | lifecycle | Sinónimo operacional em concessões. |
| `refusal_date` | date | sim | `2026-06-22` | 0.90 | lifecycle | Recusas. |
| `lapse_date` | date | sim | `2025-05-19` | 0.90 | lifecycle | Caducidades. |
| `recordal_date` | date | sim | `2025-05-19` | 0.85 | lifecycle | Averbamentos/transmissões. |
| `surrender_date` | date | sim | `2026-03-10` | 0.85 | lifecycle | Renúncias. |
| `judgment_date` | date | sim | `2025-03-10` | 0.70 | sensitive | Sentenças. |
| `deadline_type` | enum | sim | `opposition_pt` | regra | app.deadlines | Só quando legalmente suportado. |
| `deadline_date` | date | sim | `2026-08-26` | 0.95 | app.deadlines | Para pedido publicado: publicação + 2 meses. |
| `deadline_basis` | string | sim | `CPI art. 226 + 17, BPI notice` | 0.90 | auditoria | Texto curto da base. |

#### 2.3.4 Sinal, classes e produtos/serviços

| Campo | Tipo | Null | Exemplo | Confidence | Dedupe/reconciliação | Notas |
|---|---|---:|---|---:|---|---|
| `word_mark` | string | sim | `MARKEE` | 0.40-0.95 | similarity fallback | Null permitido em figurativas. |
| `mark_feature_hint` | enum | sim | `Word` | 0.50 | core | Inferido; EUIPO tem prioridade. |
| `nice_classes` | int[] | sim | `[42]` | 0.80-0.95 | matching secundário | Validar 1..45. |
| `goods_services_text` | text | sim | `Classe 42: ...` | 0.70-0.90 | audit/search | Texto PT publicado. |
| `goods_services_excerpt` | text | sim | `software as a service...` | 0.70 | UI | Versão truncada. |
| `colour_claim` | string | sim | `preto; verde` | 0.50-0.80 | P2 | Não crítico P0. |
| `vienna_codes` | string[] | sim | `["26.4.3"]` | 0.50-0.85 | P2/logo | Validar formato, não obrigatório. |

#### 2.3.5 Pessoas e entidades

| Campo | Tipo | Null | Exemplo | Confidence | Dedupe/reconciliação | RGPD/notas |
|---|---|---:|---|---:|---|---|
| `applicant_name` | string | sim | `EMPRESA X, LDA` | 0.70-0.95 | core.holders candidate | Minimizar; não enriquecer contactos. |
| `applicant_name_normalized` | string | sim | `EMPRESA X LDA` | 0.70-0.95 | matching fraco | Unicode/whitespace/case. |
| `applicant_country` | char(2) | sim | `PT` | 0.90 | matching | ISO alpha-2. |
| `holder_name` | string | sim | `...` | 0.70-0.95 | core.holders | Atual/titular conforme tabela. |
| `holder_country` | char(2) | sim | `PT` | 0.90 | matching | |
| `previous_holder_name` | string | sim | `ANTIGO TITULAR, S.A.` | 0.70-0.90 | chain of title | Transmissões. |
| `previous_holder_country` | char(2) | sim | `PT` | 0.85 | chain | |
| `new_holder_name` | string | sim | `NOVO TITULAR, LDA` | 0.70-0.90 | chain/current candidate | Transmissões. |
| `new_holder_country` | char(2) | sim | `PT` | 0.85 | chain | |
| `representative_name` | string | sim | null | 0.50 | P2 | Não extrair listas gerais de procuradores. |
| `person_type_hint` | enum | sim | `legal` | 0.50-0.80 | prospection filter | `legal`, `natural`, `unknown`; unknown tratado como natural para prospeção. |

#### 2.3.6 Legal basis, atos especiais e texto livre

| Campo | Tipo | Null | Exemplo | Confidence | Dedupe/reconciliação | Notas |
|---|---|---:|---|---:|---|---|
| `legal_basis_text` | text | sim | `arts. 209.º, n.º 1, al. a)...` | 0.80 | dedupe/refusal alert | Manter original normalizado. |
| `legal_basis_structured` | json | sim | `[{article:"209", number:"1", subparagraph:"a"}]` | 0.50-0.85 | analytics | Regex conservador; nunca substituir texto. |
| `observations` | text | sim | `TRANSMISSÃO TOTAL` | 0.70 | dedupe hash | Texto livre minimizado. |
| `recordal_subtype` | enum | sim | `invalidity_request` | 0.50-0.85 | alert routing | Para `recordal_other`. |
| `scope` | enum | sim | `partial` | 0.70 | lifecycle | `total`, `partial`, `unknown`. |
| `affected_nice_classes` | int[] | sim | `[30]` | 0.50-0.80 | scope change | Renúncia parcial. |
| `affected_goods_services_text` | text | sim | `...` | 0.50-0.80 | audit | P1/P2. |
| `changed_elements` | string[] | sim | `["sinal"]` | 0.50-0.80 | versioning | Alteração não essencial. |
| `before_value` | text | sim | null | 0.30-0.70 | versioning | Só com texto explícito. |
| `after_value` | text | sim | `novo sinal...` | 0.50-0.80 | versioning | Só com texto explícito. |
| `court_name` | string | sim | `Tribunal da Propriedade Intelectual` | 0.50-0.80 | sensitive | Mascarar na UI comum se necessário. |
| `court_case_number` | string | sim | null | 0.50 | sensitive | Evitar por defeito; preferir hash. |
| `court_case_number_hash` | string | sim | `sha256:...` | 0.90 | dedupe | Salt aplicacional. |
| `claimant_name` | string | sim | null | 0.50 | sensitive/prospection off | Só guardar claro se base legal. |
| `defendant_name` | string | sim | null | 0.50 | sensitive/prospection off | Idem. |
| `outcome` | enum | sim | `refusal_maintained` | 0.40-0.75 | lifecycle | Inferência; review se crítico. |

## 3. Nullability por event_type

Legenda: R = required; O = optional/recommended; N = normally null; Q = required or quarantine.

| Campo/evento | application | grant | refusal | renewal | lapse_fee | assignment | surrender | recordal/encumbrance | judgment/revalidation |
|---|---|---|---|---|---|---|---|---|---|
| `application_number` | R | O | O | N | O | O | O | O | O |
| `registration_number` | N | O | N | R | O | O | O | O | O |
| `process_number` | R | R | R | O | R | R | R | R | R |
| `application_date` | R | N | O | N | N | N | N | N | O |
| `registration_date` | N | R | N | N | O | N | O | N | O |
| `refusal_date` | N | N | Q | N | N | N | N | N | N |
| `lapse_date` | N | N | N | N | R | N | N | N | O |
| `recordal_date` | N | N | N | N | N | R | O | O | O |
| `word_mark` | O | N | N | N | N | N | N | N | N |
| `nice_classes` | O | O | O | N | N | N | O | O | O |
| `legal_basis_text` | N | N | Q | N | N | N | N | O | O |
| `previous_holder_name` | N | N | N | N | N | O | N | N | N |
| `new_holder_name` | N | N | N | N | N | O | N | N | N |
| `observations` | O | O | O | O | O | O | O | O | O |
| `deadline_date` | R | N | N | N | N | N | N | N | N |

## 4. Dedupe contract

### 4.1 Canonical fields

Antes de construir a chave:

- `bulletin_number`: `YYYY/MM/DD`.
- `publication_date`: ISO date.
- `section_path`: acentos removidos, lowercase, espaços colapsados para hash; guardar original à parte.
- `event_type`: YAML canonical.
- `process_or_registration_number`: dígitos normalizados.
- `act_date`: a data específica do ato, se existir.
- `legal_basis`: texto legal normalizado; vazio se não aplicável.
- `observation_hash_16`: primeiros 16 hex de SHA-256 de `observations` normalizado.

### 4.2 Fórmula

```text
semantic_key = join("|", [
  "BPI",
  bulletin_number,
  publication_date,
  section_path_norm,
  event_type,
  primary_number_norm,
  act_date_or_empty,
  legal_basis_norm_or_empty,
  observation_hash_16_or_empty
])

dedupe_key = "sha256:" + sha256(semantic_key)
```

### 4.3 Reprocessamento

| Cenário | Resultado esperado |
|---|---|
| Mesmo PDF, mesma parser_version, mesmo output | no-op |
| Mesmo PDF, parser_version nova, mesma semantic_key, payload melhor | criar nova parse version e marcar anterior como superseded/current=false |
| Mesmo PDF, mesma key, payload conflitua | `review_required` |
| Mesma data, URL diferente, SHA igual | adicionar URL alternativa, sem duplicar bulletin |
| Mesma data, SHA diferente | criar `archive_version=2`, quarantine até revisão |
| Evento sem número forte | `unknown_bpi_mark_event` ou `review_required`, nunca alertar automaticamente |

## 5. Reconciliation contract

### 5.1 Matching strengths

| `match_strength` | Regra | Auto-match |
|---|---|---:|
| `strong_application_number` | `application_number == core.trademarks.application_number` e jurisdição PT | sim |
| `strong_registration_number` | `registration_number == core.trademarks.registration_number` e jurisdição PT | sim |
| `strong_process_number_as_application` | `process_number == application_number` | sim se data compatível |
| `medium_number_classes_country` | número + país + classes coincidem | review se conflito |
| `weak_mark_date_holder` | sinal + data + titular semelhante | não |
| `none` | sem candidato | não |

### 5.2 Source priority por campo

| Campo | Prioridade | Justificação |
|---|---|---|
| `publication_date`, `bulletin_number`, `page_number`, `raw_text_excerpt` | BPI | Prova oficial de publicação. |
| `deadline_date` para oposição PT | BPI + regra CPI | Prazo nasce da publicação BPI observada. |
| `legal_basis_text` de recusa | BPI | Texto CPI publicado. |
| `status`, `renewal_status`, `update_date` | EUIPO/TMview | Snapshot normalizado/current. |
| `word_mark`, `mark_feature`, media | EUIPO/TMview preferido; BPI fallback | BPI pode omitir/fragmentar sinal figurativo. |
| `nice_classes`, `goods_services` | EUIPO/TMview para pesquisa; BPI para texto publicado PT | Preservar ambos se divergem. |
| `holder current` | EUIPO/TMview/core current; BPI para cadeia histórica | Transmissões BPI têm antigo/novo titular. |

### 5.3 Conflict payload

```json
{
  "conflict_type": "field_value_mismatch",
  "field": "nice_classes",
  "bpi_value": [42],
  "euipo_value": [41, 42],
  "source_priority": "preserve_both_bpi_publication_euipo_current",
  "resolution_status": "review_required",
  "created_from_event_id": "uuid"
}
```

## 6. Confidence contract

### 6.1 Campo a campo

`field_confidence` deve ter valores 0..1 para todos os campos críticos extraídos. Regras iniciais:

- Regex com marcador ST.17 explícito e valor válido: 0.95-0.99.
- Valor derivado de tabela com cabeçalho alinhado: 0.85-0.95.
- Valor derivado de texto livre: 0.50-0.80.
- Valor inferido por subtipo/alias: 0.40-0.75.
- OCR: teto inicial 0.75 sem revisão.
- Campo ausente mas opcional: omitir ou null sem penalizar.
- Campo ausente mas required: confidence global reduzida e quarantine/review.

### 6.2 Global

```json
{
  "parse_confidence": 0.91,
  "confidence_components": {
    "section_recognized": 0.20,
    "valid_number": 0.20,
    "valid_event_date": 0.15,
    "bulletin_page_consistent": 0.15,
    "nice_classes_valid": 0.10,
    "table_headers_aligned": 0.10,
    "critical_text_present": 0.10
  }
}
```

## 7. Event payload examples

### 7.1 Pedido publicado P0

```json
{
  "source": "bpi_pdf",
  "jurisdiction": "PT",
  "event_type": "application_published",
  "priority": "P0",
  "publication_date": "2026-06-26",
  "bulletin_number": "2026/06/26",
  "bulletin_url": "https://inpi.justica.gov.pt/LinkClick.aspx?fileticket=iZmwYAaF9PI=&portalid=6",
  "bulletin_sha256": "d030966f37bbe0a2ee4a46c21d3b5c6e227d0a177aed8c232cb3f4ea34a305bd",
  "page_number": 14,
  "section_path": "REGISTO NACIONAL DE MARCAS > Pedidos",
  "process_number": "770255",
  "application_number": "770255",
  "application_date": "2026-06-02",
  "word_mark": null,
  "nice_classes": [42],
  "colour_claim": "preto; verde",
  "vienna_codes": ["26.4.3", "26.4.5", "26.4.12", "29.1.3"],
  "deadline_type": "opposition_pt",
  "deadline_date": "2026-08-26",
  "deadline_basis": "Publicação BPI; aviso cita CPI arts. 226.º e 17.º",
  "raw_text_excerpt": "(210) 770255 ...",
  "dedupe_key": "sha256:example",
  "parser_version": "bpi_parser_v1",
  "parse_confidence": 0.91,
  "field_confidence": {
    "application_number": 0.99,
    "application_date": 0.99,
    "nice_classes": 0.90,
    "deadline_date": 0.95
  },
  "reconciliation_status": "unmatched",
  "match_strength": null
}
```

### 7.2 Recusa publicada P0

```json
{
  "source": "bpi_pdf",
  "jurisdiction": "PT",
  "event_type": "refusal_published",
  "priority": "P0",
  "publication_date": "2026-06-26",
  "bulletin_number": "2026/06/26",
  "page_number": 34,
  "section_path": "REGISTO NACIONAL DE MARCAS > Recusas",
  "process_number": "756704",
  "application_date": "2025-11-07",
  "refusal_date": "2026-06-22",
  "nice_classes": [39],
  "legal_basis_text": "arts. 209.º, n.º 1, al. a); 231.º, n.º 1, al. b); 229.º, n.º 5 CPI 2018",
  "legal_basis_structured": [
    {"article": "209", "number": "1", "subparagraph": "a", "law": "CPI 2018"},
    {"article": "231", "number": "1", "subparagraph": "b", "law": "CPI 2018"},
    {"article": "229", "number": "5", "law": "CPI 2018"}
  ],
  "raw_text_excerpt": "Processo 756704 ...",
  "dedupe_key": "sha256:example",
  "parser_version": "bpi_parser_v1",
  "parse_confidence": 0.93,
  "field_confidence": {
    "process_number": 0.99,
    "refusal_date": 0.95,
    "legal_basis_text": 0.90,
    "legal_basis_structured": 0.75
  },
  "quarantine_status": "accepted",
  "reconciliation_status": "matched",
  "match_strength": "strong_application_number"
}
```

### 7.3 Transmissão P1

```json
{
  "source": "bpi_pdf",
  "jurisdiction": "PT",
  "event_type": "assignment_recorded",
  "priority": "P1",
  "publication_date": "2025-05-22",
  "bulletin_number": "2025/05/22",
  "page_number": 79,
  "section_path": "REGISTO NACIONAL DE MARCAS > Transmissões",
  "process_number": "example",
  "recordal_date": "2025-05-19",
  "previous_holder_name": "ANTIGO TITULAR, S.A.",
  "previous_holder_country": "PT",
  "new_holder_name": "NOVO TITULAR, LDA",
  "new_holder_country": "PT",
  "observations": "TRANSMISSÃO TOTAL",
  "raw_text_excerpt": "...",
  "dedupe_key": "sha256:example",
  "parser_version": "bpi_parser_v1",
  "parse_confidence": 0.86,
  "quarantine_status": "accepted",
  "reconciliation_status": "matched",
  "match_strength": "strong_registration_number"
}
```

### 7.4 Penhora P1 com minimização

```json
{
  "source": "bpi_pdf",
  "jurisdiction": "PT",
  "event_type": "encumbrance_recorded",
  "priority": "P1",
  "publication_date": "2026-06-26",
  "bulletin_number": "2026/06/26",
  "page_number": 38,
  "section_path": "REGISTO NACIONAL DE MARCAS > Outros Averbamentos",
  "process_number": "example",
  "recordal_subtype": "seizure_recordal",
  "court_name": "Tribunal ...",
  "court_case_number": null,
  "court_case_number_hash": "sha256:salted-example",
  "claimant_name": null,
  "defendant_name": null,
  "observations": "AVERBAMENTO DA PENHORA PROCESSO Nº [mascarado]",
  "raw_text_excerpt": "excerto minimizado",
  "parse_confidence": 0.74,
  "quarantine_status": "review_required",
  "quarantine_reason": "sensitive_legal_process"
}
```

## 8. Mapping para Markee

### 8.1 `events.lifecycle_events`

| Campo Markee | Origem BPI contract |
|---|---|
| `trademark_id` | `trademark_id` depois de reconciliação; se null, evento fica staging/review. |
| `event_type` | `event_type`. |
| `event_date` | prioridade: data específica do ato (`refusal_date`, `recordal_date`, etc.); fallback `publication_date`. |
| `deadline_date` | `deadline_date` quando calculado. |
| `description` | resumo minimizado: tipo + processo + boletim/página. |
| `source` | `bpi_pdf`. |
| `source_reference` | `bulletin_number + ":" + page_number + ":" + process_number`. |
| `raw_data` | payload `BpiMarkEventNormalized` completo ou link para staging. |

### 8.2 `core.documents`

| Campo Markee | Origem BPI contract |
|---|---|
| `document_type` | `bpi_bulletin`. |
| `source_url` | `source_url`. |
| `storage_path` | `storage_path`. |
| `file_hash` | `sha256`. |
| `publication_date` | `publication_date`. |
| `language` | `pt`. |
| `metadata` | headers, page_count, text_char_count, image_count, archive_version. |

### 8.3 Deadlines

| Evento | deadline_type | Regra | Confidence |
|---|---|---|---|
| `application_published` | `opposition_pt` | `publication_date + P2M` | alta quando BPI/date/page válidos |
| `refusal_published` | `refusal_review_watch` | sem countdown final P0; requer configuração jurídica | média |
| `renewal_published` | nenhum por defeito | confirma evento; deadlines vêm de expiry/EUIPO | n/a |
| `lapse_fee_nonpayment` | nenhum por defeito | alerta estado/caducidade | n/a |

## 9. Quarantine/review contract

Campos mínimos de review:

| Campo | Tipo | Descrição |
|---|---|---|
| `review_id` | uuid | Identificador. |
| `event_id` | uuid | Evento/staging. |
| `reason` | enum | `low_confidence`, `missing_required_field`, `layout_drift`, `source_conflict`, `sensitive_personal_data`, `unknown_section`. |
| `severity` | enum | `info`, `warning`, `critical`. |
| `suggested_action` | string | Aceitar, corrigir campo, mascarar, rejeitar. |
| `review_payload` | json | Campos relevantes e excerto. |
| `created_at` | timestamptz | Auditoria. |
| `resolved_at` | timestamptz | Nullable. |
| `resolved_by` | uuid | Nullable. |

Eventos em quarantine não podem criar alertas externos nem prospeção.

## 10. Taxonomia e compatibilidade

- Lista canónica de event types: `config/bpi_event_taxonomy.yaml`.
- Um parser só pode emitir `event_type` existente na taxonomia.
- Eventos novos vão para `unknown_bpi_mark_event` com `section_path`, página e texto.
- Alterar required fields na taxonomia exige nova `parser_version` e fixtures.

## 11. Campos que NÃO entram no MVP

- Telefones, emails e websites das listas finais de procuradores autorizados.
- Moradas completas de titulares extraídas do BPI, salvo necessidade jurídica explícita.
- Números judiciais em claro por defeito.
- Imagens de sinais figurativos extraídas por OCR/computer vision do PDF.
- Dados de patentes, desenhos/modelos e outras modalidades, exceto para segmentação/ignorar corretamente.

## 12. Testes de contrato

A Forja deve implementar testes TDD para:

1. YAML parseável e todos os `event_type` únicos.
2. Todos os event types P0 têm `required_fields` e `parser_strategy`.
3. Payload P0 válido passa JSON schema/Pydantic.
4. Payload sem `publication_date` em `application_published` falha.
5. `deadline_date` = +2 meses em pedidos publicados.
6. Dedupe key estável entre duas execuções.
7. Mesma data com SHA diferente gera `archive_version=2` e review.
8. Evento confidence <0.65 fica quarantined e não gera alerta.
9. `court_case_number` em penhora é null por defeito e `court_case_number_hash` é usado para dedupe.
10. `unknown_bpi_mark_event` aceita secções novas sem quebrar o pipeline.
