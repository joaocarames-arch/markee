---
version: alpha
name: markee
description: Marc dark premium · wordmark `markee` apenas tipográfico · ciano #35D0E0 apenas no último `e` · Sora Bold (OFL 1.1) em paths.
colors:
  primary: "#08090A"
  secondary: "#1A1C1F"
  tertiary: "#35D0E0"
  neutral: "#E8E8E8"
typography:
  wordmark:
    fontFamily: Sora Bold
    fontWeight: 700
    fontSource: Google Fonts
    fontLicense: OFL-1.1
    pathOnly: true
    advanceUnits: font
  ui-heading:
    fontFamily: Inter
    fontWeight: 600
    fontSize: 32px
  ui-body:
    fontFamily: Inter
    fontWeight: 400
    fontSize: 16px
  ui-mono:
    fontFamily: JetBrains Mono
    fontWeight: 400
    fontSize: 14px
rounded:
  sm: 6px
  md: 10px
  lg: 16px
  xl: 24px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  2xl: 48px
logo:
  clearspace: 1x x-height
  minHeightPx: 24
  minHeightLowerLimitPx: 20
  accentOnLastGlyph: true
  accentColor: "#35D0E0"
  accentGlyph: "e"
  noSymbol: true
  noRadar: true
  noPictogram: true
  pathsOnly: true
components:
  wordmark-dark:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.tertiary}"
    typography: "{typography.wordmark}"
  wordmark-light:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.primary}"
    typography: "{typography.wordmark}"
  wordmark-mono-white:
    backgroundColor: "{colors.primary}"
    textColor: "#FFFFFF"
    typography: "{typography.wordmark}"
  wordmark-mono-black:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.primary}"
    typography: "{typography.wordmark}"
  button-primary:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
    padding: 12px
  button-primary-hover:
    backgroundColor: "#5EDCF0"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
    padding: 12px
  button-primary-pressed:
    backgroundColor: "#25A8B8"
    textColor: "#FFFFFF"
    rounded: "{rounded.md}"
    padding: 12px
---

## Overview

Wordmark `markee` apenas tipográfico. Sem símbolo, sem radar, sem pictograma. A cor ciano é o único acento e está limitada ao último `e` nas versões cromáticas. UI usa Inter + JetBrains Mono. Diretriz é dark premium, ciano como único acento, geometria grotesca vertical.

## Colors

- **Primary (`#08090A`)** — Ink. Background padrão e texto sobre claro.
- **Secondary (`#1A1C1F`)** — Surface. Cards, painéis.
- **Tertiary (`#35D0E0`)** — Acento. Apenas como elemento gráfico grande (último `e` no wordmark, ícones). Nunca como texto pequeno sobre branco (contraste 1.87).
- **Neutral (`#E8E8E8`)** — Texto primário sobre dark.

## Typography

- **Wordmark**: Sora Bold (OFL 1.1). Apenas glyphs em paths. Não substituir.
- **UI heading**: Inter 600 / 32 px.
- **UI body**: Inter 400 / 16 px.
- **UI mono**: JetBrains Mono 400 / 14 px.

## Logo

- Clearspace: 1× x-height em todas as direções.
- Mínimo recomendado: 24 px. Limite inferior absoluto: 20 px. O wordmark horizontal não deve ser imposto como favicon de 16 px.
- Acento (`#35D0E0`) no último `e` apenas nas variantes cromáticas (`dark`, `light`).
- Paths apenas (`<path>`). Sem `<text>` / `<image>` / `<use>` / `href` externo.

## Components

- `wordmark-dark`: aplicação padrão em superfícies escuras.
- `wordmark-light`: aplicação padrão em superfícies claras.
- `wordmark-mono-white` / `wordmark-mono-black`: impressão 1-tinta ou quando há restrição cromática.
- `button-primary` e estados: usam ciano como background, ink como texto. States `hover`/`pressed` documentados.

## Do's and Don'ts

Do:
- Manter clearspace 1× x-height.
- Renderizar ≥ 24 px no digital.
- Usar o ciano apenas no último `e` (cromáticas) e em elementos gráficos grandes.

Don't:
- Acrescentar símbolo, radar, pictograma, scan-line, ícone, círculo decorativo.
- Usar `#35D0E0` como texto pequeno sobre fundo branco ou cinza claro.
- Substituir Sora Bold por outra fonte.
- Aplicar gradientes, filtros, glow, sombras coloridas, distorções.
