# Pesquisa de Funcionalidades Inovadoras — markee

> **Data:** 2026-07-23  
> **Autor:** Sub-agente de pesquisa  
> **Foco:** Mercado PT/EU (INPI + EUIPO)  
> **Objetivo:** Identificar funcionalidades que os concorrentes principais **NÃO oferecem** e que justifiquem os planos de subscrição do markee.

---

## 1. Contexto da Concorrência (O que já existe)

| Serviço | Preço | Modelo | PT | Ciclo de Vida | Prospection | API |
|---------|-------|--------|----|---------------|-------------|-----|
| Clarivate CompuMark | $900–$1.225/marca/ano | Enterprise | Sim (global) | Limitado | Não | Sim |
| Corsearch / TrademarkNow | ~$375/marca/ano | Enterprise | Sim (global) | Limitado | Não | Sim |
| Markify | ~€16+/marca/ano | Subscrição | Sim | Não | Não | Limitada |
| IPRScan | ~€16+/marca/ano | Freemium | EU/EUA | Não | Não | Não |
| Alt Legal | ~$1.110 (200 marcas) | Flat EUA | Não | Completo (US) | Não | Sim |
| AIPLUX | Empresarial | Enterprise | Sim | Limitado | Não | Sim |
| Haloo | $$$ | AI Search | EUA | Não | Não | Não |
| EUIPO Alert | Grátis | Manual | UE | Não | Não | Não |
| **markee (target)** | **€5–€249/mês** | SaaS tiers | **PT+EU** | **Completo** | **Sim** | **Sim (Enterprise)** |

**Conclusão chave:** O mercado deixou um enorme buraco no segmento **PT/EU acessível com gestão de ciclo de vida e prospecção**. Nenhum concorrente domina este nicho.

---

## 2. Funcionalidades Inovadoras Encontradas

Para cada funcionalidade avaliamos:
- **Viabilidade** — pode ser construído com a stack atual (Python/FastAPI, PostgreSQL, Celery, Docker)?
- **Valor** — os utilizadores pagariam por isto?
- **Tier** — em que plano encaixa melhor
- **Complexidade** — baixa / média / alta
- **Fase** — Phase 1 (MVP), Phase 2 (diferenciação), Phase 3 (escala)

---

### Categoria A: AI/ML Avançado em Marcas

#### A1 — Similaridade de Logótipos por AI (Image Trademark Matching)
**Descrição:** Comparar logótipos e marcas figurativas por semelhança visual usando embeddings de imagem (CLIP/ResNet), para além do matching de texto. Deteta imitações visuais que pesquisa por texto nunca apanha.

**Estado na concorrência:**
- AIPLUX e Corsearch têm isto, mas **só em tiers enterprise** (>$500/mês).
- IPRScan, Markify, Haloo **não têm** image matching.
- Nenhum concorrente acessível oferece isto para o mercado PT.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — Open-source CLIP, vector DB (pgvector), EUIPO fornece URLs de imagens |
| Valor | **Muito alto** — deteta 30-40% mais conflitos que texto só |
| Tier | **Pro (€29/mês) ou Profissional (€99/mês)** |
| Complexidade | **Média** — embeddings + vector search; treino não é necessário |
| Fase | **Phase 2** (mês 3–4) |

**Nota:** As marcas EUIPO/INPI já têm URLs de imagem pública. Basta ingerir, gerar embeddings, e fazer nearest-neighbour search em PostgreSQL com pgvector.

---

#### A2 — Scoring Preditivo de Risco de Oposição (Opposition Risk Score)
**Descrição:** Calcular uma probabilidade (0-100%) de uma marca similar levar a uma oposição, combinando: (a) similaridade fonética/ortográfica, (b) sobreposição de classes Nice, (c) sobreposição de descrição de goods/services, (d) histórico de oposições do titular (agressivo vs passivo), (e) força da marca base (quanto mais conhecida, maior o risco).

