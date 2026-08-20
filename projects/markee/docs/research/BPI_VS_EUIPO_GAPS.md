# BPI vs EUIPO/TMview — lacunas úteis para Markee

Data de acesso: 2026-07-24
Autor: Max-2, investigação crítica para a equipa Spud
Âmbito: marcas nacionais portuguesas publicadas no Boletim da Propriedade Industrial (BPI) vs informação exposta pela stack EUIPO/TMview/Trademark Search API.

---

## 1. Resumo executivo

Conclusão principal: o BPI não deve ser tratado como fonte primária de pesquisa/similaridade, mas é uma fonte juridicamente valiosa para eventos publicados, prazos e prova de publicação. A especificação pública EUIPO Trademark Search API 1.1.0 consultada dá campos bibliográficos, estado atual, publicações normalizadas, oposições/cancelamentos/recursos com identificadores e estados, records e decisions; porém não demonstra, nesta sessão, equivalência integral para marcas nacionais portuguesas nem substitui a granularidade textual do BPI para atos como recusas com fundamentos legais, caducidades por causa específica, averbamentos com texto livre, penhoras/levantamentos, renúncias, alterações não essenciais, sentenças e revalidações.

Classificação agregada da matriz abaixo:

- A — ausente como campo equivalente na especificação pública EUIPO Trademark Search API 1.1.0 consultada; não prova ausência no ecossistema EUIPO/TMview: 3 itens.
- B — existe/modelado na especificação pública ou provavelmente refletido por estado/record, mas o BPI tem maior granularidade, texto livre ou proveniência oficial: 12 itens.
- C — equivalente ao nível de campo na especificação pública consultada, sem prova autenticada específica para PT: 3 itens.
- D — incerto/não comprovado nesta sessão: 3 itens.

Valor comprovado para Markee:

1. Prazos acionáveis: a publicação BPI de pedidos de marcas nacionais inicia explicitamente o prazo de 2 meses para reclamação/oposição, com base no aviso publicado e no CPI.
2. Alertas de recusa: o BPI inclui recusas com data da recusa e fundamentos legais por artigo/alínea do CPI; isto permite alertas mais úteis do que “status=REFUSED”.
3. Auditoria/proveniência: número/data do boletim, página e excerto do ato são evidência reprodutível.
4. Cadeia histórica: o BPI publica eventos que podem alterar a vida jurídica sem se reduzirem bem a um estado único: transmissão, renúncia parcial, caducidade por sentença, penhora, levantamento de penhora, pedido de nulidade.
5. Prospeção: eventos como recusas, pedidos sem mandatário visível, caducidades recentes e revalidações geram oportunidades comerciais legítimas para profissionais de PI, com cautela RGPD.

Conclusão explícita: estritamente exclusivo/provado nesta investigação é o que foi observado diretamente nos PDFs oficiais do BPI — texto do aviso legal PT, página, excerto, número/data do boletim e detalhe textual publicado. O restante deve ser descrito como “mais granular no BPI face à especificação pública EUIPO Trademark Search API 1.1.0 consultada”, não como ausente de todo o ecossistema EUIPO/TMview. Permanece incerta a cobertura programática real de marcas nacionais PT via API/TMview sem consulta autenticada ou documentação REST pública validada.

Recomendação curta: implementar parser BPI P0 para pedidos/publicações, recusas, concessões, caducidades, renovações simples, averbamentos críticos e proveniência. Não tentar extrair tudo no MVP: listas de procuradores autorizados, contactos pessoais, secções não-marca e detalhes figurativos complexos devem ficar fora ou em P2.

---

## 2. Metodologia e limitações

### 2.1 Amostras BPI examinadas

Foram descarregados e extraídos localmente 5 PDFs oficiais do INPI, todos via `https://inpi.justica.gov.pt/LinkClick.aspx?...&portalid=6`:

| Data do BPI | URL oficial | Páginas | Caracteres extraídos | Observação |
|---|---:|---:|---:|---|
| 2026-06-26 | https://inpi.justica.gov.pt/LinkClick.aspx?fileticket=iZmwYAaF9PI=&portalid=6 | 71 | 136 522 | Amostra recente; inclui pedidos, concessões, recusas, renovações, caducidades, transmissões, penhora/levantamento, renúncias e revalidação. |
| 2026-03-16 | https://inpi.justica.gov.pt/LinkClick.aspx?fileticket=-iMgjyyClFo=&portalid=6 | 74 | 160 693 | Amostra recente; inclui renúncias parciais, averbamentos, revalidação. |
| 2026-02-16 | https://inpi.justica.gov.pt/LinkClick.aspx?fileticket=XTGR8zYPah4=&portalid=6 | 108 | 305 525 | Amostra recente; inclui penhora e outros averbamentos. |
| 2026-01-05 | https://inpi.justica.gov.pt/LinkClick.aspx?fileticket=snvGugJAcl8=&portalid=6 | 66 | 124 165 | Amostra recente; inclui estrutura estável e lista de procuradores autorizados. |
| 2025-05-22 | https://inpi.justica.gov.pt/LinkClick.aspx?fileticket=kqzQX6KAGgw=&portalid=6 | 115 | 230 045 | Amostra mais antiga; confirmou estabilidade estrutural e atos menos frequentes: alteração de elementos não essenciais, caducidade por sentença, renúncias, nulidade. |

Extração: download HTTP direto dos PDFs oficiais; texto extraído com PyMuPDF (`fitz`). Não foram feitas chamadas autenticadas a EUIPO, TMview, Stripe, email, Telegram ou qualquer serviço pago.

### 2.2 Fontes EUIPO/TMview examinadas

