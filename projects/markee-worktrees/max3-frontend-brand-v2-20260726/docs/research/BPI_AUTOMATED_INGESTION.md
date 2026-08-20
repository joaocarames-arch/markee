# BPI automated ingestion — arquitetura operacional para Markee

Data de acesso: 2026-07-24
Autor: Max-2
Âmbito: descoberta, arquivo, extração, normalização, deduplicação e reconciliação dos Boletins da Propriedade Industrial portugueses para dados utilizáveis pelo Markee.

## 1. Conclusão executiva

Confirmado empiricamente: a página oficial do BPI expõe HTML público, sem autenticação, com links diretos `LinkClick.aspx?fileticket=...&portalid=6` para PDFs diários. A listagem tem paginação por URL path com `moduleId/14275/pageNumber/N/beginDate/YYYY-MM-DD/endDate/YYYY-MM-DD/controller/Item/action/Index`. O mecanismo permite backfill por intervalos de datas sem contornar autenticação ou CAPTCHA.

Confirmado empiricamente: os PDFs recentes são PDF 1.7 com texto extraível. Nas 7 amostras descarregadas, PyMuPDF extraiu 122k-303k caracteres nos boletins normais e 211k no boletim de 2026-07-24. Há páginas com pouco texto e imagens, sobretudo páginas de patentes/desenhos/sinais figurativos, mas a camada de marcas nacionais observada é maioritariamente texto/tabela. OCR não deve ser dependência P0; deve existir fallback P1/P2 por página e só quando a secção de marcas relevante tiver texto insuficiente.

Recomendação operacional: implementar pipeline em 5 estágios idempotentes:

1. `discover_bpi_bulletins`: descobrir URLs oficiais e datas.
2. `archive_bpi_pdf`: descarregar PDF, guardar metadados HTTP e SHA-256 de forma imutável.
3. `extract_bpi_text`: extrair texto por página e tabelas onde a secção o justifique.
4. `parse_bpi_mark_events`: parser por secção, nunca regex global.
5. `normalize_reconcile_bpi_events`: normalização, dedupe, confidence, quarantine e matching com EUIPO/TMview/core.

P0 deve cobrir pedidos/publicações, concessões, recusas e caducidades por falta de pagamento, com proveniência completa. P1 cobre renovações, transmissões, renúncias, averbamentos críticos, sentenças e revalidações. P2 fica para retificações/licenças sem fixtures, OCR profundo, marcas internacionais/logótipos e extração figurativa avançada.

## 2. Fontes e amostras oficiais

### 2.1 Página oficial e discovery

Fonte oficial examinada:

- `https://inpi.justica.gov.pt/en-gb/Industrial-Property-Bulletin`

Observações confirmadas por HTTP em 2026-07-24:

- `GET` à página: `200 OK`, `Content-Type: text/html; charset=utf-8`, `Content-Length` observado 66956/66923 bytes, `Cache-Control: no-cache`, cookies DNN/ASP.NET e `__RequestVerificationToken` no HTML público.
- Existe formulário `POST` para a própria página, mas a listagem pública é navegável por links `GET`; não é necessário submeter formulário no pipeline.
- Links PDF observados: `https://inpi.justica.gov.pt/LinkClick.aspx?fileticket=<token>%3d&portalid=6`.
- Texto do link: `Boletim da PI - YYYY-MM-DD`.
- Primeira página inclui um CTA duplicado para o boletim mais recente; dedupe por data+URL/token é obrigatório.
- Paginação observada: `.../moduleId/14275/pageNumber/0/beginDate/2026-01-24/endDate/2026-07-24/controller/Item/action/Index` e páginas `0..11` para 6 meses recentes; outro intervalo `2024-01-01` a `2024-12-31` mostrou pelo menos `0..12`.
- A alteração de `beginDate/endDate` no URL devolve listagens históricas sem autenticação.

Headers PDF confirmados em amostras:

- `Content-Type: application/pdf`
- `Content-Disposition: inline; filename="YYYY-MM-DD.pdf"`
- `Cache-Control: private`
- Sem `ETag`, sem `Last-Modified`, sem `Accept-Ranges` observado.
- Conditional GET com `If-None-Match` bogus e `If-Modified-Since` antigo devolveu `200`, não `304`. Inferência: conditional GET clássico não é útil; usar HEAD/GET leve apenas para metadados e dedupe por SHA-256.

### 2.2 Robots e prudência legal/técnica