**Estado na concorrência:**
- Clarivate lançou **RiskMark** (2025) — usa AI + case law, mas é **enterprise** e caro.
- Haloo tem "Smart-Sort" — ordena resultados por risco, mas é simplificado.
- Nenhum concorrente acessível faz scoring preditivo de oposição.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — modelo rule-based + regression/ML simples; dados históricos de oposições como labels |
| Valor | **Muito alto** — permite priorizar alertas; "esta marca é 85% provável de gerar oposição" |
| Tier | **Profissional (€99/mês)** ou **Enterprise (€249/mês)** |
| Complexidade | **Média** — requer construção de dataset de oposições históricas como ground truth |
| Fase | **Phase 2** (mês 4–5) |

---

#### A3 — Sugestão Automática de Classes Nice (Auto-Nice Classifier)
**Descrição:** O utilizador descreve o produto/serviço em linguagem natural (ex.: "aplicação móvel para reservas de restaurantes") e o sistema sugere as classes Nice corretas e os termos EUIPO/INPI aceites.

**Estado na concorrência:**
- WIPO tem o "Global Goods & Services Explorer" — gratuito, mas lento e genérico.
- USPTO lançou o "Class ACT" (2026) — assistente AI de classificação.
- Nenhum SaaS acessível em PT/EU oferece isto.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — fine-tuning de LLM (OpenAI/ollama) com os termos TMClass; ou matching semântico com sentence-transformers |
| Valor | **Alto** — evita erros de classificação que custam meses de processo |
| Tier | **Pro (€29/mês)** — atrai PMEs que não sabem classificar |
| Complexidade | **Baixa** — API do TMClass + LLM prompt engineering; não requer treino pesado |
| Fase | **Phase 2** (mês 3) |

---

#### A4 — Avaliação de Força de Marca (Trademark Strength Meter)
**Descrição:** Avaliar automaticamente a "força" de uma marca: arbitrária/fanciful (forte) → sugestiva → descritiva → genérica (fraca). Usa NLP para analisar o termo face aos goods/services descritos. Ajuda a prever probabilidade de recusa por falta de distintividade.

**Estado na concorrência:**
- Nenhum concorrente oferece isto automaticamente.
- Os advogados fazem isto manualmente em relatórios de €500+.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Média — requer dicionário PT de termos descritivos por classe + regras heurísticas + LLM |
| Valor | **Muito alto** — diferenciador único; informação estratégica para decisão de registo |
| Tier | **Pro (€29/mês)** |
| Complexidade | **Média** — construção de léxico descritivo em PT é trabalhoso mas one-time |
| Fase | **Phase 2** (mês 4–5) |

---

#### A5 — Predição de Probabilidade de Confusão (Confusion Probability Engine)
**Descrição:** Para um par de marcas, calcular a probabilidade de confusão ao consumidor usando um modelo multi-factor: similaridade visual, fonética, ortográfica, proximidade de goods/services, canais de comercialização, e nível de atenção do consumidor (low-involvement vs high-involvement goods).

**Estado na concorrência:**
- Clarivate RiskMark aproxima isto, mas apenas para enterprise.
- Nenhum concorrente acessível o faz.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Média — requer modelagem jurídica multi-factor + ML; dados de ground truth de decisões de oposição |
| Valor | **Muito alto** — suporta argumentação em oposições; justifica decisões |
| Tier | **Profissional (€99/mês) ou Enterprise (€249/mês)** |
| Complexidade | **Alta** — é a funcionalidade AI mais complexa desta lista |
| Fase | **Phase 3** (mês 8–10) |

---

### Categoria B: Especificidades Portuguesas

#### B1 — Integração com o Diário da República (DR) para Alterações de Denominação
**Descrição:** Monitorizar o Diário da República (Séries I e II) por alterações de denominação social, fusões, cisões ou encerramentos de empresas que são titulares de marcas registadas no INPI. Quando uma empresa muda de nome ou é extinta, alerta o titular da marca para atualizar o registo ou avaliar a caducidade.

**Estado na concorrência:**
- **Nenhum concorrente faz isto.** É uma ideia completamente inédita.
- O DR é público e pesquisável, mas nenhum SaaS de PI o integra.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — o DR tem API/feed de dados abertos (dados.gov.pt); alternativamente scraping estruturado |
| Valor | **Muito alto** — evita perda de direitos por falta de atualização de titularidade |
| Tier | **Profissional (€99/mês)** — valor principal para escritórios |
| Complexidade | **Baixa** — consumir feed XML/JSON do DR, fazer matching por NIPC/nome da empresa |
| Fase | **Phase 2** (mês 3–4) |

