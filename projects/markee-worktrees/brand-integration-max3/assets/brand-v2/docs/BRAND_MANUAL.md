# markee · Brand Manual v2

Manual canónico do wordmark `markee` aprovado pela revisão Max-2. PT-PT. Documenta o estado final dos SVGs em `assets/brand-v2/logos/`.

## 1. Conceito

A marca é um **wordmark apenas tipográfico** em minúsculas — `markee` — sem símbolo, sem pictograma, sem radar, sem círculos decorativos, sem scan-lines. A única concessão cromática é o **último `e` em ciano `#35D0E0`** nas versões cromáticas; nas versões monocromáticas todo o lettering usa uma cor única.

Direção visual: dark premium, ciano como único acento, geometria grotesca vertical, sem gradientes nem glow. Adequada a SaaS jurídico/técnico. Sobriedade acima de estética de startup.

## 2. Construção

- Tipo: `Sora Bold` (Google Fonts, Sora Project Authors, OFL 1.1).
- Conversão: glifos `markee` extraídos via `fontTools.svgPathPen` e gravados como `<path>` em SVG. Não há `<text>`, não há fonte embutida, não há `<image>`, não há `href` externo.
- Métricas (do `wordmark-meta.json`):
  - `units_per_em = 1000`
  - `cap_height = 730`, `x_height = 534`
  - `ascender = 970`, `descender = -290`
  - advances dos glifos (`m`, `a`, `r`, `k`, `e`, `e`): `983, 594, 421, 639, 624, 624`.
  - Side-bearings declarados para `kerning` manual leve quando o asset é regenerado.
- O `viewBox` final dos wordmarks é `0 0 1482 240`, com padding transparente de 20 unidades e avanços sempre expressos nas unidades originais da fonte antes do `scale` do grupo.
- Par `k→e` recebe ajuste explícito de -25 unidades e `e→e` de -10 unidades no gerador versionado, mantendo todos os avanços nas unidades originais da fonte.

## 3. Clearspace (área de proteção)

Definida como **1× a altura do `x` (x-height)** em todas as direções. Em prática: ≥ `x-height` do wordmark renderizado.

- Renderizar a 24 px → clearspace ≥ 24 px.
- Renderizar a 240 px → clearspace ≥ 240 px.

Dentro desta zona nada pode existir: texto, outros logos, bordas de contentores, ícones, vinhetas ou cantos. A regra aplica-se a todas as variantes.

## 4. Tamanhos mínimos

| Contexto | Mínimo recomendado | Limite inferior absoluto |
|---|---|---|
| Digital UI (header, footer) | **24 px** | 20 px |
| Mobile | **24 px** | 20 px |
| Impressão | 8 mm de cap-height | 6 mm |

Notas:
- A 24 px a leitura é clara; o contorno `r` mantém o seu bowl aberto e o `k` mantém a terminação diagonal identificável.
- A 16 px a leitura degrada-se e o wordmark horizontal não é um favicon adequado. O favicon existente permanece canónico até existir e ser aprovado manualmente um ícone próprio.
- Acima de 480 px preferir o ficheiro `markee-brand-sheet.svg` como prova de marca ou os SVGs individuais.

## 5. Variantes e aplicações

SVGs finais em `logos/`:

| Ficheiro | Fundo recomendado | Cor principal | Último `e` |
|---|---|---|---|
| `markee-wordmark-dark.svg` | escuro (`#08090A`, `#111214`, `#1A1C1F`) | `#E8E8E8` | `#35D0E0` |
| `markee-wordmark-light.svg` | claro (`#FFFFFF`, `#F5F5F5`) | `#08090A` | `#35D0E0` |
| `markee-wordmark-mono-white.svg` | escuro / fotografia | `#FFFFFF` | `#FFFFFF` (mono) |
| `markee-wordmark-mono-black.svg` | claro / impressão 1-tinta | `#08090A` | `#08090A` (mono) |

Brand sheet: `logos/markee-brand-sheet.svg` (1600×1100). Compõe hero, 4 variantes, paleta, tipografia UI, tamanhos mínimos.

Drafts e candidatos (preservados, **não usar em produção**):
- `logos/_draft-manual-lettering/`: protótipo v0 com lettering geométrico manual e `k` em lâmina. Não aprovado.
- `logos/candidates/{sora,manrope,space-grotesk}/markee-wordmark-dark.svg`: runners-up durante a triagem. Apenas o Sora foi promovido.

## 6. Cor

### 6.1 Paleta

| Token | HEX | RGB | HSL | Uso |
|---|---|---|---|---|
| Acento | `#35D0E0` | 53, 208, 224 | 187 73% 54% | Último `e` cromático, ícones grandes, foco |
| Acento Hover | `#5EDCF0` | 94, 220, 240 | 190 83% 65% | Estado hover sobre dark |
| Acento Pressed | `#25A8B8` | 37, 168, 184 | 187 65% 43% | Estado pressed (`AA` ≥ 7.00 sobre ink) |
| Ink | `#08090A` | 8, 9, 10 | 180 13% 4% | Background primário, texto sobre claro |
| Charcoal | `#111214` | 17, 18, 20 | 220 8% 7% | Background secundário |
| Surface | `#1A1C1F` | 26, 28, 31 | 210 9% 11% | Cards, painéis |
| Texto Primário | `#E8E8E8` | 232, 232, 232 | 0 0% 91% | Texto sobre dark |
| Texto Secundário | `#8A8D93` | 138, 141, 147 | 213 4% 56% | Captions, metadata |
| Danger | `#E05252` | 224, 82, 82 | 0 70% 60% | Erros (AA 5.22 sobre ink) |
| Success | `#4ADE80` | 74, 222, 128 | 142 69% 58% | Confirmações (AAA 11.44) |
| Warning | (sem cor própria) | — | — | Comunicado por ícone + texto, sobre surface/charcoal, com texto primário. Sem cor cromática adicional. |