`https://inpi.justica.gov.pt/robots.txt` respondeu `200 OK`, `Content-Type: text/plain; charset=utf-8`. O robots observado não continha `Disallow` específico para `LinkClick.aspx` nem para `/en-gb/Industrial-Property-Bulletin`. Continha vários `Disallow` técnicos como `/DesktopModules/` e `/Portals/`.

Decisão prudente:

- Usar só páginas públicas e PDFs oficiais linkados publicamente.
- Não aceder a `/Portals/` diretamente mesmo que os ficheiros físicos possam existir; usar `LinkClick.aspx` público.
- Não contornar CAPTCHA, autenticação, cookies anti-CSRF ou bloqueios.
- User-Agent identificável e rate limit baixo: discovery até 5 req/min, download 1 PDF de cada vez, backoff em 429/5xx.
- Arquivar apenas o necessário para prova e reprocessamento; minimizar dados pessoais em camadas normalizadas.

### 2.3 Amostras reais descarregadas e caracterização

Amostras oficiais por `LinkClick.aspx`:

| BPI | URL/token observado | Tamanho | SHA-256 | Páginas | Caracteres PyMuPDF | Páginas com <100 chars | Imagens | Observação |
|---|---|---:|---|---:|---:|---:|---:|---|
| 2026-07-24 | `slkzvq0qeBE%3d` | 10 330 894 | `4552c731a70e65959a73b12fb94205759bde1898ee6faad0cef01b408bc06844` | 121 | 211 290 | 23 | 97 | Boletim recente; muitas páginas de baixo texto/imagem em zonas não necessariamente P0 de marcas. |
| 2026-06-26 | `iZmwYAaF9PI=` | 1 312 177 | `d030966f37bbe0a2ee4a46c21d3b5c6e227d0a177aed8c232cb3f4ea34a305bd` | 71 | 135 063 | 1 | 44 | Amostra do relatório revisto; marcas nacionais parseáveis. |
| 2026-03-16 | `-iMgjyyClFo=` | 1 501 841 | `513b74cd305609dfb40f2e9b8d3cce4255c89d47c5f29d35403cb332bb1767c2` | 74 | 159 231 | 0 | 62 | Estrutura estável. |
| 2026-02-16 | `XTGR8zYPah4=` | 2 253 905 | `09876f62f615f706e41556b2ffb5ccd1fb6484975f58f635f84bac67e5397a8a` | 108 | 303 176 | 6 | 128 | Texto abundante; inclui averbamentos/penhoras segundo relatório revisto. |
| 2026-01-05 | `snvGugJAcl8=` | 1 029 328 | `3665a0779601fccac1b5d1d855917f3af73fa167f695930df2a685662c9e9394` | 66 | 122 845 | 1 | 23 | Estrutura estável. |
| 2025-05-22 | `kqzQX6KAGgw%3d` | 6 416 706 | `0d5c2b9371f3b8626954b3d8407379c973a00eb624b9c3c017fe7b2a4cf2eb3d` | 115 | 227 820 | 16 | 66 | Amostra histórica com atos raros. |
| 2024-12-31 | `AnBGL-tzZgs%3d` | 859 891 | `5ac5d5adce1b5c7b34704e21eb0008af646a954f45483fe97fa6c6468040d752` | 79 | 178 899 | 0 | 56 | Amostra adicional; confirma backfill por intervalo histórico. |

Ferramentas instaladas no ambiente em 2026-07-24: `fitz`/PyMuPDF, `pdfplumber` e `yaml` disponíveis; `camelot`, `tabula` e `pytesseract` não disponíveis.

## 3. Discovery e backfill

### 3.1 Modelo de descoberta

O discovery deve tratar a página oficial como índice, não como API formal. Contrato observado:

```text
GET /en-gb/Industrial-Property-Bulletin
GET /en-gb/Industrial-Property-Bulletin/moduleId/14275/pageNumber/{n}/beginDate/{YYYY-MM-DD}/endDate/{YYYY-MM-DD}/controller/Item/action/Index
```

Extração:

- Selecionar anchors cujo texto case-insensitive corresponde a `Boletim da PI - \d{4}-\d{2}-\d{2}`.
- Capturar `publication_date` do texto; não inferir a data apenas pelo filename ou token.
- Capturar `source_url` absoluto e token `fileticket` como metadado, sem o tratar como identificador estável único.
- Capturar `discovered_at`, `listing_url`, `page_number`, `begin_date`, `end_date`.
- Remover duplicados por `(publication_date, source_url)` e por `(publication_date, content_disposition_filename)` depois do HEAD/GET.