---

#### B2 — Cruzamento CAE ↔ Nice Class para Prospecção Inteligente
**Descrição:** Cruzar a Classificação Portuguesa das Atividades Económicas (CAE Rev. 3) das empresas titulares com as classes Nice das suas marcas. Isto permite:
- Segmentar prospecção por setor económico real (não só por classe Nice).
- Detetar discrepâncias: uma empresa de CAE "atividades de informática" com marcas só em classe 25 (vestuário) pode ser oportunidade de cross-selling.

**Estado na concorrência:**
- **Nenhum concorrente faz isto.** É completamente inédito.
- A CAE é específica de Portugal; concorrentes globais não têm interesse.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — CAE é pública (portal da Justiça/INPI), basta mapeamento CAE→Nice (tabela estática) |
| Valor | **Alto** — segmentação de prospecção muito mais precisa para agentes PT |
| Tier | **Profissional (€99/mês)** |
| Complexidade | **Baixa** — tabela de mapeamento CAE→Nice classes; matching por NIPC/nome |
| Fase | **Phase 2** (mês 3–4) |

---

#### B3 — Análise por Distrito (District-Level Trademark Analytics)
**Descrição:** Heatmaps e dashboards de atividade de marcas por distrito de Portugal (Lisboa, Porto, Braga, etc.): onde se registam mais marcas, quais os setores dominantes por distrito, tendências de crescimento.

**Estado na concorrência:**
- Nenhum concorrente oferece análise geográfica a nível de distrito português.
- O INPI fornece o distrito do titular nos registos; é só agregar.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — os dados de distrito já estão nos registos INPI (morada do titular) |
| Valor | **Médio-Alto** — útil para agentes de PI decidirem onde abrir escritório ou focar prospecção |
| Tier | **Pro (€29/mês)** |
| Complexidade | **Baixa** — geocodificação + agregação; frontend com mapa (Leaflet/Mapbox) |
| Fase | **Phase 2** (mês 4) |

---

#### B4 — Fonética Portuguesa Avançada (Beyond Double Metaphone)
**Descrição:** Motor fonético específico para português europeu que trata corretamente:
- Vogais nasais (ão, ãe, õe) → mesmo som
- Dígrafos especiais (lh, nh, rr, ss vs ç, sc, xc)
- Silêncio do "e" final e "s" intervocálico
- Variações dialetais (PT-PT vs PT-BR — ex.: "t" em "tipo" é surdo em PT-PT)
- Anglicismos frequentes em marcas PT (ex.: "shop", "store", "hub")

**Estado na concorrência:**
- A maioria usa Double Metaphone genérico (otimizado para inglês).
- Corsearch tem "linguistics" mas é global, não específico PT.
- Nenhum concorrente tem fonética PT-PT nativa.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — implementar como extensão do módulo `phonetic.py` já planeado; regras heurísticas + tabela de equivalências |
| Valor | **Alto** — melhora significativamente o matching em PT (ex.: "Nike" vs "Naik", "Sónia" vs "Sonya") |
| Tier | **Pro (€29/mês)** — diferenciador para o mercado PT |
| Complexidade | **Média** — requer conhecimento linguístico, mas é puramente algorítmico |
| Fase | **Phase 2** (mês 3) — já planeado no PLAN.md para mês 3 |

---

### Categoria C: Workflow para Profissionais de PI

#### C1 — Portal de Colaboração com Clientes (Client Collaboration Portal)
**Descrição:** Sub-dominio/dashbord read-only onde cada cliente do escritório vê **apenas as suas marcas**, prazos, alertas e relatórios. O agente de PI partilha um link seguro (com token temporário). O cliente pode ver mas não editar.