1. EUIPO Developer Portal — Trademark search API 1.1.0: https://dev.euipo.europa.eu/product/trademark-search_110/api/trademark-search
   - A página pública expõe OpenAPI 3.0 embutido.
   - Campos relevantes encontrados: `applicationNumber`, `applicationDate`, `applicants`, `representatives`, `registrationDate`, `publicationDate`, `expiryDate`, `status`, `statusDate`, `goodsAndServices`, `niceClasses` em resultados de pesquisa, `oppositionPeriodStartDate`, `oppositionPeriodEndDate`, `renewalStatus`, `oppositions`, `cancellations`, `records`, `appeals`, `publications`, `decisions`, `updateDate` em query.
   - A descrição oficial diz “Perform searches within EUIPO's database and retrieve all available information on a given trade mark”. A especificação observada modela pessoas com `office` enum `EM` e `WO`, o que não prova, por si só, cobertura programática completa de marcas nacionais PT nesta API.
2. TMview/EUIPN: https://www.euipn.org/en/tools/TMview e https://www.tmdn.org/tmview/
   - Ferramenta oficial de consulta agregada de marcas de institutos participantes.
   - Não foi encontrada documentação oficial pública de REST API TMview para consumo direto.
3. Documentação/projeto Markee já existente:
   - `/home/batata/projects/markee/docs/SOURCES_INVENTORY.md`
   - `/home/batata/projects/markee/docs/DATA_DICTIONARY.md`
   - `/home/batata/projects/markee/docs/SCHEMA_DESIGN.md`

### 2.3 Fontes legais/oficiais

- INPI — página oficial do BPI: https://inpi.justica.gov.pt/en-gb/Industrial-Property-Bulletin
- Diário da República — Decreto-Lei n.º 110/2018, Código da Propriedade Industrial: https://diariodarepublica.pt/dr/detalhe/decreto-lei/110-2018-117279933
- Diário da República — legislação consolidada CPI: https://diariodarepublica.pt/dr/legislacao-consolidada/decreto-lei/2018-117279941-117317999
- Aviso repetido nos BPIs consultados: “De acordo com o artigo 226.º do Código da Propriedade Industrial... da data de publicação do presente aviso começa a contar-se o prazo de dois meses para a apresentação de reclamações... em conformidade com o artigo 17.º”.

### 2.4 Limitações

- Não houve autenticação na EUIPO Trademark Search API; a comparação API assenta na especificação OpenAPI pública e não em respostas reais para marcas PT.
- Não foi possível provar empiricamente, nesta sessão, que a Trademark Search API pública cobre marcas nacionais portuguesas com os mesmos campos que EUTM/IR. A cobertura TMview de Portugal é tratada como confirmada apenas ao nível de ferramenta de consulta agregada, não como API REST documentada.
- “Não observado nas 5 amostras” não foi convertido em “não existe”. Atos não encontrados nas amostras reais são classificados como D quando a ausência não é comprovável.
- Foram evitadas transcrições extensas de nomes, moradas, emails e telefones. Exemplos abaixo usam números/processos, campos e excertos curtos; quando o ato contém dados sensíveis, o texto é resumido ou mascarado.

---

## 3. Matriz BPI vs EUIPO/TMview/API

Legenda conservadora:

- A: ausente como campo equivalente na especificação pública EUIPO Trademark Search API 1.1.0 consultada; isto não prova ausência em todo o ecossistema EUIPO/TMview.
- B: existe/modelado na especificação pública, ou pode ser refletido por estado/record/decision, mas o BPI preserva maior granularidade, texto livre, causa jurídica ou proveniência oficial.
- C: equivalente ao nível de campo na especificação pública consultada; sem prova autenticada específica para marcas PT.
- D: incerto/não comprovado nesta sessão, por falta de amostra BPI, consulta autenticada ou documentação REST pública TMview validada.

Nota: a coluna EUIPO/TMview/API descreve apenas o que foi observado na especificação pública EUIPO Trademark Search API 1.1.0 e na documentação pública TMview/EUIPN consultada. Não é uma prova negativa sobre bases internas, UI TMview completa, Open Data, bulk data ou APIs autenticadas.