### 3.2 Calendário e novos boletins

BPI é descrito como diário em dias úteis. Operação recomendada:

- `discover_bpi_today`: dias úteis às 09:15, 10:15, 12:15 e 16:15 Europe/Lisbon. Motivo: publicação pode atrasar; custo baixo.
- `archive_bpi_daily`: dispara quando aparece um `publication_date` ainda não arquivado.
- `discover_bpi_recent_repair`: diário às 22:00, intervalo últimos 14 dias, para apanhar republicações ou falhas temporárias.
- Não assumir publicação em feriados; ausência de boletim num dia útil deve gerar warning só após 16:30 Lisboa e crítica só após 2 dias úteis.

### 3.3 Backfill histórico

Estratégia robusta:

1. Dividir por janelas mensais (`beginDate=YYYY-MM-01`, `endDate=último dia`), porque a paginação anual pode mudar e páginas longas são mais frágeis.
2. Para cada janela, iterar `pageNumber=0..N` enquanto houver novos links ou até duas páginas consecutivas sem links do intervalo.
3. Guardar checkpoint por janela: `year_month`, `page_number`, `links_seen`, `last_success_at`, `status`.
4. Fazer download em fila separada, um PDF de cada vez, com retry/backoff.
5. Final de mês: comparar contagem de dias úteis esperados vs links encontrados, mas não falhar por feriados. Marcar lacunas para revisão.

Checkpoint mínimo:

```json
{
  "source": "inpi_bpi",
  "run_type": "historical_backfill",
  "window_start": "2025-05-01",
  "window_end": "2025-05-31",
  "listing_page": 0,
  "seen_publication_dates": ["2025-05-30", "2025-05-29"],
  "completed": false
}
```

### 3.4 Conditional GET, retries e rate limiting

Confirmado: os PDFs observados não trazem `ETag` nem `Last-Modified`; conditional GET devolveu `200`. Logo:

- Para a página HTML, guardar `Content-Length`, hash do HTML e links extraídos; usar GET normal com rate limit.
- Para PDFs, usar `HEAD` opcional só para validar `Content-Type`/filename/tamanho; depois `GET` e SHA-256.
- Re-download só quando:
  - URL é novo;
  - data existe mas SHA-256 ausente;
  - data existe com URL diferente e o produto decide verificar republicação;
  - auditoria manual pede replay.
- Retry: 5 tentativas em 429/500/502/503/504, backoff exponencial com jitter, base 30s, max 15min. O site mostrou 502 intermitente nesta missão; tratar como esperado.
- Circuit breaker: se 5xx persistir >30min, parar downloads e manter discovery em baixa frequência.

## 4. Raw layer

A raw layer deve ser mais forte do que `raw.api_responses`, porque PDF é binário e deve ser imutável. Sem alterar schema agora, contrato recomendado para futura implementação:

### 4.1 Objeto raw_bpi_bulletin

Campos obrigatórios:

- `id`: UUID interno.
- `source`: `inpi_bpi`.
- `publication_date`: data do link oficial.
- `bulletin_number`: `YYYY/MM/DD`, extraído do cabeçalho do PDF; deve concordar com `publication_date`.
- `source_url`: URL LinkClick usado.
- `listing_url`: página de listagem onde foi descoberto.
- `retrieved_at`: timestamptz.
- `http_status`: inteiro.
- `http_headers`: JSON com `Content-Type`, `Content-Length`, `Content-Disposition`, `Cache-Control`, `Date`, cookies omitidos ou minimizados.
- `content_type`: esperado `application/pdf`.
- `content_disposition_filename`: `YYYY-MM-DD.pdf` observado.
- `file_size_bytes`: tamanho real recebido.
- `sha256`: hash do conteúdo binário.
- `storage_path`: caminho local/S3/object storage, por exemplo `raw/bpi/YYYY/MM/YYYY-MM-DD.<sha256>.pdf`.
- `immutable`: true.
- `archive_version`: inteiro, inicia em 1.
- `supersedes_bulletin_id`: nullable; usar só se a mesma data for republicada com hash diferente.
- `discovery_metadata`: JSON.

Política de imutabilidade:

- Nunca sobrescrever um PDF arquivado.
- Se `publication_date` igual mas SHA diferente: criar nova versão, manter ambas, bloquear alertas automáticos da versão nova até revisão ou comparação de diff de texto.
- Guardar SHA-256 também em cada evento para prova.