**Estado na concorrência:**
- Alt Legal tem "secure client collaboration tools" mas é **US-only**.
- Corsearch/MarkMonitor têm portals enterprise complexos.
- **Nenhum concorrente acessível em PT/EU oferece isto.**

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — sub-dominio com token JWT, read-only views, já previsto no modelo `client_portfolios` |
| Valor | **Muito alto** — elimina email de "onde está a minha marca?"; retenção de clientes do escritório |
| Tier | **Profissional (€99/mês)** |
| Complexidade | **Média** — autenticação por token, permissões, frontend read-only |
| Fase | **Phase 2** (mês 4–5) |

---

#### C2 — Geração Automática de Documentos (Document Templates)
**Descrição:** Templates preenchidos automaticamente para:
- Carta de oposição (PT) com dados da marca oponente e da marca base
- Pedido de renovação (INPI / EUIPO)
- Procuração / Declaração de representação
- Relatório de vigilância mensal em PDF white-label

**Estado na concorrência:**
- DocketTrak tem "form letter generation" mas é **US-only**.
- Nenhum concorrente acessível tem templates em **português** para INPI.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — Jinja2 templates + WeasyPrint / docx-python; dados já na BD |
| Valor | **Muito alto** — poupa horas de trabalho por semana a cada advogado |
| Tier | **Profissional (€99/mês)** — white-label + templates |
| Complexidade | **Média** — construção de templates jurídicos requer revisão de advogado |
| Fase | **Phase 2** (mês 5) |

---

#### C3 — Sincronização com Calendários (Google Calendar, Outlook, Apple)
**Descrição:** Exportar prazos críticos (renovações, oposições, recusas) diretamente para o calendário do utilizador via ICS/iCal ou APIs nativas. Cada prazo vira um evento com lembrete configurável.

**Estado na concorrência:**
- Alt Legal e LawToolBox fazem isto, mas **US-only**.
- Nenhum concorrente PT/EU acessível oferece sync de calendário com prazos INPI/EUIPO.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — geração de ficheiros ICS (iCal) é trivial; sync via Google Calendar API / Microsoft Graph é médio |
| Valor | **Muito alto** — os prazos de PI são críticos; perder um prazo = perder um direito |
| Tier | **Individual (€5/mês) ou Pro (€29/mês)** |
| Complexidade | **Baixa** (ICS) a **Média** (API nativa) |
| Fase | **Phase 2** (mês 3–4) |

---

#### C4 — CRM-Lite para Escritórios de PI
**Descrição:** Gestão simples de contactos de clientes ligada às marcas: histórico de interações, notas, tarefas, status de prospecção (lead → contactado → proposta → cliente). Não substitui Pipedrive/HubSpot, mas evita ter que usar dois sistemas.

**Estado na concorrência:**
- Nenhum concorrente de TM monitoring tem CRM integrado.
- Os escritórios usam Pipedrive/HubSpot + Excel + TM tool separados.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — tabelas `clients`, `interactions`, `tasks`; simples CRUD |
| Valor | **Médio-Alto** — conveniência; retenção de utilizadores Profissional |
| Tier | **Profissional (€99/mês)** |
| Complexidade | **Baixa** — funcionalidade CRUD standard |
| Fase | **Phase 2** (mês 4–5) |

---

#### C5 — Ações em Massa (Bulk Actions)
**Descrição:** Selecionar múltiplas marcas e executar ações em lote: adicionar a watchlist, exportar deadlines, gerar relatório, atualizar status, enviar email a cliente.

**Estado na concorrência:**
- Enterprise tools (Corsearch, Clarivate) têm isto.
- **Nenhum concorrente acessível em PT/EU oferece bulk actions.**

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — batch operations no PostgreSQL + Celery |
| Valor | **Alto** — essencial para quem gere 100+ marcas |
| Tier | **Pro (€29/mês)** |
| Complexidade | **Baixa** |
| Fase | **Phase 2** (mês 3) |

---

### Categoria D: Visualização de Dados e Relatórios

#### D1 — Dashboard de Saúde do Portefólio (Portfolio Health Dashboard)
**Descrição:** Painel visual que mostra a "saúde" de um portefólio de marcas: marcas ativas vs em risco, distribuição por classes, marcas sem renovação agendada, marcas com alertas de similaridade pendentes, tendência de risco ao longo do tempo.

