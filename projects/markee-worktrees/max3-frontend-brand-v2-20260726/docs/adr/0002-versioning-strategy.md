# ADR 0002: Versioning Strategy — Never Delete, Always Append

- **Status:** accepted
- **Date:** 2026-07-24
- **Deciders:** João
- **Replaces:** N/A (decisão inicial)

---

## Context

O markee ingere dados de fontes externas (EUIPO API, INPI BPI) que atualizam o estado das marcas ao longo do tempo. Uma marca pode mudar de estado (APPLICATION_PUBLISHED → REGISTERED), mudar de titular, ter oposições, ser renovada, ou caducar.

A questão: como preservar o histórico destas alterações?

Uma abordagem ingénua seria fazer UPDATE na linha da marca em `core.trademarks`. Mas isso destrói o estado anterior — não saberíamos que a marca esteve em APPLICATION_PUBLISHED antes de REGISTERED, nem quando.

## Decision

**Nunca eliminar versões anteriores. Sempre criar novas versões.**

Implementação:

1. **Tabela `core.trademark_versions`** — cada alteração a uma marca gera uma nova linha nesta tabela.
2. **Snapshot completo** — cada versão guarda um JSONB com o estado completo da marca naquele momento.
3. **Diff entre versões** — cada versão (exceto a primeira) inclui um `diff_from_previous` que descreve exatamente o que mudou.
4. **Tabela `core.trademarks` mantém o estado atual** — a linha principal é atualizada com o estado mais recente, mas a versão anterior é preservada em `trademark_versions`.

Fluxo:

```
Polling descobre marca X com status=REGISTERED (antes era APPLICATION_PUBLISHED)
  → INSERT INTO core.trademark_versions (snapshot, diff_from_previous, change_type='status_change')
  → UPDATE core.trademarks SET status='REGISTERED', updated_at=now()
```

## Alternatives Considered

### Alternativa A: Audit table com triggers

**Rejeitada.** Triggers são opacos, difíceis de testar, e não capturam a semântica da alteração (change_type, change_source). Queremos lógica de versão explícita no código da aplicação.

### Alternativa B: Event sourcing puro (só versions, sem current state)

**Rejeitada.** Para queries de leitura (listar marcas ativas, pesquisar por status), ter de reconstruir o estado atual a partir do histórico é ineficiente. A tabela `trademarks` como "current state" é um índice materializado natural.

### Alternativa C: Temporal tables (PostgreSQL 17+)

**Rejeitada.** PostgreSQL 15 é o target. Temporal tables nativas só chegaram em versões experimentais. Podemos migrar no futuro.

## Consequences

### Positivas

- **Auditabilidade total.** Sabemos exatamente quando e porquê cada campo mudou.
- **Reprocessamento seguro.** Se um parsing do BPI introduzir um erro, podemos reverter para a versão anterior e reprocessar.
- **Análise temporal.** Podemos responder a perguntas como "quantas marcas passaram de APPLICATION_PUBLISHED para REGISTERED em julho 2026?"
- **Diff legível por humanos.** O campo `diff_from_previous` mostra exatamente o que mudou, sem precisar de comparar JSONBs manualmente.

### Negativas

- **Espaço em disco.** Cada versão duplica o estado completo da marca. Para 1M de marcas com 5 versões cada, são ~5M de linhas. Com JSONB comprimido, estimamos ~2KB por versão → ~10GB. Aceitável.
- **Complexidade de escrita.** Cada atualização requer duas operações (INSERT version + UPDATE current). Isto é encapsulado no serviço, não exposto ao código da API.

## Implementation Notes

- `version_number` é sequencial por marca (1, 2, 3...), não global.
- `change_source` identifica a origem: `euipo_poll`, `bpi_parse`, `manual`.
- `change_type` classifica a alteração: `status_change`, `owner_change`, `renewal`, `opposition`, `expiry`, `classification_change`.
- O diff é gerado com `deepdiff` (Python) ou equivalente — compara o snapshot novo com o anterior e produz um JSON com `added`, `removed`, `changed`.

## References

- [DATA_DICTIONARY.md](../DATA_DICTIONARY.md) — `core.trademark_versions`
- [SCHEMA_DESIGN.md](../SCHEMA_DESIGN.md) — DDL da tabela