### 4.2 Retenção

O ADR 0001 fala em raw API por 90 dias, mas BPI PDF tem valor probatório. Recomendação: PDFs BPI e extrações de texto devem ter retenção indefinida ou, no mínimo, enquanto houver eventos/deadlines ativos derivados. Se custo for problema, comprimir texto e manter PDF original em storage barato.

Estimativa: boletins observados 0,86 MB a 10,3 MB. Assumindo 260 dias úteis/ano e média conservadora 3 MB, custo anual bruto ≈ 780 MB/ano; 10 anos ≈ 8 GB. Isto é baixo para VPS/storage moderno.

## 5. Extraction

### 5.1 Pipeline por página

Para cada PDF:

1. Abrir com PyMuPDF.
2. Validar PDF magic `%PDF` e número de páginas.
3. Para cada página:
   - texto simples: `page.get_text("text")`;
   - blocos com coordenadas: `page.get_text("dict")` ou `blocks`;
   - imagens: contagem e metadados básicos;
   - cabeçalho: regex `BOLETIM DA PROPRIEDADE INDUSTRIAL N.º (\d{4}/\d{2}/\d{2})` e página `N de M`;
   - secções/cabeçalhos candidatos.
4. Guardar `page_text`, `page_blocks`, `page_metrics`.
5. Só chamar pdfplumber/table extractor nas páginas/zonas que contenham cabeçalhos de tabela reconhecidos.

### 5.2 Texto, tabelas e blocos livres

Recomendação mínima fiável:

- PyMuPDF como extractor primário: rápido, já disponível, bom texto por página, bom para cabeçalhos e blocos ST.17.
- pdfplumber como extractor secundário para tabelas de concessões/recusas/caducidades/transmissões. Nas amostras, `extract_tables()` encontrou tabelas reais, mas também muitas de patentes; chamar por secção evita ruído.
- Não usar Camelot/Tabula P0: dependências externas mais pesadas, Java/Ghostscript, não instaladas, maior custo operacional. Só reavaliar se pdfplumber falhar em fixtures P1.
- OCR fora do P0. Adicionar fallback por página com `ocr_required=true` quando `text_chars < 100`, `image_count > 0` e a página está dentro de secção de marcas relevante. OCR deve ser assíncrono e quarantine-first.

### 5.3 ST.17 e segmentação de secções

Os BPIs começam com sumário, aviso, códigos ST.17 e secções por modalidade. Para marcas nacionais, o parser deve procurar primeiro `REGISTO NACIONAL DE MARCAS`, depois subtítulos:

- `Pedidos`
- `Concessões`
- `Recusas`
- `Renovações`
- `Caducidades`
- `Transmissões`
- `Outros Averbamentos`
- `Renúncias`
- `Vigências por sentença`
- `Pedidos de revalidação` / `Avisos de deferimento de revalidação`

Regra crítica: termos como “licenças”, “transmissão” ou “reclamações” dentro de listas de produtos/serviços não são atos. Só cabeçalhos e zonas de secção podem criar eventos.

### 5.4 OCR fallback

OCR trigger conservador:

```text
ocr_required = page_text_chars < 100
               AND page_image_count > 0
               AND page_section_path startswith "REGISTO NACIONAL DE MARCAS"
               AND page_contains_expected_event_boundary is unknown
```

P0 não deve bloquear se OCR não existir. Resultado de OCR deve ter `extraction_method=ocr`, `confidence` inicial mais baixa e não deve disparar alertas críticos sem revisão humana.

## 6. Parsing por secção

A taxonomia machine-readable está em `config/bpi_event_taxonomy.yaml`. Resumo operacional:

| Event type | Prioridade | Estratégia | Estado |
|---|---|---|---|
| `application_published` | P0 | campos ST.17 `(210)`, `(220)`, `(730)`, `(511)`, `(540)` | confirmado |
| `grant_published` | P0 | tabela por cabeçalho | confirmado |
| `refusal_published` | P0 | tabela + fundamento CPI | confirmado |
| `lapse_fee_nonpayment` | P0 | tabela por cabeçalho | confirmado |
| `renewal_published` | P1 | lista compacta de números | confirmado |
| `assignment_recorded` | P1 | tabela antigo/atual titular | confirmado |
| `recordal_other` | P1/P2 | tabela + classificador subtipo | confirmado, heterogéneo |
| `encumbrance_recorded` / `encumbrance_lifted` | P1 | subtipo de averbamento por regex | confirmado |
| `surrender_total` / `surrender_partial` | P1 | tabela + classificador de âmbito | confirmado |
| `lapse_by_judgment`, `validity_by_judgment` | P1 | tabela/texto livre | confirmado parcial |
| `revalidation_requested`, `revalidation_deferred` | P1 | tabela/texto | confirmado parcial |
| `correction_published`, `license_recorded`, `opposition_filed` | P2/P1 | collect/quarantine até fixtures | incerto ou sem amostras suficientes |
| `unknown_bpi_mark_event` | P2 | quarantine | extensibilidade |