| # | Informação / evento | BPI observado | EUIPO/TMview/API observado na especificação pública consultada | Classe | Impacto Markee |
|---:|---|---|---|---|---|
| 1 | Publicação de pedido nacional PT | Secção “Pedidos”; inclui aviso legal, processo, data pedido, titular, país, classes, termos, cores, sinal, Vienna. | API tem `publicationDate`, `publications`, `publicationSection`, `applicationDate`, `wordMarkSpecification`, `goodsAndServices`; TMview é ferramenta agregada de consulta, mas sem REST pública validada nesta sessão. | B | BPI é prova oficial PT e contém aviso legal textual que dispara prazo nacional. |
| 2 | Prazo de 2 meses para reclamação/oposição PT | Texto expresso em todos os BPIs recentes: prazo de dois meses desde a publicação, art. 17.º e 226.º CPI. | API tem `oppositionPeriodEndDate`, mas a especificação é genérica/EUIPO; não contém o aviso legal português nem página BPI. | B | P0 para deadline engine; usar BPI como fonte documental do prazo PT. |
| 3 | Número/data/página do boletim | Cabeçalho por página: “BPI n.º YYYY/MM/DD”, página N de M; secção e excerto. | API tem `bulletinNumber`, `publicationSection`, `publicationDate` em `Publication`; a especificação pública não expõe página PDF nem excerto. | A | Auditoria e prova de publicação. |
| 4 | Pedido — número e data | Campos `(210)` e `(220)`. | API tem `applicationNumber`, `applicationDate`. | C | Equivalente ao nível de campo; cobertura PT via API não foi validada por consulta autenticada. |
| 5 | Pedido — sinal nominativo | Campo `(540)` quando nominativo; em figurativas pode estar vazio/depender de imagem. | API tem `wordMarkSpecification.verbalElement` e media endpoints para imagem/som/vídeo/modelo. | C | Similaridade deve continuar por fonte bibliográfica/API quando validada; BPI é fallback/proveniência. |
| 6 | Pedido — classes e termos Nice | Campo `(511)` com classes e lista de produtos/serviços em PT. | API tem `goodsAndServices` multilingue e `niceClasses` em pesquisa. | C | Equivalente ao nível de campo; BPI confirma texto PT publicado. |
| 7 | Pedido — cores | Campo `(591)` com nomes/CMYK, por vezes livre. | API tem colour claim/disclaimer multilingue filtrável por `Accept-Language`, mas não foi validada normalização PT nacional. | B | Útil só para figurativas/logos; P2. |
| 8 | Pedido — classificação de Viena | Campo `(531)` com códigos Vienna. | A especificação pública consultada não expôs campo Vienna explícito no `Trademark` visível. | A | P2 para logo/figurativo; não MVP. |
| 9 | Concessão | Tabela com processo, data do registo, data do despacho, titular, país, classes, observações. | API tem `status=REGISTERED`, `registrationDate`, `statusDate`, `publications`; não garante texto/observação/despacho PT. | B | P0/P1 para converter publicação em evento jurídico e fechar oposição. |
| 10 | Recusa | Tabela com processo, data pedido, data recusa, titular, país, classes e fundamentos legais concretos, ex. “arts. 232.º...; 229.º...” | API tem `status=REFUSED` e `statusDate`; `decisions` tem `caseNumber`, `decisionDate`, `decisionKind`; a especificação pública não tem campo equivalente para fundamentos legais CPI textualizados. | A | P0. Alerta juridicamente útil, triagem e prospeção. |
| 11 | Renovações | Secção “Renovações” por lista de números de registo/processo. | API tem `expiryDate`, `renewalStatus`; records podem existir, mas não há lista textual BPI/página. | B | P1. Útil para auditoria; deadlines de renovação podem vir da API. |
| 12 | Caducidade por falta de pagamento de taxa | Tabela com processo, data registo, data caducidade, titular, país, observações. | API tem `status=EXPIRED` e `expiryDate`; não distingue necessariamente causa publicada. | B | P0/P1 para estado recoverable/dead e prospeção. |
| 13 | Caducidade por sentença | Observado em 2025-05-22: processo, data pedido, data da sentença, tribunal/processo e texto: recurso improcedente mantém recusa. | API tem `decisions` simplificado e `status`; a existência de reflexo noutros canais EUIPO/TMview não foi validada. | B | P1 para cadeia histórica/prova; não essencial para MVP básico. |
| 14 | Vigências por sentença | Observado no índice e página 33 do BPI 2026-06-26. | API pode refletir estado final/decision, mas não foi comprovado texto nacional nem equivalência de evento. | D | P1 se afetar direitos ativos; requer parser robusto e mais amostras. |
| 15 | Transmissões | Tabela com processo, data averbamento, antigo titular, país, atual titular, país, observações (“transmissão total”). | API tem `records` com `recordKind`, datas, estado; pode atualizar `applicants/owners`, mas o schema não inclui antigo vs atual titular no record. | B | P1 para cadeia de titularidade e prospeção. |
| 16 | Outros averbamentos art. 29.º | Ex.: pedido de declaração de nulidade apresentado no INPI, com requerente/requerido em texto livre. | API tem `records`, `cancellations`, `decisions`; pode haver reflexo genérico, mas a especificação pública não mostra texto/partes com esta granularidade. | B | P1/P2; relevante para litigância/auditoria. |
| 17 | Penhora / levantamento de penhora | Observado em 2026-06-26 e 2026-02-16: “averbamento da penhora/levantamento”, processo judicial, tribunal, exequente/executado. | API `records` pode ter recordKind genérico; a especificação pública não oferece campos estruturados de ónus, tribunal, exequente/executado. | B | P1 para risco jurídico e auditoria; cuidado RGPD. |
| 18 | Renúncias e renúncias parciais | Observado no índice e secções próprias; tabelas com datas e observações. | API tem `status=SURRENDERED`, records; não garante parcialidade/observação textual. | B | P1 para alteração de âmbito e deadlines. |
| 19 | Alteração de elementos não essenciais | Observado em 2025-05-22: processo, data alteração, elementos alterados, ex. alteração do sinal. | API pode refletir snapshot atualizado ou record genérico; não foi comprovado evento textual nem “antes/depois” equivalente. | B | P1/P2 para auditoria de alterações ao sinal. |
| 20 | Procuradores autorizados / contactos | Listas finais dos BPIs com nomes, cartório, telefone, email, web. | Persons API/representatives dão identificadores/nome; BPI dá contactos públicos pontuais. | D | Não compensa no MVP; risco RGPD/qualidade; usar Persons API/representantes por marca quando necessário. |
| 21 | Oposição apresentada / contestação como ato próprio em marcas nacionais | Não foi observada secção dedicada nas 5 amostras; só foi observado o prazo de reclamação/oposição em pedidos. Códigos ST.17 incluem fase de oposição. | API tem `oppositions.oppositionNumber`, `oppositionDate`, `status`; para PT nacional via TMview/API não comprovado. | D | Não assumir parser pronto; desenhar taxonomia para suportar quando aparecer. |

---

## 4. Catálogo de atos e campos observados no BPI

### 4.1 Estrutura geral relevante

Os BPIs examinados começam com sumário, códigos de rubricas ST.17 OMPI e depois secções por modalidade. Para marcas nacionais aparece “REGISTO NACIONAL DE MARCAS”. Também aparecem secções de marcas internacionais e logótipos; são úteis mas não equivalentes a marca nacional PT simples.

Rubricas/códigos observados no cabeçalho:

- BB — Publicação de pedidos e correspondente.
- FC — Recusas.
- FG — Concessão; Registo; Estatuto legal; Licenças.
- PC — Transmissão.
- QB — Licenças concedidas e registadas.
- HK — Retificações.
- MM — Caducidades.
- MA — Renúncias.
- RL — Despachos proferidos por sentença alterando.

