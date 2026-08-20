# ADR 0003: INPI/BPI Strategy — PDF Parsing with TMview Fallback

- **Status:** accepted
- **Date:** 2026-07-24
- **Deciders:** João
- **Replaces:** N/A (decisão inicial)

---

## Context

O INPI Portugal (Instituto Nacional da Propriedade Industrial) não oferece uma API pública para consulta de marcas. O acesso a dados de marcas portuguesas depende de:

1. **BPI (Boletim da Propriedade Industrial)** — PDF diário publicado em `inpi.justica.gov.pt`. Fonte autoritativa para eventos legais (despachos, oposições, renovações, caducidades).
2. **Portal de pesquisa legacy** — `servicosonline.inpi.pt/pesquisas/main/marcas.jsp`. HTML de 2008, sem API.
3. **TMview (via EUIPO API)** — agrega dados do INPI como participante. Cobre pesquisa e similaridade, mas não eventos legais com a granularidade do BPI.

Adicionalmente, `inpi.justica.gov.pt` tem historial de indisponibilidade intermitente.

A questão: como obter dados de marcas portuguesas de forma fiável, considerando que a fonte primária (INPI) não tem API e o site oficial é instável?

## Decision

Estratégia em três camadas:

### Camada 1 — Pesquisa e Similaridade: EUIPO/TMview API

Para pesquisa de marcas, deteção de similaridade, e dados básicos (nome, classes, titular), usamos a **EUIPO Trademark Search API**, que indexa os dados do INPI via TMview.

**Justificação:** O INPI é participante TMview. Os dados estão disponíveis na EUIPO API com a mesma qualidade que estariam numa API do INPI. A EUIPO API é estável, documentada, e já é a fonte primária para EUTM.

### Camada 2 — Eventos Legais: BPI PDF Parsing

Para eventos do ciclo de vida (oposições, renovações, caducidades, transmissões), a única fonte autoritativa é o BPI. Fazemos parsing diário do PDF com `pymupdf` + `pdfplumber`.

**Justificação:** O BPI é o diário oficial. A data de publicação no BPI inicia o prazo de oposição de 2 meses para marcas PT. Nenhuma outra fonte tem esta informação com este nível de detalhe e autoridade legal.

### Camada 3 — Fallback: INPI Search Portal (Playwright)

Quando a EUIPO API não devolve resultados suficientes para uma pesquisa fonética em português (ex: pesquisa por sonoridade que o RSQL da EUIPO não cobre bem), usamos o portal legacy do INPI via Playwright.

**Justificação:** O portal legacy do INPI tem pesquisa fonética built-in otimizada para português. É um fallback, não a via primária. O scraping é frágil e deve ser usado com moderação.

## Alternatives Considered

### Alternativa A: Scraping do portal INPI como fonte primária

**Rejeitada.** O portal é HTML de 2008, sem estrutura semântica, propenso a breaking changes sem aviso. Scraping como fonte primária é uma receita para manutenção constante.

### Alternativa B: Esperar pela API do INPI (Signa.io Q3 2026)

**Rejeitada como estratégia única.** A Signa.io lista "INPI Portugal API — Coming Soon Q3 2026", mas não há anúncio oficial do INPI. Não podemos depender de um produto third-party sem data confirmada. Se a API sair, será integrada como fonte adicional, não como substituição.

### Alternativa C: Ignorar o BPI e usar só TMview

**Rejeitada.** O TMview não tem eventos legais com a granularidade do BPI. Perderíamos:
- Datas exatas de publicação de despachos (crítico para prazos de oposição)
- Renovações e caducidades em tempo real
- Transmissões de titularidade

## Mitigação da Instabilidade do inpi.justica.gov.pt

| Problema | Mitigação |
|---|---|
| Site offline | Retry policy agressiva (5 tentativas, backoff 30s). O BPI é diário — perder um dia não é crítico, recupera-se no dia seguinte. |
| PDF muda de formato | Parser com testes de regressão. Snapshots de PDFs de exemplo no repositório de testes. |
| PDF publicado em `/en-gb/` | URL fixa no config. Se mudar, é uma alteração de configuração, não de código. |
| Bloqueio de IP | User-Agent respeitoso, rate limit conservador (5 req/min). Se bloquearem, usamos o portal legacy como fallback para o dia. |

## Consequences

### Positivas

- **Cobertura completa.** Pesquisa + eventos legais, cada um pela fonte mais adequada.
- **Resiliência.** Se uma fonte falha, as outras continuam a funcionar.
- **Baixo acoplamento.** Cada fonte é um serviço independente. Adicionar a API do INPI no futuro não requer reescrever as outras.

### Negativas

- **3 code paths para dados PT.** Complexidade de manutenção. Cada fonte tem o seu parser, autenticação, e retry logic.
- **PDF parsing é frágil.** O formato do BPI pode mudar. Precisamos de testes de regressão com PDFs reais.
- **Latência.** Dados PT chegam por duas vias: TMview (via EUIPO API, quase em tempo real) e BPI (diário, com 1 dia de atraso). Para eventos legais, o atraso de 1 dia é aceitável — o prazo de oposição são 2 meses.

## References

- [SOURCES_INVENTORY.md](../SOURCES_INVENTORY.md) — Secção 3 (INPI Portugal)
- [config/sources.yaml](../../config/sources.yaml) — Configuração `inpi_bpi` e `inpi_search_portal`
- [SCHEMA_DESIGN.md](../SCHEMA_DESIGN.md) — `events.lifecycle_events`