## 7. Cleaning e normalização

Regras mínimas:

- Datas: converter `YYYY.MM.DD` para ISO `YYYY-MM-DD`; validar intervalo razoável (`1900-01-01` a `publication_date+1y`, salvo exceção em quarantine).
- Números de processo/registo: guardar `*_raw`; canónico remove espaços, pontos de milhar e prefixos `N.º`, `N.os`, mantendo só dígitos quando aplicável.
- Classes Nice: extrair inteiros 1..45; remover zeros à esquerda; se aparecer classe fora do intervalo, field confidence baixa/quarantine.
- Países: normalizar para ISO alpha-2 maiúsculo; aceitar códigos observados no BPI (`PT`, `US`, `DE`, etc.); país desconhecido fica null, não inventar.
- Titulares/representantes: normalizar whitespace, Unicode NFC, remover quebras de linha artificiais. Não tentar enriquecer moradas/contactos no P0.
- Fundamentos CPI: extrair `article`, `number`, `paragraph`, `subparagraph`, `law_version` por regex conservador; manter sempre `legal_basis_text` original.
- Texto: normalizar encoding, hífens de quebra de linha, espaços múltiplos; preservar `raw_text_excerpt` curto e `raw_text_hash`.
- Aliases: mapear cabeçalhos observados via YAML, com matching case-insensitive e acentos normalizados.
- Before/after: só preencher quando o texto contiver marcadores explícitos como “alterado ... para”; caso contrário manter em `observations`.

## 8. Identidade, dedupe e reprocessamento idempotente

Dedupe lógico por evento:

```text
dedupe_key = sha256(
  "BPI" |
  bulletin_number |
  publication_date |
  section_path |
  event_type |
  process_or_registration_number |
  act_date_or_empty |
  normalized_legal_basis_or_empty |
  normalized_observation_hash_16 |
  parser_family_key
)
```

Campos de identidade obrigatórios:

- `bulletin_sha256`
- `bulletin_number`
- `publication_date`
- `page_number`
- `section_path`
- `event_type`
- `process_number` ou `registration_number` quando aplicável
- `raw_text_hash`
- `parser_version`

Idempotência:

- Reprocessar o mesmo PDF com a mesma `parser_version` deve produzir as mesmas `dedupe_key`.
- Nova `parser_version` pode produzir eventos melhores, mas deve ligar a `supersedes_event_id`/`previous_parse_event_id` quando a chave semântica forte coincidir.
- Eventos automáticos existentes não devem ser apagados; marcar `is_current_parse=false` se substituídos.
- Se `dedupe_key` igual e payload normalizado igual: no-op.
- Se `dedupe_key` igual mas payload mudou: criar `parser_conflict` para revisão; não sobrescrever silenciosamente.

## 9. Reconciliação BPI ↔ EUIPO/TMview

Princípio: BPI não substitui EUIPO/TMview; complementa com publicação oficial, página e texto.

Matching forte:

1. `application_number`/`process_number` exato contra `core.trademarks.application_number`.
2. `registration_number` exato contra `core.trademarks.registration_number`.
3. Para renovações em lista: registo exato + jurisdição PT.
4. Para transmissão/renúncia/caducidade: número forte + data do ato/publicação.

Matching fraco permitido apenas para sugerir revisão, nunca fundir automaticamente:

- número + classes + país;
- sinal nominativo + data de pedido;
- titular normalizado + classes.

Source priority:

- BPI tem prioridade para `publication_date` oficial PT, `bulletin_number`, `page_number`, `legal_notice`, `legal_basis_text`, cadeia textual de averbamentos, prazos nacionais baseados em publicação.
- EUIPO/TMview tem prioridade para snapshot bibliográfico atual, media, status normalizado, dados harmonizados multijurisdição e similarity search.
- Em conflito, preservar ambos e criar `source_conflict` com `conflict_type`, `field`, `bpi_value`, `euipo_value`, `resolution_status`.