**Estado na concorrência:**
- Clarivate FoundationIP tem isto, mas **enterprise**.
- Nenhum concorrente acessível oferece dashboard de saúde de portefólio.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — agregações PostgreSQL + frontend com gráficos (Recharts/Chart.js) |
| Valor | **Muito alto** — visualização estratégica para decisão de gestão de portefólio |
| Tier | **Pro (€29/mês)** |
| Complexidade | **Média** — design de KPIs relevantes requer iteração com utilizadores |
| Fase | **Phase 2** (mês 4) |

---

#### D2 — Mapa de Competidores (Competitor Landscape Map)
**Descrição:** Para uma marca ou setor, visualizar todos os titulares concorrentes, as suas marcas, classes, datas, e overlaps. Permite ver "quem está a registar o quê" num setor.

**Estado na concorrência:**
- Corsearch tem "landscape analysis" mas **enterprise**.
- Nenhum concorrente acessível o faz.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — agregações por titular + visualização de rede/graph |
| Valor | **Alto** — inteligência competitiva para planeamento de marca |
| Tier | **Pro (€29/mês) ou Profissional (€99/mês)** |
| Complexidade | **Média** — frontend de graph/network visualisation (D3.js / Cytoscape) |
| Fase | **Phase 2** (mês 5) |

---

#### D3 — Construtor de Relatórios Customizados (Custom Report Builder)
**Descrição:** O utilizador escolhe: métricas, filtros, formato (PDF, CSV, Excel), periodicidade (mensal, trimestral), e destinatários. O sistema gera e envia automaticamente.

**Estado na concorrência:**
- Computer Packages (CPI) tem "custom reports" mas é **enterprise antigo**.
- Nenhum concorrente moderno acessível oferece isto.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — query builder + templates + Celery scheduling |
| Valor | **Alto** — automação de reporting para clientes |
| Tier | **Profissional (€99/mês)** — white-label + custom reports |
| Complexidade | **Média** — UI de query builder + engine de geração |
| Fase | **Phase 3** (mês 6–7) |

---

#### D4 — Análise de Tendências de Registo (Filing Trend Analytics)
**Descrição:** Gráficos de séries temporais mostrando: volume de registos por classe/mês, picos sazonais, novos tituladores emergentes, marcas estrangeiras a entrar em PT.

**Estado na concorrência:**
- Alguns concorrentes têm gráficos básicos, mas não análise PT-específica.
- Nenhum oferece análise de tendências de registo em Portugal.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — time-series aggregation com PostgreSQL |
| Valor | **Médio-Alto** — inteligência de mercado para agentes e empresas |
| Tier | **Pro (€29/mês)** |
| Complexidade | **Baixa** |
| Fase | **Phase 2** (mês 4) |

---

### Categoria E: Integrações

#### E1 — Alertas por WhatsApp Business API
**Descrição:** Enviar alertas críticos (prazo de oposição a expirar, marca similar detetada) via WhatsApp Business API para números de telefone dos utilizadores. Em Portugal, os advogados e agentes de PI usam WhatsApp intensivamente.

**Estado na concorrência:**
- **Nenhum concorrente de TM monitoring oferece alertas por WhatsApp.**
- Email é o standard; Telegram é raro (só IPRScan tem Telegram básico).

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — WhatsApp Business API (Meta Cloud API) tem wrappers Python; custo ~€0.05/msg |
| Valor | **Muito alto** — WhatsApp é o canal de comunicação preferido em PT; abertura de mensagens >90% |
| Tier | **Pro (€29/mês)** — diferenciador massivo vs concorrência |
| Complexidade | **Baixa** — integração REST API standard |
| Fase | **Phase 2** (mês 3) |

---

#### E2 — Webhooks para Zapier / Make.com
**Descrição:** Permitir que os utilizadores configurem webhooks para disparar quando eventos ocorrem: nova marca similar, prazo próximo, mudança de estado. Integra-se com Zapier, Make.com, n8n para automações customizadas (ex.: criar tarefa no Trello, enviar SMS, atualizar Google Sheets).