A presença do código no cabeçalho não prova que o ato exista em todas as edições. Serve para taxonomia e reconhecimento estrutural.

### 4.2 Pedidos / publicações

Observado em todos os BPIs recentes.

Campos extraíveis:

- `bulletin_number`: ex. `2026/06/26`.
- `publication_date`: derivada do número/data do BPI.
- `page_number`: página onde começa/ocorre o pedido.
- `section`: `REGISTO NACIONAL DE MARCAS > Pedidos`.
- `legal_notice`: texto que cita art. 226.º e prazo de dois meses conforme art. 17.º CPI.
- `application_number`: campo `(210)`; ex. `770255`.
- `mark_type_or_series`: linha curta após `(210)`, ex. `MNA`.
- `application_date`: campo `(220)`, ex. `2026.06.02`.
- `priority`: campo `(300)`, por vezes vazio; exemplo observado com prioridade estrangeira/EM em 2026-02-16.
- `applicant_country`: em `(730)`, ex. `PT`, `DE`.
- `applicant_name`: em `(730)`; deve ser minimizado/normalizado.
- `goods_services`: campo `(511)` com classes e termos completos.
- `nice_classes`: derivável dos números dentro de `(511)`.
- `colour_claim`: campo `(591)`, ex. nomes de cores/CMYK.
- `verbal_element_or_caption`: campo `(540)` quando existe; ex. sinal nominativo.
- `vienna_codes`: campo `(531)`, ex. `26.4.3 ; 26.4.5 ; 29.1.3`.
- `raw_text_excerpt`: bloco do pedido.

Prazo desencadeado:

- Oposição/reclamação: 2 meses desde a data de publicação BPI, conforme texto do próprio BPI e CPI.

Exemplo não sensível:

- BPI 2026/06/26, páginas 14-15: pedido `(210) 770255`, `(220) 2026.06.02`, classe `42`, cores “preto; verde”, Vienna `26.4.3 ; 26.4.5 ; 26.4.12 ; 29.1.3`.

### 4.3 Concessões

Observado em 2026-06-26 e 2025-05-22.

Campos extraíveis:

- `application_number`/`process_number`.
- `registration_date`.
- `decision_date` / `dispatch_date`.
- `first_holder_name`.
- `holder_country`.
- `nice_classes`.
- `observations`.
- `bulletin_number`, `publication_date`, `page_number`, `raw_text_excerpt`.

Prazo/efeito:

- Fecha o ciclo de exame/oposição para muitos casos.
- Inicia/confirmar ciclo de vigência e renovação, conforme regras de marcas aplicáveis.

Exemplo:

- BPI 2026/06/26, página 31: tabela “Concessões” com colunas “Processo”, “Data do registo”, “Data do despacho”, “Nome do 1º requerente/titular”, “País resid.”, “Classes (Nice)”, “Observações”.

### 4.4 Recusas

Observado em 2026-06-26.

Campos extraíveis:

- `process_number`.
- `application_date`.
- `refusal_date`.
- `first_holder_name`.
- `holder_country`.
- `nice_classes`.
- `legal_basis`: artigos/alíneas do CPI.
- `observations`: texto legal livre.
- `bulletin_number`, `publication_date`, `page_number`, `raw_text_excerpt`.

Prazo/efeito:

- Evento de risco/alerta para o titular.
- Pode desencadear necessidade de resposta/recurso, mas o prazo exato deve ser parametrizado por tipo de despacho e confirmado juridicamente; não inferir automaticamente apenas do cabeçalho.

Exemplo não sensível:

- BPI 2026/06/26, página 34: processo `756704`, data pedido `2025.11.07`, data recusa `2026.06.22`, classe `39`, observações com `arts. 209.º, n.º 1, al. a); 231.º, n.º 1, al. b); 229.º, n.º 5 CPI 2018`.

Diferença crítica vs API:

- `status=REFUSED` diz o resultado; o BPI diz o ato publicado, data do despacho, fundamento legal e proveniência.

### 4.5 Renovações

Observado em 2025-05-22 e 2026-06-26.

Campos extraíveis:

- `registration_numbers`/`process_numbers`: muitas vezes uma lista compacta “N.os ...”.
- `bulletin_number`, `publication_date`, `page_number`.
- `raw_text_excerpt`.

Prazo/efeito:

- Confirma renovação publicada; útil para auditoria e evitar alertas falsos de expiração.

Limitação:

- A secção pode ser apenas lista de números, com baixa granularidade e sem titular/classes. Reconciliar por número contra base EUIPO/TMview/core.

### 4.6 Caducidades por falta de pagamento de taxa

Observado em 2025-05-22 e 2026-06-26.

Campos extraíveis:

- `process_number`.
- `registration_date`.
- `lapse_date`.
- `first_holder_name`.
- `holder_country`.
- `observations`.
- `bulletin_number`, `publication_date`, `page_number`, `raw_text_excerpt`.

Prazo/efeito:

- Alerta de perda/risco.
- Para prospeção: marcas caducadas recentemente podem ser oportunidades, mas usar apenas entidades coletivas ou base jurídica documentada.

Exemplo:

- BPI 2025/05/22, páginas 76-78: tabela “Caducidades por falta de pagamento de taxa” com data de registo e data de caducidade.

### 4.7 Caducidades por sentença / decisões judiciais

Observado em 2025-05-22.

Campos extraíveis:

- `process_number`.
- `application_date`.
- `judgment_date`.
- `holder_country`.
- `nice_classes`.
- `court`: extraível de texto livre, ex. Tribunal da Propriedade Intelectual.
- `court_case_number`: ex. formato `.../..YHLSB`, se presente.
- `decision_text`: excerto livre.
- `outcome`: inferível com cuidado, ex. mantém decisão de recusa.
- `bulletin_number`, `publication_date`, `page_number`.