Event links:

```json
{
  "bpi_event_id": "uuid",
  "trademark_id": "uuid|null",
  "euipo_publication_ref": "optional",
  "match_strength": "strong_application_number",
  "reconciliation_status": "matched|unmatched|conflict|review_required",
  "source_priority_applied": ["bpi_publication_provenance", "euipo_current_snapshot"]
}
```

## 10. Qualidade, quarantine e drift

### 10.1 Confidence

Score global sugerido:

- +0.20 secção reconhecida
- +0.20 número processo/registo válido
- +0.15 data de ato válida
- +0.15 página/boletim extraídos e consistentes
- +0.10 classes Nice válidas quando esperadas
- +0.10 cabeçalhos de tabela alinhados
- +0.10 campo crítico extraído, por exemplo fundamento legal para recusa

Thresholds:

- `>=0.85`: automático.
- `0.65..0.84`: inserir, mas marcar review se gerar alerta crítico.
- `<0.65`: quarantine; não alertar.

### 10.2 Validações

- `publication_date` deve bater certo com `bulletin_number` e filename, se todos existirem.
- `page_number <= page_count`.
- `event_type` deve existir na taxonomia YAML.
- `nice_classes` só 1..45.
- Recusa P0 deve ter `refusal_date` ou `legal_basis_text`; se ambos ausentes, review.
- Pedido P0 deve ter `application_number` e `application_date`; sem `(540)` pode ser figurativo, não falhar automaticamente.
- Não criar `opposition_deadline_pt` sem `publication_date` válida.

### 10.3 Drift de layout

Métricas por boletim:

- número de páginas;
- caracteres por página;
- percentagem de páginas com texto baixo;
- secções reconhecidas vs esperadas;
- eventos por tipo;
- taxa de quarantine;
- alterações de cabeçalhos de tabela;
- divergência entre data do link e cabeçalho PDF.

Alertas internos:

- zero pedidos em dia útil com BPI publicado;
- queda >50% de eventos P0 face à média móvel 20 boletins;
- >20% páginas OCR-required dentro de marcas nacionais;
- nova secção desconhecida com >5 processos;
- PDF com SHA diferente para data já arquivada.

### 10.4 Golden fixtures

Criar fixtures de teste com PDFs oficiais pequenos/representativos:

- 2026-06-26: pedidos, concessões, recusas, caducidades, transmissões, penhoras/levantamentos, renúncias, revalidação.
- 2025-05-22: alteração de elementos não essenciais, caducidade por sentença, nulidade.
- 2026-01-05: estrutura estável e procuradores autorizados para garantir exclusão no MVP.
- 2024-12-31: amostra histórica adicional.
- 2026-07-24: boletim grande para performance e drift.

Fixtures devem guardar SHA-256, páginas-alvo e eventos esperados minimizados, sem expor contactos pessoais desnecessários.

## 11. RGPD e minimização

Base: dados de marcas e atos publicados são públicos por natureza registral, mas isso não elimina obrigações de minimização, finalidade e retenção.

Políticas recomendadas:

- Guardar PDF original para prova; em payload normalizado guardar só campos necessários ao evento.
- Pessoas singulares: classificar `holder_type=natural|legal|unknown` por heurística conservadora; se unknown, tratar como natural para prospeção.
- Não extrair listas finais de procuradores autorizados no MVP: incluem telefone/email/web e não são eventos de marca.
- Contactos, moradas completas, tribunais e números de processo judicial: só guardar quando necessário para evento jurídico; para UI pública/utilizador comum, mascarar por defeito.
- `court_case_number_hash`: preferir hash com salt aplicacional para dedupe; guardar número claro só se houver base legal documentada e controlo de acesso.
- Prospeção: usar apenas pessoas coletivas ou pessoas singulares com base de interesse legítimo documentada; retenção curta para leads não convertidos; opt-out/supressão.
- Alertas: não incluir moradas/contactos pessoais; incluir link/proveniência BPI, número de processo e excerto curto.

## 12. Operação

### 12.1 Celery schedules

Proposta:

| Task | Schedule Lisbon | Função |
|---|---|---|
| `discover_bpi_today` | `15 9,10,12,16 * * 1-5` | Verificar publicação do dia. |
| `discover_bpi_recent_repair` | `0 22 * * 1-5` | Reconciliar últimos 14 dias. |
| `archive_bpi_pdf` | on-demand/fila | Download e raw archive. |
| `extract_bpi_pdf` | após arquivo | Texto, páginas, tabelas, métricas. |
| `parse_bpi_events` | após extração | Eventos normalizados por secção. |
| `reconcile_bpi_events` | após parsing e diário 23:00 | Matching com core/EUIPO. |
| `calculate_deadlines` | hourly | Gerar prazos derivados. |
| `bpi_backfill_month` | manual/background | Backfill histórico por mês. |