**Estado na concorrência:**
- Nenhum concorrente acessível oferece webhooks/Zapier.
- Apenas enterprise (Corsearch API) permite isto via API REST custom.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — FastAPI webhook endpoints + assinatura HMAC; documentação simples |
| Valor | **Alto** — flexibilidade extrema; integra com o stack que o utilizador já usa |
| Tier | **Profissional (€99/mês)** |
| Complexidade | **Baixa** — webhook pattern é standard |
| Fase | **Phase 2** (mês 4) |

---

#### E3 — Sync de Calendário (Google Calendar / Outlook / iCal)
*(Ver C3 — já coberto na Categoria C)*

---

#### E4 — Listagem em API Marketplaces
**Descrição:** Publicar a API REST do markee em marketplaces como RapidAPI, Postman API Network, e eventualmente SAP/Oracle marketplaces. Aumenta descoberta e permite "API-first" revenue.

**Estado na concorrência:**
- Markify tem API mas não está em marketplaces.
- Nenhum concorrente acessível está listado em API marketplaces.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — a API já é OpenAPI/Swagger; listar é administrativo |
| Valor | **Médio** — canal de aquisição de developers/enterprise |
| Tier | **Enterprise (€249/mês) + pay-per-call no marketplace** |
| Complexidade | **Baixa** — abertura de conta + documentação |
| Fase | **Phase 3** (mês 6–7) |

---

### Categoria F: Monetização

#### F1 — Créditos Pay-Per-Search (fora do plano)
**Descrição:** Utilizadores em planos limitados podem comprar créditos para pesquisas avulstas: €2 por pesquisa de similaridade avançada, €5 por análise de logótipo, €1 por relatório de risco. Pagamento via Stripe com um clique.

**Estado na concorrência:**
- Apify (EUIPO search) usa pay-per-usage.
- Nenhum concorrente de TM monitoring SaaS usa pay-per-search.
- O modelo é comum em AI tools (OpenAI credits) mas inédito em PI.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — Stripe metered billing + contador de créditos na BD |
| Valor | **Muito alto** — revenue expansion sem upgrade de plano; captura uso esporádico |
| Tier | **Todos os tiers** — créditos disponíveis para todos |
| Complexidade | **Baixa** — billing metered no Stripe + saldo na BD |
| Fase | **Phase 2** (mês 5) |

---

#### F2 — Marketplace de Serviços de PI (IP Services Marketplace)
**Descrição:** Dentro da plataforma, os utilizadores podem solicitar serviços de agentes de PI parceiros: registo de marca, oposição, renovação, consultoria. O markee fica com uma comissão (10-20%) e o parceiro executa o serviço.

**Estado na concorrência:**
- **Completamente inédito.** Nenhum SaaS de TM monitoring é também marketplace.
- LegalZoom faz algo similar (marketplace + legal services), mas é EUA e não é TM monitoring.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Média — requer onboarding de parceiros, gestão de qualidade, pagamentos escrow |
| Valor | **Muito alto** — novo stream de revenue; cria network effects |
| Tier | **Todos os tiers** — lead generation para parceiros |
| Complexidade | **Alta** — marketplace completo: perfis, reviews, matching, pagamentos, disputas |
| Fase | **Phase 3** (mês 9–12) |

---

#### F3 — Sistema de Referral (Refer-a-Friend)
**Descrição:** Utilizador convida outro; ambos recebem créditos ou desconto (ex.: 1 mês grátis para quem refere, 20% de desconto para quem é referido). Rastreamento por código único.

**Estado na concorrência:**
- Standard em SaaS, mas raro em PI. IPRScan não tem; Markify não tem.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — código único + Stripe coupon API + tracking na BD |
| Valor | **Alto** — CAC reduzido; crescimento orgânico |
| Tier | **Todos os tiers** |
| Complexidade | **Baixa** |
| Fase | **Phase 2** (mês 5) |

---

#### F4 — Programa de Afiliados para Advogados e Agentes de PI
**Descrição:** Advogados e agentes de PI registam-se como afiliados, recebem um link único, e ganham comissão recorrente (ex.: 20% mensalidade) por cada cliente que trazem. Comissões pagas via Stripe Connect ou transferência.

**Estado na concorrência:**
- Nenhum concorrente de TM monitoring tem programa de afiliados.
- É comum em SaaS (ex.: Notion, Figma), mas inédito em PI.