Exemplo não sensível:

- BPI 2025/05/22, página 78: processo `682074`, data da sentença `2025.03.10`, classe `30`, observação indica que a sentença do Tribunal da Propriedade Intelectual julgou recurso improcedente e manteve a decisão de recusa.

### 4.8 Vigências por sentença

Observado no BPI 2026-06-26, índice/página 33.

Campos esperados/extraíveis conforme tabela quando presente:

- `process_number`.
- `registration_date` ou `application_date`.
- `judgment_date` / `dispatch_date`.
- `holder`.
- `country`.
- `nice_classes`.
- `observations` com texto de sentença.
- Proveniência BPI.

Classificação: confirmado como secção observada; extração detalhada precisa de mais amostras.

### 4.9 Transmissões

Observado em 2025-05-22 e 2026-06-26.

Campos extraíveis:

- `process_number`.
- `recordal_date`.
- `previous_holder_name`.
- `previous_holder_country`.
- `new_holder_name`.
- `new_holder_country`.
- `observations`: ex. “TRANSMISSÃO TOTAL”.
- `bulletin_number`, `publication_date`, `page_number`, `raw_text_excerpt`.

Exemplo não sensível:

- BPI 2025/05/22, página 79: tabela “Transmissões” com antigo e atual titular e observação “TRANSMISSÃO TOTAL” em alguns registos.

### 4.10 Outros averbamentos — artigo 29.º

Observado em 2025-05-22, 2026-02-16, 2026-03-16, 2026-06-26.

Campos extraíveis:

- `process_number`.
- `recordal_date`.
- `holder_name`.
- `holder_country`.
- `recordal_kind`: classificador a inferir do texto.
- `observations`: texto livre.
- Entidades relacionadas quando existirem: requerente/requerido, tribunal, processo judicial.
- Proveniência BPI.

Exemplo não sensível:

- BPI 2025/05/22, página 80: “AVERBAMENTO DO PEDIDO DE DECLARAÇÃO DE NULIDADE APRESENTADO NO INPI”, com requerente/requerido no texto.

### 4.11 Penhoras e levantamentos de penhora

Observado em 2026-02-16, 2026-03-16 e 2026-06-26.

Campos extraíveis:

- `process_number` da marca.
- `recordal_date`.
- `holder_name` e país.
- `encumbrance_type`: `seizure_recordal` ou `seizure_lifted`.
- `court_case_number`: mascarar/armazenar só se necessário.
- `court_name`.
- `claimant`/`defendant` quando pessoa coletiva e legalmente justificável.
- `observations`.
- Proveniência BPI.

Exemplo minimizado:

- BPI 2026/06/26, páginas 33 e 38-39: aparecem “averbamento do levantamento da penhora” e “AVERBAMENTO DA PENHORA PROCESSO Nº ...T8...”.

### 4.12 Renúncias e renúncias parciais

Observado em 2025-05-22, 2026-03-16 e 2026-06-26.

Campos extraíveis:

- `process_number`.
- `registration_date`.
- `surrender_date`.
- `holder_name`.
- `holder_country`.
- `scope`: total/parcial.
- `observations`: classes/produtos afetados quando presentes.
- Proveniência BPI.

Diferença vs API:

- API pode reduzir a `SURRENDERED`; o BPI permite distinguir renúncia parcial e texto de âmbito.

### 4.13 Alteração de elementos não essenciais

Observado em 2025-05-22.

Campos extraíveis:

- `process_number`.
- `change_date`.
- `changed_elements`.
- `new_value_text`, quando presente.
- Proveniência BPI.

Exemplo:

- BPI 2025/05/22, página 69: processo `563867`, data `2025.05.19`, texto “CONSIDERE-SE ALTERADO O SINAL DO REGISTO PARA: ...”.

Impacto:

- Útil para auditoria e comparação de sinal antes/depois; não necessário para alerta MVP.

### 4.14 Pedidos e avisos de deferimento de revalidação

Observado no índice e secções de 2025-05-22, 2026-03-16 e 2026-06-26.

Campos extraíveis:

- `process_number`.
- `request_or_deferral_date`.
- `holder`.
- `country`.
- `observations`.
- Proveniência BPI.

Impacto:

- Útil para marcas recuperáveis/reabilitadas e para evitar classificar como “dead” cedo demais.

### 4.15 Retificações / correções

Não foi observada secção com atos concretos de marca nas amostras, mas o cabeçalho ST.17 inclui `HK — Retificações` e existem “Outros Atos - Patente europeia - HK4A” noutras modalidades.

Classificação para marcas: D nesta sessão. Deve existir suporte taxonómico, mas não implementar parser específico sem amostras reais de marca.

### 4.16 Licenças

O cabeçalho ST.17 inclui `QB — Licenças concedidas e registadas`; nas 5 amostras, não encontrei uma secção concreta de licença de marca nacional com linhas parseáveis. Muitas ocorrências de “licenças” eram termos de produtos/serviços dentro de pedidos, não atos jurídicos.

Classificação para marcas: D nesta sessão. Não confundir ocorrências no texto Nice com atos de licença.

### 4.17 Procuradores autorizados

Observado no fim dos BPIs, com nome, cartório, telefone, email e web.

Decisão de produto:

- Não extrair no MVP. Não é evento de marca, traz dados pessoais/contactos, e a ligação a marcas específicas não é direta.
- Se for necessário para diretório profissional, usar base legal explícita, minimização e retenção curta.

---

## 5. Diferença conceptual: estado atual vs evento jurídico publicado

A distinção mais importante para Markee:

- EUIPO/API/TMview tende a responder: “qual é o estado atual da marca?” ou “quais são os objetos normalizados associados?”
- BPI responde: “que ato foi publicado oficialmente, em que dia, em que boletim, em que página, com que texto e que prazo/prova desencadeia?”