### 12.2 Locking

- Lock por `publication_date` para download/arquivo.
- Lock por `bulletin_sha256 + parser_version` para extração/parsing.
- Lock por `event_dedupe_key` para upsert idempotente.
- Usar timeout e heartbeat; se worker morrer, desbloquear após TTL.

### 12.3 Observabilidade

Logs estruturados:

- `source_run_id`, `publication_date`, `listing_url`, `pdf_url`, `sha256`, `parser_version`, `event_type`, `confidence`, `quarantine_reason`.

Métricas:

- `bpi_discovery_links_total`
- `bpi_download_bytes_total`
- `bpi_download_failures_total`
- `bpi_parse_events_total{event_type}`
- `bpi_quarantine_total{reason}`
- `bpi_reconciliation_total{status}`
- `bpi_ocr_required_pages_total`
- `bpi_layout_drift_score`

Alertas operacionais:

- site 5xx prolongado;
- BPI ausente em dia útil;
- hash diferente para data existente;
- parser P0 com taxa de confiança <85% por dois boletins;
- fila Celery atrasada >2h.

### 12.4 Replay e disaster recovery

- Raw PDF + page extraction + parser version permitem replay determinístico.
- Backups: raw PDFs em storage incremental; DB core/events/app em backup diário; raw extraction pode ser regenerável se PDF existir.
- Em desastre, restaurar PDFs, correr `extract_bpi_pdf` e `parse_bpi_events` por `parser_version` atual, depois reconciliar.
- Nunca depender da estabilidade eterna dos tokens `fileticket`; guardar PDF e URL descoberto.

### 12.5 Custo

Custo direto estimado: praticamente zero em dados; armazenamento <1 GB/ano em média provável, talvez 1-3 GB/ano se boletins grandes forem frequentes. CPU: PyMuPDF/pdfplumber em boletins de 100 páginas é aceitável num VPS pequeno. OCR é o único custo potencial; por isso fica fora do P0 e só por página.

## 13. Interfaces para Markee

### 13.1 Tabelas/schemas recomendados

Sem alterar DB nesta missão, a futura implementação deve mapear para:

- `core.documents`: PDF BPI completo (`document_type=bpi_bulletin`) e eventualmente documento por evento se necessário.
- `events.lifecycle_events`: evento normalizado consumido pela app.
- `raw.bpi_bulletins` e `raw.bpi_page_extractions`: recomendadas como extensão futura, porque `raw.api_responses` não é ideal para binário.
- `events.bpi_event_links` ou JSON em `raw_data`: reconciliação com EUIPO/TMview.

### 13.2 Eventos e deadlines

P0 produz:

- `application_published` → cria `deadline_type=opposition_pt`, `deadline_date=publication_date + 2 meses`.
- `refusal_published` → alerta `refusal_watch`, sem prazo final automático até validação jurídica.
- `grant_published` → atualiza lifecycle e fecha watch de oposição quando aplicável.
- `lapse_fee_nonpayment` → alerta expiração/caducidade e prospeção prudente.

### 13.3 API/UI

API interna sugerida:

- `GET /api/v1/bpi/bulletins?from=&to=`: lista boletins arquivados.
- `GET /api/v1/bpi/bulletins/{id}`: metadados, SHA, páginas, eventos.
- `GET /api/v1/trademarks/{id}/events`: inclui eventos BPI com provenance.
- `GET /api/v1/deadlines`: mostra prazos PT derivados do BPI.
- `GET /api/v1/review/bpi-events`: fila de quarantine/review para admins/profissionais autorizados.

UI:

- Em alertas, mostrar “Fonte: BPI n.º YYYY/MM/DD, página N, SHA …, excerto”.
- Botão “abrir PDF oficial” aponta para `source_url`; se link oficial falhar, usar cópia arquivada interna apenas para utilizadores autorizados.
- Mostrar confidence e estado de reconciliação quando houver conflito.

## 14. Exemplo de payload normalizado

