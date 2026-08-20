# ADR 0001: PostgreSQL Schemas — raw, core, events, app

- **Status:** accepted
- **Date:** 2026-07-24
- **Deciders:** João
- **Replaces:** N/A (decisão inicial de arquitetura)

---

## Context

O markee lida com dados de múltiplas fontes externas (EUIPO API, INPI BPI PDFs, EUTM Download XML) que precisam de ser ingeridos, normalizados, e expostos a utilizadores via API. Os dados têm naturezas diferentes:

1. **Respostas brutas de APIs** — imutáveis, volumosas, com utilidade decrescente ao longo do tempo (auditoria e reprocessamento).
2. **Entidades de domínio** — marcas, titulares, representantes, classes de Nice. Dados normalizados, relacionais, com integridade referencial.
3. **Eventos legais** — oposições, renovações, caducidades. Dados temporais com deadlines.
4. **Dados de aplicação** — utilizadores, watchlists, alertas, subscrições. Dados que a aplicação lê e escreve diretamente.

A questão: como organizar estas entidades na base de dados?

## Decision

Usamos **4 schemas PostgreSQL separados** dentro da mesma base de dados:

| Schema | Propósito | Exemplos |
|---|---|---|
| `raw` | Respostas originais das APIs | `api_responses` |
| `core` | Entidades de domínio normalizadas | `trademarks`, `holders`, `representatives`, `nice_classes` |
| `events` | Eventos legais do ciclo de vida | `lifecycle_events` |
| `app` | Dados da aplicação | `users`, `watchlists`, `alerts`, `subscriptions` |

## Alternatives Considered

### Alternativa A: Base de dados única, schema `public` para tudo

**Rejeitada.** Misturar respostas raw (que podem ser truncadas) com dados de negócio no mesmo namespace é confuso. Políticas de retenção diferentes seriam impossíveis de aplicar. Permissões granulares também.

### Alternativa B: Bases de dados separadas (raw_db, core_db, app_db)

**Rejeitada.** Complexidade operacional desnecessária para um sistema self-hosted. Foreign keys entre schemas do mesmo database funcionam; entre databases diferentes requerem FDW ou lógica aplicacional. Para a escala do markee, schemas são suficientes.

### Alternativa C: Schema único com prefixos nas tabelas (raw_, core_, app_)

**Rejeitada.** Funciona, mas schemas PostgreSQL oferecem namespacing real, search_path configurável por role, e isolamento de permissões que prefixos não dão.

## Consequences

### Positivas

- **Separação clara de responsabilidades.** Um developer novo sabe exatamente onde cada entidade vive.
- **Políticas de retenção diferentes.** `raw` pode ser truncado após 90 dias sem afetar `core` ou `app`.
- **Permissões granulares.** A role `markee_api` lê `core` e `events`, escreve em `app`, e nunca toca em `raw`. A role `markee_worker` escreve em `raw`, `core` e `events`, lê de `app`.
- **Backups seletivos.** `app` precisa de backups frequentes (dados de utilizador). `raw` não precisa de backup — é efémero.
- **Search_path por role.** `markee_api` vê `app` primeiro; `markee_worker` vê `core` primeiro.

### Negativas

- **Foreign keys cross-schema.** PostgreSQL suporta, mas é menos comum e requer qualificação explícita (`REFERENCES core.trademarks(id)`).
- **Mais objetos para gerir.** 4 schemas em vez de 1. Migrações Alembic precisam de especificar o schema alvo.
- **Curva de aprendizagem.** Quem não conhece o padrão pode estranhar.

## References

- [PostgreSQL Schemas Documentation](https://www.postgresql.org/docs/15/ddl-schemas.html)
- [SCHEMA_DESIGN.md](../SCHEMA_DESIGN.md) — DDL completo
- [DATA_DICTIONARY.md](../DATA_DICTIONARY.md) — Catálogo de entidades