### 6.2 Ciano como acento

- O ciano é o único acento cromático. Não duplicar com gradientes ou múltiplas tonalidades em paralelo.
- Sobre fundos escuros (`#08090A` family) o ciano **passa AAA** em todo o contraste testado (10.68 → 9.15).
- Sobre fundos claros `#FFFFFF` e `#E8E8E8` o ciano **falha AA** (1.87 e 1.52). Por isso o ciano **não pode ser usado como texto pequeno sobre branco ou cinza claro** — apenas como elemento gráfico grande (wordmark, ícones, títulos ≥ 24 px).
- Para texto ciano sobre fundo claro usar `#25A8B8` (pressed) só em elementos ≥ 18 px e/ou bold, mantendo fallback para ink em texto corrido.

### 6.3 Transversal

- Não introduzir cores além das listadas.
- Sem cor âmbar. Sem gradientes. Sem sombras coloridas.

## 7. Acessibilidade (WCAG 2.1 contrast)

Resultados reais calculados com luminância relativa sRGB:

- Texto primário `#E8E8E8` sobre `#08090A` = 16.26 → **AAA**.
- Texto secundário `#8A8D93` sobre `#08090A` = 5.99 → **AA**.
- Ciano `#35D0E0` sobre `#08090A` = 10.68 → **AAA**.
- Ciano `#35D0E0` sobre `#FFFFFF` = 1.87 → **FAIL** (não usar como texto).
- Ciano Hover `#5EDCF0` sobre `#08090A` = 12.31 → **AAA**.
- Ciano Pressed `#25A8B8` sobre `#08090A` = 7.00 → **AA** (limite).
- Ink `#08090A` sobre `#FFFFFF` = 19.93 → **AAA**.

Implicações para o wordmark:
- O ciano existe **apenas** como elemento gráfico grande (último `e` em wordmark). Como a área é grande, não há texto a ser lido dentro do ciano, e o contraste visual permanece claro.
- Não usar o ciano como texto de UI sobre fundos claros. Para texto corrido usar `#E8E8E8` em dark e `#08090A` em light.

## 8. Tipografia

Wordmark: `Sora Bold` (OFL 1.1). Nunca substituir por outra fonte — o wordmark é path, não há reprodução dinâmica.

UI e website:
- Sans-serif: **Inter** (Google Fonts, OFL 1.1). Pesos 400, 500, 600, 700.
- Mono: **JetBrains Mono** (Google Fonts, OFL 1.1). Pesos 400, 500.

Escala UI (pixel): `12 / 14 / 16 / 18 / 24 / 32 / 48`.

## 9. Usos proibidos

1. Adicionar qualquer símbolo, radar, círculo decorativo, scan-line, ícone ou pictograma ao wordmark.
2. Usar `<text>` ou `<image>` dentro dos SVGs finais.
3. Alterar a cor do último `e` para algo diferente de `#35D0E0` (cromáticas) ou `#FFFFFF`/`#08090A` (mono).
4. Usar texto ciano pequeno sobre fundo branco ou cinza claro.
5. Esticar, distorcer, inclinar, outline, stroke, sombra, glow ou rotacionar o wordmark.
6. Recortar parte do wordmark ou dispô-lo em caixas que violem o clearspace.
7. Substituir o Sora por outra fonte nos caminhos.
8. Aplicar gradientes, patterns ou filtros SVG.
9. Renderizar abaixo de 16 px de altura de x-height.
10. Usar `markee` em maiúsculas, all-caps, com espaçamento artificial ou rearranjos.
11. Recolorir todo o wordmark em ciano (apenas o último `e`).
12. Usar as versões `_draft-manual-lettering/` ou `candidates/` em produção.

## 10. Iconografia, fotografia, motion

- Iconografia: stroke-based monocromática, traço 1.5 px a 24 px. Cor de traço `#E8E8E8` sobre dark, `#08090A` sobre light. Acento ciano apenas em estado ativo/hover.
- Fotografia: tons frios e neutros; sem texturas vintage; sem retratos sorridentes. Quando houver produto, enquadrar close.
- Motion: transições 150–200 ms, easing `cubic-bezier(0.2, 0.0, 0.0, 1.0)`. Sem bouncing nem parallax exagerado.

## 11. Grid, spacing, radius, elevation

- Grid base 8 px. Bleeds 24 px / 32 px / 48 px.
- Radius: `6 / 10 / 16 / 24`.
- Elevation (apenas neutras): `--shadow-sm 0 1px 2px rgba(0,0,0,0.3)`, `--shadow-md 0 4px 12px rgba(0,0,0,0.4)`, `--shadow-lg 0 12px 32px rgba(0,0,0,0.5)`. Não existe `shadow-glow` ciano.

## 12. Handoff frontend

- Tokens publicados em `tokens/tokens.json` (DTCG) e `tokens/css-variables.css`.
- Não tocar em `frontend/landing/` ou outros diretórios do frontend — usar os tokens aqui publicados.
- Para sites de terceiros, fornecer sempre `markee-wordmark-dark.svg` em fundo escuro + `markee-wordmark-light.svg` em fundo claro. Versão mono apenas a pedido.

## 13. Versão

- Wordmark: Sora Bold v2.000.
- Manual: v2 (2026-07). Próximas revisões só com aprovação do owner.