Exemplos:

1. `status=REFUSED` é um estado. “Recusa publicada no BPI 2026/06/26, página 34, com fundamentos arts. 232.º... e 229.º...” é um evento jurídico auditável.
2. `expiryDate`/`renewalStatus` calculam risco futuro. “Caducidade por falta de pagamento de taxa publicada no BPI, com data de caducidade X” é prova de perda efetiva.
3. `applicants` atualizado mostra o titular atual. “Transmissão total de antigo titular A para atual titular B, averbada em data X” preserva a cadeia histórica.
4. `records.recordKind` é útil, mas o BPI preserva observações livres como penhora, levantamento, nulidade, sentença, partes e tribunal.

---

## 6. Implicações para produto e deadlines

### 6.1 Deadline engine

P0:

- `opposition_deadline_pt`: pedido publicado em BPI + 2 meses.
- `refusal_response_or_review_watch`: recusa publicada; prazo exato deve ser configurável por tipo de despacho/fundamento e confirmado por jurista antes de automatizar contagem final.
- `grant_event`: concessão publicada; fecha watch de oposição e inicia auditoria de vigência.
- `lapse_event`: caducidade publicada; rever estado recoverable/dead.

P1:

- `assignment_recorded`: transmissão; alertar titulares/portfólios.
- `partial_surrender`: altera cobertura de classes/produtos.
- `court_decision`: decisão judicial/administrativa; alto valor para auditoria.
- `encumbrance_recorded`: penhora/ónus; alerta de risco.

### 6.2 Alertas de oposição

Para uma marca seguida:

1. Ingerir diariamente pedidos BPI.
2. Calcular similaridade contra watchlist por sinal + classes.
3. Criar alerta: “marca semelhante publicada no BPI n.º X, página Y; tem até D para reclamar/opôr-se”.
4. Guardar PDF hash + excerto para prova.

Isto é superior a depender apenas de `oppositionPeriodEndDate`, porque o BPI contém a origem legal portuguesa e permite demonstrar a publicação.

### 6.3 Alertas de recusa

Para marcas do utilizador ou prospects:

- Detetar `refusal_published` com fundamento CPI.
- Enviar resumo: processo, data do pedido, data da recusa, artigos, classes, página BPI.
- Para prospeção, limitar titulares individuais e contactos; priorizar empresas.

### 6.4 Auditoria e cadeia histórica

Guardar eventos BPI como imutáveis. Mesmo que a API altere `status`, a cadeia de eventos permite responder:

- quando foi publicado;
- em que boletim;
- que texto constava;
- que entidade/tribunal foi mencionado;
- se houve transmissão total/parcial, renúncia, caducidade ou revalidação.

---

## 7. Proposta de schema/pipeline

### 7.1 Taxonomia de eventos

Proposta normalizada:

| `event_type` | Origem BPI | Prioridade | Notas |
|---|---|---|---|
| `application_published` | Pedidos | P0 | Dispara oposição/reclamação PT. |
| `grant_published` | Concessões | P0 | Confirma registo/despacho. |
| `refusal_published` | Recusas | P0 | Incluir `legal_basis`. |
| `renewal_published` | Renovações | P1 | Muitas vezes só lista de números. |
| `lapse_fee_nonpayment` | Caducidades por falta de pagamento de taxa | P0/P1 | Causa específica. |
| `lapse_by_judgment` | Caducidades por sentença | P1 | Incluir tribunal/processo se necessário. |
| `validity_by_judgment` | Vigências por sentença | P1 | Requer mais amostras. |
| `assignment_recorded` | Transmissões | P1 | Antigo/atual titular. |
| `recordal_other` | Outros averbamentos art. 29.º | P1/P2 | Classificar subtipo por regex. |
| `encumbrance_recorded` | Penhora | P1 | RGPD/minimização. |
| `encumbrance_lifted` | Levantamento de penhora | P1 | Idem. |
| `surrender_total` | Renúncias | P1 | Se total. |
| `surrender_partial` | Renúncias parciais | P1 | Alteração de âmbito. |
| `non_essential_change` | Alteração de elementos não essenciais | P1/P2 | Pode alterar sinal. |
| `revalidation_requested` | Pedidos de revalidação | P1 | Recuperação. |
| `revalidation_deferred` | Avisos de deferimento de revalidação | P1 | Recuperação. |
| `correction_published` | Retificações | P2/D | Não observado para marcas nas amostras. |
| `license_recorded` | Licenças | P2/D | Não observado concretamente para marcas nas amostras. |
| `opposition_filed` | Oposições/contestações | D/P1 | Taxonomia pronta; amostra insuficiente. |

### 7.2 Campos de evento BPI

Adicionar/usar em `events.lifecycle_events.raw_data` ou tabela `events.bpi_events` dedicada:

```text
id
trademark_id nullable
source = 'bpi_pdf'
event_type
jurisdiction = 'PT'
application_number
registration_number nullable
publication_date
bulletin_number
bulletin_url
bulletin_sha256
page_number
section_path
st17_code nullable
act_date nullable
application_date nullable
registration_date nullable
decision_date nullable
lapse_date nullable
recordal_date nullable
legal_basis_text nullable
legal_basis_structured jsonb nullable
nice_classes int[] nullable
goods_services_excerpt text nullable
holder_name_normalized nullable
holder_country nullable
previous_holder_name_normalized nullable
new_holder_name_normalized nullable
representative_name nullable
related_process_numbers jsonb nullable
court_name nullable
court_case_number_hash nullable
observations text nullable
raw_text_excerpt text
parse_confidence numeric(3,2)
field_confidence jsonb
parser_version
dedupe_key
reconciliation_status
created_at
```

### 7.3 Proveniência mínima obrigatória

Para cada evento BPI:

- `source_url`: URL oficial do PDF.
- `retrieved_at`.
- `http_status`.
- `content_type`.
- `file_size_bytes`.
- `sha256` do PDF.
- `bulletin_number` e `publication_date`.
- `page_number`.
- `section_path`.
- `raw_text_excerpt` com limite, ex. 1 000-2 000 chars.
- `parser_name` e `parser_version`.
- `parse_confidence` global e `field_confidence` por campo.

### 7.4 Chave de deduplicação

Chave primária lógica sugerida:

```text
sha256(
  source='BPI' |
  bulletin_number |
  publication_date |
  section_path |
  event_type |
  application_or_registration_number |
  act_date_or_empty |
  normalized_legal_basis_or_empty |
  normalized_observation_hash_16
)
```

Notas:

- Para pedidos: usar `(bulletin_number, event_type, application_number)`.
- Para renovações em lista: usar `(bulletin_number, event_type, registration_number)`.
- Para transmissões: incluir hash de antigo+novo titular, porque o mesmo processo pode ter mais de um averbamento histórico.
- Para penhoras/nulidades/sentenças: incluir subtipo + hash de observações; o mesmo processo pode ter múltiplos atos.

### 7.5 Estratégia de reconciliação BPI ↔ EUIPO/TMview

1. Ingestão BPI diária:
   - descarregar PDF oficial;
   - calcular hash;
   - extrair páginas;
   - detetar secções;
   - extrair eventos;
   - guardar raw/proveniência.
2. Normalização:
   - normalizar números: remover espaços em `N.os 190 596` -> `190596` mas guardar original;
   - converter datas `YYYY.MM.DD` -> ISO;
   - normalizar classes `04` -> `4`;
   - separar `legal_basis_text` e `legal_basis_structured` por regex conservador.
3. Matching contra core:
   - chave forte: `application_number` ou `registration_number`;
   - chave secundária: número + país + classes;
   - nunca fundir só por nome/sinal.
4. Não duplicar eventos EUIPO:
   - se EUIPO tem `publications` com mesma data/secção e BPI tem evento, marcar `reconciled_with='euipo_publication'`, mas manter evento BPI como provenance jurídico.
   - se EUIPO só mudou `status`, ligar a mudança ao evento BPI por janela temporal: `statusDate` ± 7 dias e mesmo processo.
   - se conflito: não sobrescrever; criar `source_conflict` com prioridade BPI para publicação oficial PT e EUIPO/TMview para bibliografia/snapshot atual.
5. Confiança:
   - alta: secção reconhecida + número + data + página + tabela coerente.
   - média: secção reconhecida + número mas campos desalinhados.
   - baixa: texto livre sem tabela ou OCR suspeito; requer revisão manual.

### 7.6 Confiança de parsing sugerida

| Sinal | Peso |
|---|---:|
| Secção reconhecida | +0.20 |
| Número de processo/registo válido | +0.20 |
| Data do ato válida | +0.15 |
| Página/boletim extraídos | +0.15 |
| Classes Nice válidas quando esperadas | +0.10 |
| Cabeçalhos de tabela alinhados | +0.10 |
| Observações/fundamento legal extraído quando esperado | +0.10 |

Thresholds:

- `>=0.85`: automático.
- `0.65-0.84`: inserir mas marcar para revisão se o evento disparar alerta crítico.
- `<0.65`: guardar raw, não alertar sem revisão.

---

## 8. Prioridades de implementação

### P0 — Implementar já

1. Download, hash e arquivo de PDFs BPI.
2. Parser de secções `REGISTO NACIONAL DE MARCAS > Pedidos`.
3. Extração de pedidos: processo, data pedido, sinal `(540)`, classes/termos `(511)`, titular minimizado, cores/Vienna se simples, página, excerto.
4. Cálculo de `opposition_deadline_pt = publication_date + 2 meses`.
5. Parser de `Recusas` com fundamento legal.
6. Parser de `Concessões` com data de registo/despacho.
7. Parser de `Caducidades por falta de pagamento de taxa`.
8. Deduplicação e proveniência.

### P1 — Implementar depois do MVP de alertas

1. `Renovações` por lista de números.
2. `Transmissões` com antigo/atual titular.
3. `Renúncias` e `Renúncias parciais`.
4. `Outros averbamentos (artigo 29.º)` com classificador conservador: nulidade, penhora, levantamento, outros.
5. `Caducidades por sentença` e `Vigências por sentença`.
6. `Pedidos/Avisos de deferimento de revalidação`.
7. Parser de `legal_basis_structured` para artigos/alíneas CPI.
8. UI de auditoria: link para boletim, página, excerto.

### P2 — Só se houver procura ou depois de dados estáveis

1. Cores `(591)` avançadas e CMYK estruturado.
2. Vienna `(531)` estruturado para figurativas/logos.
3. Retificações específicas, após recolher amostras reais de marcas.
4. Licenças, após recolher amostras reais de marcas.
5. Decisões judiciais com parsing profundo de tribunal/partes, com política RGPD específica.
6. Parser de marcas internacionais e logótipos, se entrarem no plano comercial.

### Não compensa extrair no MVP

- Listas finais de procuradores autorizados com telefone/email/morada: não são eventos de marca; risco RGPD; atualização incerta; usar fontes próprias de representantes quando necessário.
- Contactos pessoais de titulares individuais para prospeção: risco jurídico/reputacional; limitar a pessoas coletivas e base legal documentada.
- Todas as ocorrências textuais de palavras como “licenças”, “transmissão”, “reclamações” dentro de listas de produtos/serviços: geram falsos positivos; só considerar cabeçalhos/zonas de ato.
- Dados de patentes, desenhos/modelos e outras modalidades no MVP de marcas: separar pipelines.
- OCR/imagens de sinal figurativo a partir do PDF BPI: melhor usar media endpoints/portal específico; BPI PDF é fraco para imagem.

---

## 9. Recomendações acionáveis