```json
{
  "event_type": "application_published",
  "source": "bpi_pdf",
  "jurisdiction": "PT",
  "publication_date": "2026-06-26",
  "bulletin_number": "2026/06/26",
  "bulletin_url": "https://inpi.justica.gov.pt/LinkClick.aspx?fileticket=iZmwYAaF9PI=&portalid=6",
  "bulletin_sha256": "d030966f37bbe0a2ee4a46c21d3b5c6e227d0a177aed8c232cb3f4ea34a305bd",
  "page_number": 14,
  "section_path": "REGISTO NACIONAL DE MARCAS > Pedidos",
  "application_number": "770255",
  "application_date": "2026-06-02",
  "word_mark": null,
  "nice_classes": [42],
  "goods_services_excerpt": "...",
  "applicant_country": "PT",
  "opposition_deadline": "2026-08-26",
  "raw_text_excerpt": "(210) 770255 ...",
  "dedupe_key": "sha256:...",
  "parser_version": "bpi_parser_v1",
  "parse_confidence": 0.91,
  "field_confidence": {
    "application_number": 0.99,
    "application_date": 0.99,
    "nice_classes": 0.90,
    "word_mark": 0.40
  },
  "reconciliation": {
    "status": "unmatched",
    "match_strength": null,
    "trademark_id": null
  }
}
```

## 15. MVP e implementação TDD para a Forja

### P0 — 2 a 3 semanas

1. Fixtures oficiais: guardar PDFs ou páginas extraídas minimizadas com SHA conhecido.
2. Discovery parser de HTML:
   - teste duplica CTA removido;
   - teste paginação mensal;
   - teste extração de data e URL.
3. Archive service:
   - teste SHA-256 e metadados HTTP;
   - teste mesma data/mesmo hash idempotente;
   - teste mesma data/hash diferente cria versão/review.
4. Extraction service:
   - teste page_count, headers, page_text e metrics nas fixtures.
5. Section segmenter:
   - teste delimita `REGISTO NACIONAL DE MARCAS` e subtítulos.
6. Parsers P0:
   - pedidos: processo, data, classes, deadline +2 meses;
   - recusas: data, processo, fundamentos CPI;
   - concessões: registo/despacho;
   - caducidades por taxa.
7. Dedupe/reconciliation básico por número forte.
8. Confidence/quarantine.

Definition of Done P0:

- Suite unitária + integração verde.
- Reprocessar fixture duas vezes não duplica eventos.
- Pelo menos 95% dos eventos P0 esperados nas golden fixtures são extraídos ou explicitamente quarantined com motivo.
- Nenhum alerta crítico nasce de evento confidence <0.65.

### P1 — 3 a 5 semanas

- Renovações por lista.
- Transmissões antigo/novo titular.
- Renúncias total/parcial.
- Averbamentos: nulidade, penhora, levantamento.
- Sentenças e revalidações.
- UI/API de provenance e review queue.
- Métricas de drift.

### P2 — depois de dados estáveis

- OCR por página.
- Retificações/licenças/oposições quando houver amostras reais suficientes.
- Parsing profundo de tribunal/partes com política RGPD reforçada.
- Marcas internacionais/logótipos se o plano comercial exigir.

## 16. Riscos e bloqueios

- Instabilidade INPI: 502 observado nesta sessão. Mitigação: retry/backoff, recent repair e backfill.
- Ausência de ETag/Last-Modified: não há conditional GET real. Mitigação: dedupe por SHA e HEAD opcional.
- Layout drift: mitigação com fixtures, métricas e quarantine.
- Eventos raros sem amostras: não implementar parser “criativo”; YAML já reserva tipos, mas P2/quarantine.
- RGPD/prospeção: risco reputacional se forem usados contactos ou pessoas singulares sem base. Mitigação: minimização e filtros desde P0.
- EUIPO/TMview PT via API não validado autenticadamente nesta missão: reconciliação deve aceitar `unmatched` e não depender de paridade total.

## 17. Fontes consultadas

- INPI — Industrial Property Bulletin: `https://inpi.justica.gov.pt/en-gb/Industrial-Property-Bulletin`
- INPI robots.txt: `https://inpi.justica.gov.pt/robots.txt`
- PDFs oficiais BPI via `LinkClick.aspx` listados na secção 2.3.
- Relatório interno revisto: `docs/research/BPI_VS_EUIPO_GAPS.md`.
- Documentação interna: `docs/SOURCES_INVENTORY.md`, `docs/DATA_DICTIONARY.md`, `docs/SCHEMA_DESIGN.md`, ADR 0001-0003, `config/sources.yaml`.
