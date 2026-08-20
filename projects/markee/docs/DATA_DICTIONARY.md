# Data Dictionary — markee

> Last updated: 2026-07-24
> Covers all entities across raw, core, events, and app schemas.

---

## 1. Marcas (Trademarks) — `core.trademarks`

A registered or pending trademark. The central entity.

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | sistema | NÃO | Identificador interno único |
| `source_id` | `VARCHAR(64)` | NOT NULL | fonte externa | NÃO | ID na fonte de origem (ex: applicationNumber do EUIPO) |
| `jurisdiction` | `VARCHAR(8)` | NOT NULL, CHECK IN ('EU', 'PT', 'WIPO') | fonte externa | NÃO | Jurisdição: EU (EUTM), PT (INPI), WIPO (internacional) |
| `application_number` | `VARCHAR(32)` | UNIQUE, NOT NULL | EUIPO/INPI | NÃO | Número de pedido oficial |
| `registration_number` | `VARCHAR(32)` | UNIQUE | EUIPO/INPI | SIM | Número de registo (só após concessão) |
| `word_mark` | `VARCHAR(512)` | NOT NULL | EUIPO/INPI | NÃO | Texto da marca nominativa |
| `mark_feature` | `VARCHAR(32)` | NOT NULL, DEFAULT 'Word' | EUIPO | NÃO | Tipo: Word, Figurative, 3D, Colour, Sound, etc. |
| `figurative_mark_url` | `TEXT` | | EUIPO/INPI | SIM | URL da imagem da marca figurativa |
| `status` | `VARCHAR(64)` | NOT NULL, INDEXED | EUIPO/INPI | NÃO | Estado atual (REGISTERED, APPLICATION_PUBLISHED, etc.) |
| `status_date` | `TIMESTAMPTZ` | | EUIPO/INPI | SIM | Data da última mudança de estado |
| `application_date` | `DATE` | INDEXED | EUIPO/INPI | SIM | Data do pedido |
| `registration_date` | `DATE` | | EUIPO/INPI | SIM | Data de registo |
| `expiry_date` | `DATE` | INDEXED | EUIPO/INPI | SIM | Data de expiração (10 anos após pedido) |
| `renewal_status` | `VARCHAR(64)` | | EUIPO | SIM | Estado de renovação (RENEWAL_PERIOD_OPEN, etc.) |
| `opposition_period_end` | `DATE` | | EUIPO/BPI | SIM | Fim do prazo de oposição (3 meses EU, 2 meses PT) |
| `update_date` | `TIMESTAMPTZ` | INDEXED | EUIPO | SIM | Última modificação na fonte (usado para polling incremental) |
| `nice_classes` | `INTEGER[]` | | EUIPO/INPI | SIM | Array de classes de Nice |
| `raw_data` | `JSONB` | | fonte externa | SIM | Dados completos da resposta original |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | Data de criação do registo interno |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | Data da última atualização interna |

**Índices:**
- `idx_trademarks_word_mark_trgm` — GIN trigram index on `word_mark` (pg_trgm)
- `idx_trademarks_application_number` — B-tree unique
- `idx_trademarks_status` — B-tree
- `idx_trademarks_expiry_date` — B-tree
- `idx_trademarks_update_date` — B-tree
- `idx_trademarks_nice_classes` — GIN on array

---

## 2. Versões de Marcas — `core.trademark_versions`

Histórico de alterações de cada marca. Nunca se elimina uma versão anterior.

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | sistema | NÃO | Identificador único da versão |
| `trademark_id` | `UUID` | FK → core.trademarks.id, NOT NULL | sistema | NÃO | Marca a que esta versão pertence |
| `version_number` | `INTEGER` | NOT NULL | sistema | NÃO | Número sequencial da versão (1, 2, 3...) |
| `snapshot` | `JSONB` | NOT NULL | sistema | NÃO | Snapshot completo dos campos da marca nesta versão |
| `diff_from_previous` | `JSONB` | | sistema | SIM | Diff JSON entre esta versão e a anterior |
| `change_source` | `VARCHAR(64)` | NOT NULL | sistema | NÃO | Origem da alteração: 'euipo_poll', 'bpi_parse', 'manual' |
| `change_type` | `VARCHAR(32)` | NOT NULL | sistema | NÃO | Tipo: 'status_change', 'owner_change', 'renewal', 'opposition', etc. |
| `raw_response_id` | `UUID` | FK → raw.api_responses.id | sistema | SIM | Resposta da API que originou esta versão |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | Data de criação da versão |