1. Separar claramente duas fontes:
   - EUIPO/TMview/API: pesquisa, similaridade, snapshot bibliográfico, atualização incremental.
   - BPI: eventos publicados, deadlines PT, auditoria/proveniência.
2. Guardar BPI mesmo quando o mesmo evento já parece refletido na API. Não é duplicação; é prova.
3. Não depender apenas de `status`. Um estado atual destrói história.
4. Implementar parser por secção, não por regex global. Nas amostras, termos de produtos/serviços contêm palavras como “transmissão”, “licenças” e “reclamações”, causando falsos positivos se a extração for ingénua.
5. Criar modo “review required” para eventos de baixa confiança que geram alertas jurídicos.
6. Validar prazos de recusa/recurso com jurista antes de prometer countdowns automáticos; o prazo de oposição de 2 meses para pedidos está forte porque aparece no próprio aviso BPI e no CPI.
7. Para prospeção, implementar desde o início filtros RGPD: pessoa coletiva vs singular, finalidade, retenção e supressão.

---

## 10. Conclusões com níveis de confiança

### Alta confiança

- O BPI português publica diariamente, em PDF, eventos jurídicos de marcas nacionais com número/data/página e secções estáveis.
- A publicação de pedidos de marcas nacionais no BPI inclui aviso que desencadeia prazo de 2 meses para reclamações/oposição, com referência aos artigos 226.º e 17.º do CPI.
- Recusas no BPI incluem fundamentos legais concretos por artigo/alínea do CPI, informação mais granular do que um simples estado `REFUSED`.
- Concessões, caducidades por falta de pagamento, transmissões, renúncias e alterações não essenciais foram observadas em amostras reais.
- A especificação pública EUIPO Trademark Search API 1.1.0 contém estados, publicações, records, decisions, oppositions/cancellations/appeals, mas o schema observado é normalizado e não contém, como campos equivalentes, página PDF, excerto BPI, classificação Vienna visível no `Trademark` ou fundamento legal CPI textualizado para recusas.

### Estritamente exclusivo/provado nesta sessão

- Publicação oficial no BPI com número/data do boletim, página e excerto diretamente verificáveis nos PDFs oficiais descarregados.
- Texto do aviso legal português que inicia o prazo de 2 meses para reclamações/oposição a partir da publicação do pedido.
- Fundamentos legais de recusas tal como publicados no BPI, incluindo artigos/alíneas do CPI.
- Texto livre de atos observados, como caducidade por sentença, transmissão, nulidade, penhora/levantamento, renúncia e alteração de elementos não essenciais.

### Mais granular no BPI face à especificação pública consultada

- Estados e eventos que a EUIPO Trademark Search API 1.1.0 modela de forma normalizada (`status`, `statusDate`, `publications`, `records`, `decisions`, `renewalStatus`, `oppositions`, `cancellations`, `appeals`) podem refletir parte do mesmo ciclo jurídico, mas a especificação pública não preserva necessariamente causa, texto livre, partes, tribunal, antigo/novo titular, página e excerto.
- Para produto, isto justifica guardar o BPI como provenance e não como substituto da pesquisa bibliográfica.

### Média confiança

- Para marcas nacionais PT via TMview, campos bibliográficos devem estar acessíveis na ferramenta agregada, mas não foi validada nesta sessão uma REST API TMview oficial pública nem uma consulta autenticada que confirme paridade de campos para PT.
- Eventos como penhora, nulidade, sentença, transmissão e renúncia podem ser parcialmente refletidos como `records`/`decisions` ou mudança de estado noutras fontes; a conclusão suportada é apenas que o BPI preserva detalhe textual superior nas amostras observadas.

### Baixa confiança / incerto

- Oposição apresentada/contestação como ato próprio de marca nacional não foi observada nas 5 amostras; existe suporte conceptual/códigos e a API modela oposições, mas é necessária recolha de mais BPIs com esse evento.
- Licenças de marca e retificações específicas de marca não foram observadas em linhas parseáveis nas amostras; não implementar extração dedicada sem amostras.
- A ausência de campos na especificação pública EUIPO Trademark Search API 1.1.0 não deve ser lida como ausência em todo o ecossistema EUIPO/TMview, Open Data, bulk data, UI TMview ou endpoints autenticados.

---

## 11. Anexo — fontes oficiais e datas de acesso

Acedido em 2026-07-24:

- INPI — Industrial Property Bulletin: https://inpi.justica.gov.pt/en-gb/Industrial-Property-Bulletin
- BPI 2026/06/26 PDF: https://inpi.justica.gov.pt/LinkClick.aspx?fileticket=iZmwYAaF9PI=&portalid=6
- BPI 2026/03/16 PDF: https://inpi.justica.gov.pt/LinkClick.aspx?fileticket=-iMgjyyClFo=&portalid=6
- BPI 2026/02/16 PDF: https://inpi.justica.gov.pt/LinkClick.aspx?fileticket=XTGR8zYPah4=&portalid=6
- BPI 2026/01/05 PDF: https://inpi.justica.gov.pt/LinkClick.aspx?fileticket=snvGugJAcl8=&portalid=6
- BPI 2025/05/22 PDF: https://inpi.justica.gov.pt/LinkClick.aspx?fileticket=kqzQX6KAGgw=&portalid=6
- EUIPO Developer Portal — Trademark search API 1.1.0: https://dev.euipo.europa.eu/product/trademark-search_110/api/trademark-search
- TMview / EUIPN: https://www.euipn.org/en/tools/TMview
- TMview: https://www.tmdn.org/tmview/
- Diário da República — Decreto-Lei n.º 110/2018: https://diariodarepublica.pt/dr/detalhe/decreto-lei/110-2018-117279933
- Diário da República — CPI consolidado: https://diariodarepublica.pt/dr/legislacao-consolidada/decreto-lei/2018-117279941-117317999