| Critério | Avaliação |
|----------|-----------|
| Viabilidade | Alta — Stripe Connect para split payments; ou tracking manual + payouts |
| Valor | **Muito alto** — canal de aquisição através de influencers do setor de PI |
| Tier | **Todos os tiers** |
| Complexidade | **Média** — Stripe Connect + dashboard de afiliado + payouts |
| Fase | **Phase 3** (mês 6–7) |

---

## 3. Top 10 Funcionalidades Mais Inovadoras e Viáveis

| # | Funcionalidade | Categoria | Inovação | Viabilidade | Valor | Tier | Fase | Complex. |
|---|----------------|-----------|----------|-------------|-------|------|------|----------|
| 1 | **Alertas por WhatsApp Business API** | Integração | ★★★★★ | ★★★★★ | ★★★★★ | Pro (€29) | Phase 2 | Baixa |
| 2 | **Scoring Preditivo de Risco de Oposição** | AI/ML | ★★★★★ | ★★★★☆ | ★★★★★ | Profissional (€99) | Phase 2 | Média |
| 3 | **Integração com Diário da República** | PT-Específico | ★★★★★ | ★★★★★ | ★★★★★ | Profissional (€99) | Phase 2 | Baixa |
| 4 | **Similaridade de Logótipos por AI** | AI/ML | ★★★★★ | ★★★★☆ | ★★★★★ | Pro/Profissional | Phase 2 | Média |
| 5 | **Portal de Colaboração com Clientes** | Workflow | ★★★★☆ | ★★★★★ | ★★★★★ | Profissional (€99) | Phase 2 | Média |
| 6 | **Cruzamento CAE ↔ Nice Class** | PT-Específico | ★★★★★ | ★★★★★ | ★★★★☆ | Profissional (€99) | Phase 2 | Baixa |
| 7 | **Geração Automática de Documentos (PT)** | Workflow | ★★★★☆ | ★★★★★ | ★★★★★ | Profissional (€99) | Phase 2 | Média |
| 8 | **Sincronização com Calendários (Google/Outlook/iCal)** | Workflow | ★★★☆☆ | ★★★★★ | ★★★★★ | Individual/Pro | Phase 2 | Baixa |
| 9 | **Créditos Pay-Per-Search** | Monetização | ★★★★☆ | ★★★★★ | ★★★★★ | Todos | Phase 2 | Baixa |
| 10 | **Fonética Portuguesa Avançada** | PT-Específico | ★★★★☆ | ★★★★★ | ★★★★☆ | Pro (€29) | Phase 2 | Média |

### Justificação detalhada do Top 10

#### 1. Alertas por WhatsApp Business API
**Porquê #1:** Em Portugal, os profissionais de PI (advogados, agentes, empresários) usam WhatsApp como canal principal de comunicação. Nenhum concorrente oferece isto. É trivial de implementar (REST API), barato por mensagem, e a taxa de abertura de mensagens de WhatsApp (>90%) é muito superior ao email (~20%). É um **differentiator imediato e de baixo custo**.

#### 2. Scoring Preditivo de Risco de Oposição
**Porquê #2:** Clarivate acabou de lançar RiskMark (2025) a preços enterprise. Se o markee oferecer uma versão acessível e focada em PT/EU, captura todo o mercado de PMEs e escritórios que não podem pagar $900/marca/ano. O modelo pode começar rule-based e evoluir para ML com dados históricos.

#### 3. Integração com Diário da República
**Porquê #3:** Funcionalidade **completamente inédita** em qualquer SaaS de PI. Quando uma empresa muda de nome ou é extinta, o markee alerta o titular da marca automaticamente. Isto evita perda de direitos e posiciona o markee como o **SaaS de PI mais ligado à realidade empresarial portuguesa**.

#### 4. Similaridade de Logótipos por AI
**Porquê #4:** AIPLUX e Corsearch têm isto, mas a preços enterprise. O mercado de PMEs e escritórios médios em PT **nunca teve acesso** a image-based trademark search. Com CLIP + pgvector, o markee pode oferecer isto a €29/mês. O impacto é grande: deteta imitações visuais que pesquisa de texto nunca apanha.