**Índices:**
- `idx_versions_trademark_id` — B-tree
- `idx_versions_trademark_version` — B-tree unique on (trademark_id, version_number)

---

## 3. Titulares (Applicants/Owners) — `core.holders`

Pessoas singulares ou coletivas titulares de marcas.

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | sistema | NÃO | Identificador interno único |
| `source_id` | `VARCHAR(64)` | NOT NULL | EUIPO | NÃO | Identifier na fonte (ex: EUIPO applicant identifier) |
| `name` | `VARCHAR(512)` | NOT NULL, INDEXED (trgm) | EUIPO/INPI | NÃO | Nome do titular |
| `address` | `TEXT` | | EUIPO/INPI | SIM | Morada completa |
| `country` | `CHAR(2)` | | EUIPO/INPI | SIM | Código ISO 3166-1 alpha-2 |
| `type` | `VARCHAR(32)` | CHECK IN ('natural', 'legal') | EUIPO | SIM | Tipo: pessoa singular ou coletiva |
| `raw_data` | `JSONB` | | fonte externa | SIM | Dados completos da resposta original |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |

---

## 4. Representantes (Representatives) — `core.representatives`

Agentes de propriedade industrial / advogados que representam titulares.

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | sistema | NÃO | |
| `source_id` | `VARCHAR(64)` | NOT NULL | EUIPO | NÃO | Identifier na fonte |
| `name` | `VARCHAR(512)` | NOT NULL, INDEXED (trgm) | EUIPO/INPI | NÃO | Nome do representante |
| `address` | `TEXT` | | EUIPO/INPI | SIM | Morada completa |
| `country` | `CHAR(2)` | | EUIPO/INPI | SIM | Código ISO 3166-1 alpha-2 |
| `type` | `VARCHAR(32)` | CHECK IN ('natural', 'legal', 'association') | EUIPO | SIM | |
| `raw_data` | `JSONB` | | fonte externa | SIM | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |

---

## 5. Relação Marca-Titular — `core.trademark_holders`

Tabela de junção N:M entre marcas e titulares.

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `trademark_id` | `UUID` | FK → core.trademarks.id, NOT NULL | sistema | NÃO | |
| `holder_id` | `UUID` | FK → core.holders.id, NOT NULL | sistema | NÃO | |
| `role` | `VARCHAR(32)` | NOT NULL, DEFAULT 'applicant' | EUIPO | NÃO | Papel: applicant, owner, licensee, etc. |
| `since_date` | `DATE` | | EUIPO/INPI | SIM | Data desde que detém este papel |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |

**PK:** (trademark_id, holder_id, role)

---

## 6. Relação Marca-Representante — `core.trademark_representatives`

Tabela de junção N:M entre marcas e representantes.

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `trademark_id` | `UUID` | FK → core.trademarks.id, NOT NULL | sistema | NÃO | |
| `representative_id` | `UUID` | FK → core.representatives.id, NOT NULL | sistema | NÃO | |
| `role` | `VARCHAR(32)` | NOT NULL, DEFAULT 'representative' | EUIPO | NÃO | |
| `since_date` | `DATE` | | EUIPO | SIM | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |

**PK:** (trademark_id, representative_id)

---

## 7. Classes de Nice — `core.nice_classes`

Catálogo de classes da Classificação de Nice.

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | sistema | NÃO | |
| `class_number` | `INTEGER` | UNIQUE, NOT NULL, CHECK (1-45) | WIPO/EUIPO | NÃO | Número da classe (1-34 produtos, 35-45 serviços) |
| `description_pt` | `TEXT` | | WIPO/EUIPO | SIM | Descrição em português |
| `description_en` | `TEXT` | | WIPO/EUIPO | SIM | Descrição em inglês |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |

---

## 8. Produtos e Serviços — `core.goods_services`

Itens específicos dentro de cada classe de Nice, associados a marcas.

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | sistema | NÃO | |
| `trademark_id` | `UUID` | FK → core.trademarks.id, NOT NULL | sistema | NÃO | |
| `nice_class_id` | `UUID` | FK → core.nice_classes.id, NOT NULL | sistema | NÃO | |
| `term` | `TEXT` | NOT NULL | EUIPO/INPI | NÃO | Descrição do produto/serviço |
| `language` | `VARCHAR(8)` | NOT NULL, DEFAULT 'pt' | EUIPO/INPI | NÃO | Língua do termo |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |

---

## 9. Eventos Legais — `events.lifecycle_events`

Eventos do ciclo de vida de uma marca (oposições, renovações, caducidades, etc.).

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | sistema | NÃO | |
| `trademark_id` | `UUID` | FK → core.trademarks.id, NOT NULL, INDEXED | sistema | NÃO | |
| `event_type` | `VARCHAR(64)` | NOT NULL, INDEXED | EUIPO/BPI | NÃO | Tipo: opposition, renewal, expiry, refusal, grant, assignment, etc. |
| `event_date` | `DATE` | NOT NULL | EUIPO/BPI | NÃO | Data do evento |
| `deadline_date` | `DATE` | INDEXED | EUIPO/BPI | SIM | Data limite associada (ex: fim do prazo de oposição) |
| `description` | `TEXT` | | EUIPO/BPI | SIM | Descrição textual do evento |
| `source` | `VARCHAR(32)` | NOT NULL | sistema | NÃO | Fonte: euipo_api, bpi_pdf, eutm_download, manual |
| `source_reference` | `VARCHAR(128)` | | fonte externa | SIM | Referência na fonte (ex: oppositionNumber) |
| `raw_data` | `JSONB` | | fonte externa | SIM | Dados completos do evento na fonte |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |

**Índices:**
- `idx_events_trademark_id` — B-tree
- `idx_events_event_type` — B-tree
- `idx_events_deadline_date` — B-tree
- `idx_events_trademark_type` — B-tree on (trademark_id, event_type)

---

## 10. Documentos — `core.documents`

Documentos oficiais associados a marcas (PDFs do BPI, certidões, etc.).

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | sistema | NÃO | |
| `trademark_id` | `UUID` | FK → core.trademarks.id | sistema | SIM | Marca associada (NULL se for documento genérico como BPI completo) |
| `document_type` | `VARCHAR(64)` | NOT NULL | sistema | NÃO | Tipo: bpi_bulletin, registration_certificate, opposition_filing, etc. |
| `source_url` | `TEXT` | | fonte externa | SIM | URL original do documento |
| `storage_path` | `TEXT` | | sistema | SIM | Caminho no storage local/S3 |
| `file_hash` | `VARCHAR(64)` | | sistema | SIM | SHA-256 do ficheiro |
| `publication_date` | `DATE` | | fonte externa | SIM | Data de publicação do documento |
| `language` | `VARCHAR(8)` | DEFAULT 'pt' | fonte externa | SIM | Língua do documento |
| `metadata` | `JSONB` | | sistema | SIM | Metadados extraídos (páginas, tamanho, etc.) |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |

---

## 11. Prazos (Deadlines) — `app.deadlines`

Prazos calculados e tracking para utilizadores.

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | sistema | NÃO | |
| `user_id` | `UUID` | FK → app.users.id, NOT NULL | sistema | NÃO | Utilizador que segue este prazo |
| `trademark_id` | `UUID` | FK → core.trademarks.id, NOT NULL | sistema | NÃO | |
| `lifecycle_event_id` | `UUID` | FK → events.lifecycle_events.id | sistema | SIM | Evento que originou o prazo |
| `deadline_type` | `VARCHAR(32)` | NOT NULL | sistema | NÃO | Tipo: opposition, renewal, response, grace_period |
| `deadline_date` | `DATE` | NOT NULL, INDEXED | sistema | NÃO | Data limite |
| `warning_date` | `DATE` | | sistema | SIM | Data para primeiro aviso |
| `status` | `VARCHAR(16)` | NOT NULL, DEFAULT 'pending' | sistema | NÃO | pending, warned, completed, missed |
| `notes` | `TEXT` | | utilizador | SIM | Notas do utilizador |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |

---

## 12. Fontes de Dados — `core.sources`

Registo das fontes de dados configuradas.

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | sistema | NÃO | |
| `name` | `VARCHAR(64)` | UNIQUE, NOT NULL | config/sources.yaml | NÃO | Nome único da fonte |
| `source_type` | `VARCHAR(32)` | NOT NULL | config | NÃO | api_rest, xml_bulk, pdf_bulletin, html_scrape |
| `base_url` | `TEXT` | | config | SIM | URL base |
| `auth_method` | `VARCHAR(32)` | | config | SIM | none, oauth2_client_credentials, subscription_portal |
| `is_enabled` | `BOOLEAN` | NOT NULL, DEFAULT true | config | NÃO | Fonte ativa? |
| `priority` | `INTEGER` | NOT NULL, CHECK (>= 1) | config | NÃO | Prioridade (1 = mais alta) |
| `config_snapshot` | `JSONB` | | config | SIM | Snapshot da config no momento do registo |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |

---

## 13. Execuções (Runs) — `core.source_runs`

Registo de cada execução de polling/parsing de fontes.

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | sistema | NÃO | |
| `source_id` | `UUID` | FK → core.sources.id, NOT NULL | sistema | NÃO | |
| `run_type` | `VARCHAR(32)` | NOT NULL | sistema | NÃO | incremental_poll, full_backfill, daily_parse |
| `status` | `VARCHAR(16)` | NOT NULL | sistema | NÃO | running, completed, failed, partial |
| `started_at` | `TIMESTAMPTZ` | NOT NULL | sistema | NÃO | |
| `completed_at` | `TIMESTAMPTZ` | | sistema | SIM | |
| `items_processed` | `INTEGER` | DEFAULT 0 | sistema | SIM | Número de itens processados |
| `items_new` | `INTEGER` | DEFAULT 0 | sistema | SIM | Itens novos |
| `items_updated` | `INTEGER` | DEFAULT 0 | sistema | SIM | Itens atualizados |
| `items_failed` | `INTEGER` | DEFAULT 0 | sistema | SIM | Itens com erro |
| `error_message` | `TEXT` | | sistema | SIM | Mensagem de erro se falhou |
| `cursor_value` | `VARCHAR(128)` | | sistema | SIM | Valor do cursor para a próxima execução (ex: última update_date) |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |

---

## 14. Respostas Raw — `raw.api_responses`

Respostas originais das APIs, preservadas para auditoria e reprocessamento.

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | sistema | NÃO | |
| `source_id` | `UUID` | FK → core.sources.id, NOT NULL | sistema | NÃO | |
| `source_run_id` | `UUID` | FK → core.source_runs.id | sistema | SIM | Execução que originou esta resposta |
| `endpoint` | `TEXT` | NOT NULL | sistema | NÃO | URL completa do endpoint chamado |
| `request_params` | `JSONB` | | sistema | SIM | Parâmetros do pedido |
| `response_status` | `INTEGER` | | sistema | SIM | HTTP status code |
| `response_headers` | `JSONB` | | sistema | SIM | Cabeçalhos da resposta |
| `response_body` | `JSONB` | | sistema | SIM | Corpo da resposta |
| `response_size_bytes` | `INTEGER` | | sistema | SIM | Tamanho da resposta |
| `duration_ms` | `INTEGER` | | sistema | SIM | Duração do pedido em ms |
| `error_message` | `TEXT` | | sistema | SIM | Erro se o pedido falhou |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |

**Índices:**
- `idx_raw_source_id_created` — B-tree on (source_id, created_at DESC)

---

## 15. Utilizadores — `app.users`

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | sistema | NÃO | |
| `email` | `VARCHAR(255)` | UNIQUE, NOT NULL | registo | NÃO | Email do utilizador |
| `hashed_password` | `VARCHAR(255)` | NOT NULL | registo | NÃO | Hash bcrypt da password |
| `full_name` | `VARCHAR(255)` | NOT NULL | registo | NÃO | Nome completo |
| `company_name` | `VARCHAR(255)` | | registo | SIM | Empresa (para profissionais) |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT true | sistema | NÃO | Conta ativa? |
| `is_superuser` | `BOOLEAN` | NOT NULL, DEFAULT false | sistema | NÃO | Superuser? |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |

---

## 16. Watchlists — `app.watchlists`

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | sistema | NÃO | |
| `user_id` | `UUID` | FK → app.users.id, NOT NULL | sistema | NÃO | |
| `name` | `VARCHAR(255)` | NOT NULL | utilizador | NÃO | Nome da watchlist |
| `similarity_threshold` | `FLOAT` | NOT NULL, DEFAULT 0.75, CHECK (0-1) | utilizador | NÃO | Limiar de similaridade para alertas |
| `phonetic_weight` | `FLOAT` | NOT NULL, DEFAULT 0.30, CHECK (0-1) | utilizador | NÃO | Peso da similaridade fonética |
| `class_weight` | `FLOAT` | NOT NULL, DEFAULT 0.20, CHECK (0-1) | utilizador | NÃO | Peso da sobreposição de classes |
| `jurisdictions` | `VARCHAR[]` | NOT NULL, DEFAULT '{EU,PT}' | utilizador | NÃO | Jurisdições a monitorizar |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT true | utilizador | NÃO | Watchlist ativa? |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |

---

## 17. Itens de Watchlist — `app.watchlist_items`

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | sistema | NÃO | |
| `watchlist_id` | `UUID` | FK → app.watchlists.id, NOT NULL | sistema | NÃO | |
| `mark_text` | `VARCHAR(512)` | NOT NULL | utilizador | NÃO | Texto da marca a vigiar |
| `nice_classes` | `INTEGER[]` | | utilizador | SIM | Classes de Nice relevantes |
| `notes` | `TEXT` | | utilizador | SIM | Notas |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |

---

## 18. Alertas — `app.alerts`

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | sistema | NÃO | |
| `user_id` | `UUID` | FK → app.users.id, NOT NULL | sistema | NÃO | |
| `title` | `VARCHAR(512)` | NOT NULL | sistema | NÃO | Título do alerta |
| `body` | `TEXT` | | sistema | SIM | Corpo do alerta |
| `alert_type` | `VARCHAR(32)` | NOT NULL | sistema | NÃO | similarity_match, renewal_due, opposition_filed, etc. |
| `severity` | `VARCHAR(16)` | NOT NULL, DEFAULT 'info' | sistema | NÃO | info, warning, critical |
| `reference_trademark_id` | `UUID` | FK → core.trademarks.id | sistema | SIM | Marca referenciada no alerta |
| `is_read` | `BOOLEAN` | NOT NULL, DEFAULT false | utilizador | NÃO | |
| `is_dismissed` | `BOOLEAN` | NOT NULL, DEFAULT false | utilizador | NÃO | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |

---

## 19. Subscrições — `app.subscriptions`

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | sistema | NÃO | |
| `user_id` | `UUID` | FK → app.users.id, UNIQUE, NOT NULL | sistema | NÃO | |
| `plan_type` | `VARCHAR(32)` | NOT NULL | sistema | NÃO | free, individual, pro, profissional, enterprise |
| `status` | `VARCHAR(16)` | NOT NULL, DEFAULT 'active' | Stripe | NÃO | active, past_due, canceled, trialing |
| `stripe_customer_id` | `VARCHAR(255)` | | Stripe | SIM | |
| `stripe_subscription_id` | `VARCHAR(255)` | | Stripe | SIM | |
| `max_marks` | `INTEGER` | NOT NULL | sistema | NÃO | Limite de marcas do plano |
| `max_users` | `INTEGER` | DEFAULT 1 | sistema | SIM | Limite de utilizadores |
| `max_clients` | `INTEGER` | DEFAULT 0 | sistema | SIM | Limite de clientes (prospecting) |
| `current_period_start` | `TIMESTAMPTZ` | | Stripe | SIM | |
| `current_period_end` | `TIMESTAMPTZ` | | Stripe | SIM | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |

---

## 20. Equipas — `app.teams`

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | sistema | NÃO | |
| `name` | `VARCHAR(255)` | NOT NULL | utilizador | NÃO | |
| `owner_id` | `UUID` | FK → app.users.id, NOT NULL | sistema | NÃO | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |

---

## 21. Portfolios — `app.portfolios`

| Campo | Tipo | Constraints | Fonte | Nullable | Descrição |
|---|---|---|---|---|---|
| `id` | `UUID` | PK, DEFAULT gen_random_uuid() | sistema | NÃO | |
| `team_id` | `UUID` | FK → app.teams.id, NOT NULL | sistema | NÃO | |
| `client_name` | `VARCHAR(512)` | NOT NULL | utilizador | NÃO | Nome do cliente |
| `client_email` | `VARCHAR(255)` | | utilizador | SIM | Email do cliente |
| `notes` | `TEXT` | | utilizador | SIM | |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT now() | sistema | NÃO | |

---

## Notas

- **Tipos PostgreSQL:** `TIMESTAMPTZ` = timestamp with time zone. `JSONB` = binary JSON.
- **UUIDs:** gerados com `gen_random_uuid()` (pgcrypto ou nativo PostgreSQL 13+).
- **Arrays:** `INTEGER[]` e `VARCHAR[]` são arrays nativos PostgreSQL.
- **Trigram indexes:** requerem extensão `pg_trgm`.
- **Nullable SIM** = campo pode ser NULL. **NÃO** = NOT NULL constraint.
