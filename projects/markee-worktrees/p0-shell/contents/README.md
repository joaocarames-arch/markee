# Markee contents

Pasta editorial/UI canónica para copy, hierarquia de interface, estados e blocos reutilizáveis do Markee.

Contrato de entrada:

- [../docs/SITEMAP.md](../docs/SITEMAP.md) — rotas, estados e navegação alvo.
- [../docs/REQUIREMENTS.md](../docs/REQUIREMENTS.md) — requisitos, gates P0/admin/BPI e claims permitidos.
- [../BRAND_MANUAL.md](../BRAND_MANUAL.md) — voz, marca visual e tom.

Como usar:

1. Ler [CONTENT_PRINCIPLES.md](./CONTENT_PRINCIPLES.md) antes de escrever qualquer copy pública.
2. Consultar [SITEMAP_CONTENT_MATRIX.md](./SITEMAP_CONTENT_MATRIX.md) para confirmar objetivo, estado, CTA e blocos por rota.
3. Usar [UI_BLOCKS.md](./UI_BLOCKS.md) como catálogo canónico. Não criar blocos novos sem atualizar este ficheiro.
4. Abrir o documento de página em [pages/](./pages/) para copy, estados e microcopy.
5. Validar termos em [GLOSSARY.md](./GLOSSARY.md).

Marcas internas de estado:

- `[IMPLEMENTED]` — existe código e teste local para o comportamento essencial.
- `[PARTIAL]` — existe parte funcional, mas falta UI, teste, integração real, contrato ou política.
- `[PLANNED]` — alvo decidido, sem implementação suficiente.
- `[BLOCKED]` — depende de decisão, schema, validação legal, credencial ou gates.
- `[OPEN DECISION]` — produto ainda não decidiu.

Estas marcas são internas. Nunca aparecem como copy pública.

Princípios editoriais rápidos:

- Uma ação principal por página, com a exceção legal de consentimento (`Aceitar todos` / `Apenas necessários` / `Configurar` são opções equivalentes em RGPD).
- Claims factuais, com fonte/estado quando houver dependência.
- BPI automatizado fica `[BLOCKED]`/NO-GO até `BPI-GATE-01..16`.
- Stripe real, envios de alertas, deadlines BPI e cobertura completa nunca são afirmados como operacionais sem evidência.
- Tabelas para densidade operacional; cards só para decisão rápida.

Mapa dos documentos:

- [CONTENT_PRINCIPLES.md](./CONTENT_PRINCIPLES.md) — voz, terminologia, claims, acessibilidade e microcopy.
- [SITEMAP_CONTENT_MATRIX.md](./SITEMAP_CONTENT_MATRIX.md) — matriz rota → objetivo → mensagem → CTA → estado → blocos.
- [UI_BLOCKS.md](./UI_BLOCKS.md) — blocos públicos, produto e admin P0 (catálogo canónico).
- [GLOSSARY.md](./GLOSSARY.md) — termos canónicos.
- [pages/PUBLIC_LANDING.md](./pages/PUBLIC_LANDING.md) — landing e anchors públicas.
- [pages/AUTH_ONBOARDING.md](./pages/AUTH_ONBOARDING.md) — login, registo e onboarding inicial.
- [pages/DASHBOARD.md](./pages/DASHBOARD.md) — painel e shell privada.
- [pages/SEARCH_MARK_DETAIL.md](./pages/SEARCH_MARK_DETAIL.md) — pesquisa e detalhe de marca.
- [pages/WATCHLISTS_ALERTS_DEADLINES.md](./pages/WATCHLISTS_ALERTS_DEADLINES.md) — vigilâncias, alertas e prazos.
- [pages/ADMIN_PORTAL.md](./pages/ADMIN_PORTAL.md) — portal admin P0 e gates BPI.
- [pages/SETTINGS_BILLING.md](./pages/SETTINGS_BILLING.md) — conta, plano e billing parcial/mock.
- [pages/LEGAL_ERRORS.md](./pages/LEGAL_ERRORS.md) — páginas legais, cookies, erros e estados.