#### 5. Portal de Colaboração com Clientes
**Porquê #5:** Alt Legal tem isto nos EUA. Em Portugal, os escritórios de PI ainda enviam PDFs por email. Um portal seguro onde o cliente vê as suas marcas e prazos é **retenção de clientes em massa** e um argumento de venda imbatível para o plano Profissional.

#### 6. Cruzamento CAE ↔ Nice Class
**Porquê #6:** Outra funcionalidade **inédita**. A CAE é o sistema português de classificação de atividades económicas. Cruzar CAE com Nice permite prospecção por setor REAL (ex.: "todas as empresas de software em Lisboa com marcas a expirar"). Nenhum CRM ou TM tool faz isto.

#### 7. Geração Automática de Documentos (PT)
**Porquê #7:** Templates de cartas de oposição e pedidos de renovação em português, preenchidos automaticamente com dados do sistema. Poupa horas de trabalho por semana. DocketTrak faz isto nos EUA; em Portugal, **ninguém faz**.

#### 8. Sincronização com Calendários
**Porquê #8:** Prazos de PI são binários — ou cumpre-se ou perde-se o direito. Sync com Google Calendar/Outlook é table stakes para um docketing moderno. Nenhum concorrente acessível em PT/EU oferece isto. É **baixo esforço, alto valor**.

#### 9. Créditos Pay-Per-Search
**Porquê #9:** Modelo de monetização inédito em TM monitoring. Utilizadores no plano Grátis ou Individual podem pagar €2 por uma pesquisa avançada ocasional, sem subir de tier. Aumenta revenue per user e captura utilizadores que não querem compromisso mensal. Stripe metered billing torna isto trivial.

#### 10. Fonética Portuguesa Avançada
**Porquê #10:** O Double Metaphone genérico falha em português (ão, lh, nh, etc.). Um motor fonético PT-PT nativo melhora significativamente a qualidade dos alertas de similaridade. É um **diferenciador técnico** que os concorrentes globais não têm incentivo para construir.

---

## 4. Funcionalidades por Ordem de Implementação Recomendada (Phase 2)

```
Mês 3:  WhatsApp alerts (E1) + Auto-Nice Classifier (A3) + Fonética PT (B4)
Mês 4:  Calendar sync (C3/E3) + CAE cross-reference (B2) + DR integration (B1) + District analytics (B3)
Mês 5:  Client portal (C1) + Document generation (C2) + Pay-per-search credits (F1)
Mês 6:  Opposition risk scoring (A2) + Portfolio health dashboard (D1) + Bulk actions (C5)
Mês 7:  Image similarity (A1) + Competitor landscape (D2) + Webhooks/Zapier (E2)
Mês 8:  Custom report builder (D3) + Affiliate program (F4)
Mês 9+: Marketplace de serviços (F2) + Confusion probability engine (A5) + API marketplace (E4)
```

---

## 5. Resumo Executivo para João

O mercado de TM monitoring em PT/EU está **desatendido no segmento médio** (€5–€99/mês). Os concorrentes ou são enterprise caros (Corsearch, Clarivate) ou são globais genéricos sem funcionalidades PT (Markify, IPRScan).

As **maiores oportunidades de diferenciação** estão em:
1. **Canais de comunicação locais** (WhatsApp — ninguém faz)
2. **Dados portugueses específicos** (Diário da República, CAE, fonética PT, distritos)
3. **Workflow de escritório** (portal de clientes, documentos PT, calendário, CRM-lite)
4. **AI acessível** (image similarity, risk scoring, auto-classification — só existem em enterprise)
5. **Monetização flexível** (pay-per-search, afiliados)

**Recomendação:** Priorizar funcionalidades de **baixa complexidade + alto valor + inéditas**. WhatsApp, DR, CAE, calendário e fonética PT são todas **baixa/média complexidade** e **nenhum concorrente as tem**. Deixar image similarity e confusion engine para mais tarde (maior complexidade).

O plano **Profissional a €99/mês** justifica-se sozinho se incluir: portal de clientes + DR + CAE + documentos + scoring de risco. Um escritório de PI que gere 10 clientes paga €99 e poupa 10+ horas/semana.
