# markee · brand v2

Identidade visual v2 do SaaS jurídico `markee`. Wordmark **apenas tipográfico** (sem símbolo, sem radar, sem pictograma), `markee` em Sora Bold (OFL 1.1) convertido para `<path>` SVG. O último `e` é ciano `#35D0E0` nas variantes cromáticas.

## Inventário

```
assets/brand-v2/
├── README.md                    ← este ficheiro
├── docs/
│   ├── BRAND_MANUAL.md          ← manual completo em PT-PT
│   └── DESIGN.md                ← spec alpha (Google DESIGN.md v1)
├── tokens/
│   ├── tokens.json              ← DTCG, source of truth
│   └── css-variables.css        ← espelho CSS
├── source/
│   └── Sora-Bold.ttf            ← fonte oficial Google Fonts, OFL 1.1
├── scripts/
│   └── generate_wordmark.py     ← geração reproduzível dos SVGs finais
└── logos/
    ├── markee-brand-sheet.svg   ← brand sheet 1600×1100
    ├── markee-wordmark-dark.svg ← para fundos escuros
    ├── markee-wordmark-light.svg← para fundos claros
    ├── markee-wordmark-mono-white.svg
    ├── markee-wordmark-mono-black.svg
    ├── wordmark-meta.json       ← métricas Sora Bold
    ├── _draft-manual-lettering/ ← protótipo v0 (NÃO USAR)
    └── candidates/
        ├── sora/                ← snapshot do candidato Sora corrigido (matches final)
        ├── manrope/             ← runner-up OFL
        └── space-grotesk/       ← runner-up OFL
```

## Artefactos finais vs drafts/candidates

| Estado | Localização | Uso |
|---|---|---|
| **Final** | `logos/markee-*.svg`, `logos/wordmark-meta.json` | Produção |
| Documentação | `docs/BRAND_MANUAL.md`, `docs/DESIGN.md` | Manual oficial |
| Tokens | `tokens/tokens.json`, `tokens/css-variables.css` | Handoff frontend |
| Brand sheet | `logos/markee-brand-sheet.svg` | Apresentação |
| Draft (não usar) | `logos/_draft-manual-lettering/*` | Histórico v0 |
| Candidatos (não usar) | `logos/candidates/{manrope,space-grotesk}/*` | Auditoria comparativa |

## Licença

- Wordmark: Sora Bold v2.000, **OFL 1.1** (SIL Open Font License). `https://scripts.sil.org/OFL`.
- Os paths SVG são entregues para uso livre dentro do projeto markee; podem ser redistribuídos enquanto a fonte permanecer sob OFL.
- UI: Inter (OFL 1.1) e JetBrains Mono (OFL 1.1) — Google Fonts.
- Drafts manuais e candidatos Manrope/Space Grotesk: também OFL 1.1 (não usados em produção).

## Como renderizar

O gerador versionado usa `fontTools`; a validação visual usa `cairosvg` e `Pillow`:

```bash
# Renderizar a PNG para inspeção (transparente)
python3 -c "from cairosvg import svg2png; svg2png(url='logos/markee-wordmark-dark.svg', write_to='out.png', output_width=1482, output_height=240)"

# Renderizar a 24 px de glyph (altura de x-height)
python3 -c "from cairosvg import svg2png; svg2png(url='logos/markee-wordmark-dark.svg', write_to='out24.png', output_width=179, output_height=29)"

# Regenerar a partir da fonte oficial versionada
python3 scripts/generate_wordmark.py
```

## Como validar

Comandos reproduzíveis:

```bash
# 1. JSON válido
python3 -c "import json; json.load(open('tokens/tokens.json'))"

# 2. CSS válido
python3 -c "import tinycss2; tinycss2.parse_stylesheet(open('tokens/css-variables.css').read(), skip_whitespace=True)"

# 3. Testes estruturais, geométricos e de rasterização (na raiz do repositório)
pytest -q tests/frontend/test_brand_v2.py

# 4. Coerência manual ↔ tokens ↔ CSS
diff <(grep -oE '#[0-9A-Fa-f]{6}' docs/BRAND_MANUAL.md | sort -u) \
     <(grep -oE '#[0-9A-Fa-f]{6}' tokens/css-variables.css | sort -u)
```

Saídas esperadas:
- Testes geométricos → seis glifos ordenados, sem overlap, com render a 24/32/132 px.
- WCAG: ciano `#35D0E0` em `#FFFFFF` = 1.87 (FAIL conhecido e documentado).
- `tokens.json` → carrega sem erro.
- `css-variables.css` → parses sem erro.
- `diff` → todas as cores HEX do CSS aparecem no manual (e vice-versa).

## Limites e ressalvas

- **Ciano sobre branco falha AA** (1.87). Por isso o ciano no wordmark é um elemento gráfico grande, não texto. Proibido texto ciano pequeno sobre fundo claro.
- **Drafts preservados** em `_draft-manual-lettering/` e em `candidates/` por instrução do owner. Não promover.
- **Fonte reproduzível** — `source/Sora-Bold.ttf` é o ficheiro oficial Google Fonts usado pelo gerador, com SHA-256 registado em metadata.
- **Versão compacta** (`markee-wordmark-vertical.svg`) só existe no draft manual, não foi promovida — recomendada a não usar; se necessário, gerar nova a partir do wordmark Sora final.
- **Favicon** — o wordmark horizontal não é usado a 16 px; o favicon pré-existente é preservado até aprovação manual de uma solução própria.
