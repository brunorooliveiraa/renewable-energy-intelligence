# Plano de desenvolvimento — Renewable Energy Intelligence

> **Projeto de portfólio | Engenharia de Dados + Análise de Dados + Energias Renováveis**  
> **Problema central:** investigar restrições de geração (*constrained-off* / *curtailment*) em empreendimentos eólicos brasileiros com dados abertos do ONS.  
> **Foco inicial:** Ceará; evolução para Nordeste e energia solar.  
> **Status:** Fases 1 e 2 concluídas localmente; pronto para iniciar a Fase 3 (transformação e validação).

---

## 1. Visão geral

### 1.1. O que vamos construir?

Uma aplicação web com um pipeline reproduzível que:

1. **Extrai** arquivos oficiais do Operador Nacional do Sistema Elétrico (ONS).
2. **Inspeciona e valida** a qualidade dos registros.
3. **Transforma** os dados de restrição em tabelas adequadas à análise.
4. **Calcula indicadores** de geração, restrições e diferença frente à geração de referência, com unidades e premissas explícitas.
5. **Armazena** os resultados em um banco SQL.
6. **Exibe** um dashboard interativo para análise temporal, comparação de empreendimentos e investigação de motivos.
7. **Documenta e publica** metodologia, código e resultados no GitHub.

### 1.2. Problema de negócio

Empreendimentos eólicos podem sofrer limitações de geração por condições externas, requisitos de confiabilidade, razões energéticas e outras restrições registradas pelo ONS. Gestores e analistas precisam identificar onde, quando e por que essas ocorrências se concentram e qual é a diferença entre geração verificada e referências operacionais disponíveis.

**Pergunta principal:** *Como evoluem as restrições de geração eólica no Ceará e quais empreendimentos, períodos e razões concentram os maiores impactos energéticos estimados?*

### 1.3. Perguntas que o dashboard deve responder

- Qual foi a geração verificada dos empreendimentos monitorados no período selecionado?
- Em quantos intervalos foram registrados códigos de restrição?
- Qual foi a **diferença estimada entre geração de referência final e geração verificada** nos intervalos válidos e classificados como restrição?
- Como esse indicador evoluiu por dia, mês e horário?
- Quais usinas **ou conjuntos de usinas** concentram os maiores valores?
- Qual é a distribuição por **razão** (`REL`, `CNF`, `ENE`, `PAR`) e por **origem** (`LOC`, `SIS`)?
- Quais registros têm lacunas, valores ausentes ou problemas de qualidade?

### 1.4. Objetivo profissional

Demonstrar domínio de **Python, Pandas, SQL, ETL, séries temporais, análise exploratória, visualização, testes e Git/GitHub**, aplicados a um problema real do setor elétrico brasileiro.

---

## 2. Escopo e prioridades

### 2.1. MVP — primeira versão funcional

- **Tecnologia:** geração eólica.
- **Geografia:** Ceará (`id_estado = 'CE'`, conforme dicionário do ONS).
- **Período inicial de desenvolvimento:** janeiro a março de **2025**; ampliar depois que o pipeline estiver validado.
- **Granularidade de origem:** registros semi-horários publicados pelo ONS.
- **Recursos essenciais:** extração, tratamento, indicadores, banco PostgreSQL (Neon / Vercel Storage), API serverless FastAPI (`api/index.py`) e dashboard web em HTML, CSS e JavaScript hospedado gratuitamente na Vercel.
- **Publicação:** repositório público no GitHub com instruções para reproduzir os resultados e aplicação web + API hospedadas na Vercel.

### 2.2. Segunda versão

- Incluir todo o histórico **2025** e os meses publicados de **2026**, informando a data de atualização.
- Comparar estados do Nordeste, evitando confundir amostra monitorada com toda a geração estadual.
- Incorporar dados de geração **fotovoltaica**.
- Relacionar empreendimentos ao cadastro ANEEL/SIGA por **CEG válido**, quando houver correspondência.
- Incluir indicadores complementares de fator de capacidade quando a comparação metodológica for válida.

### 2.3. Fora do escopo do MVP

- Previsão por aprendizado de máquina.
- Monitoramento em tempo real; os dados são históricos e podem sofrer revisão.
- Cálculo de indenização, receita perdida ou valores em reais.
- Diagnóstico causal conclusivo de falhas de equipamentos.
- Afirmar que a diferença entre referência e geração corresponde automaticamente à **energia indenizável** ou à **perda financeira**.

---

## 3. Fontes oficiais e documentação

| Fonte | Link | Uso no projeto | Prioridade |
|---|---|---|---|
| ONS — restrições eólicas | https://dados.ons.org.br/dataset/restricao_coff_eolica_usi | Base principal, por usina ou conjunto de usinas | **MVP** |
| ONS — dicionário da base eólica | https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/restricao_coff_eolica_tm/DicionarioDados_RestricaoContrainedoff_UsiEolicas.pdf | Colunas, semântica, unidades e códigos | **MVP** |
| ONS — detalhamento de restrições eólicas | https://dados.ons.org.br/dataset/restricao_coff_eolica_detail | Investigar granularidade em usinas individuais | Evolução |
| ONS — restrições fotovoltaicas | https://dados.ons.org.br/dataset/restricao_coff_fotovoltaica | Comparação com energia solar | Evolução |
| ONS — fator de capacidade eólico/solar | https://dados.ons.org.br/dataset/fator-capacidade-2 | Indicador complementar de aproveitamento | Evolução |
| ANEEL — SIGA | https://dadosabertos.aneel.gov.br/dataset/siga-sistema-de-informacoes-de-geracao-da-aneel | Cadastro de empreendimentos, capacidade e localização | Evolução |

**Cuidados com as fontes:**

- Os conjuntos do ONS são revisáveis. Salvar **fonte, URL, nome do arquivo, mês de referência, data da coleta e versão/hash** sempre que possível.
- O conjunto principal contém linhas referentes a **usinas e conjuntos**. Não tratar indiscriminadamente cada linha como uma usina individual.
- A coluna `ceg` pode trazer `-` para conjuntos de usinas. **Não forçar `JOIN` com ANEEL nesses casos**.
- Consultar dicionários atualizados antes de assumir que campos e regras não mudaram entre meses.
- ONS: atribuição de crédito conforme licença **CC BY**; ANEEL/SIGA: observar os termos **ODbL**.

---

## 4. Definições técnicas e métricas

### 4.1. Campos prioritários do ONS (eólicas)

O dicionário oficial contém, entre outros:

| Campo original | Significado | Tratamento previsto |
|---|---|---|
| `id_estado` | Sigla da UF | Filtrar `CE` no MVP |
| `nom_usina` | Usina ou conjunto de usinas | Preservar nome e identificador |
| `id_ons` | Identificador no ONS | Chave principal de agregação por empreendimento/conjunto |
| `ceg` | Código ANEEL, quando existente | Chave opcional de enriquecimento |
| `din_instante` | Data/hora do registro | Converter para `datetime` e verificar fuso |
| `val_geracao` | Geração verificada em **MWmed** | Numérico; negativos são auditados, sem bloqueio na ausência de regra oficial específica |
| `val_geracaolimitada` | Geração limitada, em **MWmed** | Numérico, pode ser nulo |
| `val_disponibilidade` | Disponibilidade verificada, em **MWmed** | Numérico, pode ser nulo |
| `val_geracaoreferencia` | Geração de referência, em **MWmed** | Numérico, pode ser nulo |
| `val_geracaoreferenciafinal` | Geração de referência **final**, em **MWmed** | Referência principal a investigar |
| `cod_razaorestricao` | Motivo `REL`, `CNF`, `ENE`, `PAR` | Classificar sem alterar código original |
| `cod_origemrestricao` | Origem `LOC`, `SIS` | Classificar local/sistêmica |
| `dsc_restricao` | Texto descritivo da restrição | Preservar para exploração qualitativa |
| `id_pontoconexao` | Identificador do ponto de conexão | Preservar como texto |
| `nom_pontoconexao` | Nome do ponto de conexão | Preservar como texto |
| `nom_agenteoperador` | Agente responsável pela operação | Preservar como texto |
| `val_geracaonaorealizadaapurada` | Geração Não Realizada Apurada (GNRa) | Campo oficial prioritário; unidade pendente de confirmação documental |
| `num_minutos_rel` | Minutos de restrição `REL` no patamar | Numérico entre 0 e 30 quando preenchido |
| `num_minutos_cnf` | Minutos de restrição `CNF` no patamar | Numérico entre 0 e 30 quando preenchido |
| `num_minutos_ene` | Minutos de restrição `ENE` no patamar | Numérico entre 0 e 30 quando preenchido |
| `num_minutos_restricao` | Minutos com qualquer restrição no patamar | Não reaplicar automaticamente como ponderador da GNRa |

**Atenção às unidades:** `MWmed` é potência média no intervalo, **não** energia em MWh. Como a série é semi-horária, a conversão de potência média para energia do intervalo é `MWmed × 0,5 h`, **desde que a duração/semântica desse registro tenha sido conferida**.

### 4.2. Indicadores do MVP

1. **Geração verificada (MWh)** = `Σ(val_geracao × duração_horas)` em registros válidos.
2. **Geração de referência final (MWh)** = `Σ(val_geracaoreferenciafinal × duração_horas)` onde a referência existir.
3. **Intervalos classificados com restrição** = contagem de intervalos com código de razão válido; documentar se a fonte inclui linhas sem restrição.
4. **Geração Não Realizada Apurada (GNRa)** = utilizar prioritariamente `val_geracaonaorealizadaapurada`, campo publicado pelo ONS. A forma de agregação e conversão energética só será definida depois da confirmação documental da unidade. Manter a conciliação com `max(val_geracaoreferencia − val_geracao, 0)` como validação, não como substituição silenciosa do valor oficial.
5. **Empreendimentos/conjuntos distintos** = `nunique(id_ons)` (não chamar de quantidade de parques individuais sem validação).
6. **Distribuição das restrições** por razão (`REL`, `CNF`, `ENE`, `PAR`), origem (`LOC`, `SIS`), data e empreendimento.
7. **Indicadores de qualidade** = percentual de nulos por campo, duplicidades e intervalos esperados/observados, sem equiparar lacunas da cobertura a dados faltantes de operação.

### 4.3. Regras metodológicas obrigatórias

- **Não** chamar automaticamente a GNRa de “energia efetivamente desperdiçada”, energia indenizável ou perda financeira. Usar o nome oficial do campo e expor razões, cobertura e limitações.
- **Não** substituir automaticamente nulos por zero em medidas de potência ou referência.
- Não recalcular a GNRa para substituir silenciosamente o valor oficial. A fórmula `max(..., 0)` pode ser usada para conciliação, mantendo divergências e casos negativos visíveis.
- Não somar `MWmed` de intervalos diferentes como se fosse energia.
- Não comparar dois períodos sem explicitar cobertura e disponibilidade dos registros.
- Agregar **uma única linha por chave única de origem/intervalo** antes de somar, para evitar duplicidade ao combinar arquivos e cadastros.
- Se a documentação apontar outra definição do indicador, **corrigir a fórmula e registrar a decisão no `docs/metodologia.md`**.

---

## 5. Arquitetura proposta (Vercel + FastAPI + Neon PostgreSQL)

```text
                   DADOS ABERTOS — ONS (API CKAN / S3)
                            |
                     download / extração (local ou GitHub Actions)
                            |
                   data/raw/ (originais + .metadata.json)
                            |
                 leitura + validação + limpeza (pandas / pyarrow)
                            |
                   data/processed/ (.parquet)
                            |
                      carga idempotente em lote (psycopg v3)
                            |
               PostgreSQL gerenciado (Neon / Vercel Storage)
                            |
                 API Serverless FastAPI (api/index.py — leve, sem pandas)
                            |
              aplicação web estática na Vercel — HTML + CSS + JavaScript
                            |
                    Dashboard interativo
```

**Tecnologias:** Python 3.11+, Pandas, NumPy, Requests, PyArrow, **PostgreSQL (Neon via Vercel Storage)**, **`psycopg` v3**, **FastAPI**, HTML5, CSS3, JavaScript, Pytest, Git/GitHub e **Vercel (Hobby Plan)**. Para respeitar o limite de bundle (250 MB) e timeout (10 s) da Vercel, `requirements.txt` mantém apenas `fastapi` e `psycopg[binary]`, enquanto `requirements-etl.txt` concentra as dependências do pipeline ETL e testes. Detalhes em `docs/arquitetura_vercel.md`.

### 5.1. Estrutura de pastas planejada

```text
renewable-energy-intelligence/
├── plano.md
├── README.md
├── vercel.json                  # Roteamento de /api/* (FastAPI) e frontend estático na Vercel
├── requirements.txt             # Dependências leves da API serverless na Vercel (FastAPI + psycopg)
├── requirements-etl.txt         # Dependências completas do pipeline ETL, análise e testes
├── .gitignore
├── .env.example                 # Modelo de DATABASE_URL (pooled) e DIRECT_DATABASE_URL (Neon)
├── LICENSE
├── api/
│   ├── __init__.py
│   └── index.py                 # Entrypoint FastAPI serverless (/api/health e rotas analíticas)
├── frontend/
│   ├── index.html               # Entrada da aplicação web
│   └── assets/
│       ├── css/styles.css       # Estilos responsivos
│       └── js/app.js            # Comportamento e visualizações (consome /api/*)
├── src/
│   ├── __init__.py
│   ├── extract.py               # Descoberta CKAN, download seguro, revisões/hash e faixa de meses
│   ├── transform.py             # Limpeza, tipagem e normalização
│   ├── validate.py              # Regras de qualidade e unicidade de chave
│   ├── metrics.py               # Indicadores e agregações
│   ├── database.py              # Escrita idempotente e consultas PostgreSQL (Neon)
│   └── pipeline.py              # Orquestração das etapas ETL
├── data/
│   ├── raw/.gitkeep             # Downloads originais (não versionar CSVs grandes)
│   └── processed/.gitkeep       # Saídas tratadas (não versionar arquivos grandes)
├── database/.gitkeep            # Reservado para artefatos auxiliares locais não versionados
├── notebooks/
│   └── 01_exploracao.ipynb
├── sql/
│   └── schema.sql               # DDL PostgreSQL (tabelas fato, dimensão, auditoria e agregações)
├── tests/
│   ├── test_api.py
│   ├── test_extract.py
│   ├── test_transform.py
│   ├── test_metrics.py
│   └── test_quality.py
├── docs/
│   ├── arquitetura_vercel.md
│   ├── metodologia.md
│   ├── dicionario_dados.md
│   ├── extracao.md
│   └── imagens/                 # Capturas do dashboard
└── .github/workflows/
    └── ci.yml                   # Testes automáticos e ETL agendado (evolução)
```

### 5.2. Modelo de dados mínimo

**Tabela `fact_restricoes`:** identificador ONS, CEG bruto, nome da usina/conjunto, UF, instante, MWmed verificado, MWmed de referência final, MWmed limitado, razão, origem, descrição, arquivo de origem, data da ingestão e indicadores calculados **com metodologia versionada**.

**Tabela `dim_empreendimentos`:** `id_ons` (chave do ONS), nome de exibição, UF e `ceg` quando válido. A tabela ANEEL será opcional e só será incorporada com correspondência comprovada.

**Tabela `etl_execucoes`:** fonte, arquivo, período, hora da coleta, quantidade de linhas, quantidade rejeitada, hash/versão e situação da execução.

---

## 6. Roadmap executável — tarefas em ordem

### Fase 0 — Preparação do ambiente

- [x] Criar repositório `renewable-energy-intelligence` no GitHub.
- [x] Criar pasta local e inicializar Git (`git init`) ou clonar o repositório.
- [x] Criar e adicionar este arquivo como `plano.md`.
- [x] Criar a árvore de diretórios proposta na seção 5.1.
- [x] Criar ambiente virtual do Python.
- [x] Instalar dependências e salvar `requirements.txt`.
- [x] Criar `.gitignore`: `.venv/`, `__pycache__/`, `.env`, `data/raw/*`, `data/processed/*`, `database/*.db`, mantendo `.gitkeep`.
- [ ] Fazer primeiro commit com a estrutura e o plano.

**Comandos sugeridos (Windows PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install pandas numpy requests pyarrow pytest jupyter
pip freeze > requirements.txt
```

**Critério de conclusão:** abrir o projeto no VS Code, ativar ambiente e executar `python --version` e `git status` sem erro.

### Fase 1 — Reconhecimento dos dados (primeira tarefa prática)

- [x] Abrir a página de restrições eólicas do ONS.
- [x] Baixar **manualmente o CSV de janeiro de 2025** na seção “Dados e recursos”.
- [x] Salvar o original em `data/raw/RESTRICAO_COFF_EOLICA_2025_01.csv`.
- [x] Abrir o dicionário oficial e comparar os nomes de colunas.
- [x] Criar `notebooks/01_exploracao.ipynb`.
- [x] Inspecionar codificação, delimitador, separador decimal, tipos e quantidade de registros.
- [x] Executar: `.head()`, `.info()`, `.describe()`, `.isna().sum()`, `.duplicated().sum()`.
- [x] Verificar `id_estado`, `id_ons`, `ceg`, `din_instante`, `cod_razaorestricao` e medidas de potência.
- [x] Filtrar Ceará e verificar quantos empreendimentos/conjuntos e intervalos aparecem.
- [x] Investigar se cada linha representa uma observação única de `id_ons` + `din_instante`.
- [x] Registrar descobertas, dúvidas e decisões iniciais em `docs/dicionario_dados.md`.

**Critério de conclusão:** conseguir explicar o significado de cada coluna usada no projeto, quantidade de registros e cobertura temporal do mês.

### Fase 2 — Extração automática (`src/extract.py`)

- [x] Investigar a **API CKAN** do portal ONS para descobrir recursos por conjunto/mês e formato, sem copiar dezenas de URLs manualmente.
- [x] Criar função de descoberta de arquivos (`dataset`, `ano`, `mes`, `formato`).
- [x] Criar função de download com `requests`, timeout, tentativas com limite e mensagens de erro.
- [x] Salvar nomes previsíveis: `ons_eolica_YYYY_MM.csv`.
- [x] Não sobrescrever silenciosamente um arquivo que possa ter sido revisado; registrar versão/hash.
- [x] Salvar metadados da coleta (data/hora, URL de origem, nome, tamanho e hash quando possível).
- [x] Permitir escolher um mês ou uma faixa de meses.
- [x] Tratar meses sem arquivo publicado de forma explícita.

**Critério de conclusão:** um script baixa o mês solicitado e registra a origem sem intervenção manual. Caso a API não funcione, documentar uma fonte alternativa de URL e manter a ingestão reproduzível.

### Fase 3 — Transformação e validação (`src/transform.py` + `src/validate.py`)

- [x] Ler CSV com separador/decimal/codificação confirmados na Fase 1.
- [x] Padronizar nomes internos sem perder o mapeamento para os nomes originais.
- [x] Converter `din_instante` para data/hora e documentar o fuso aplicável.
- [x] Converter valores em MWmed para tipos numéricos, sem arredondar precocemente.
- [x] Filtrar `id_estado == 'CE'` para o MVP.
- [x] Manter `id_ons` como identificador e preservar `ceg` como texto (inclusive `-`).
- [x] Verificar duplicidades na chave e decidir a regra de resolução **antes** de somar.
- [x] Identificar nulos, valores negativos observados, códigos desconhecidos e datas fora do mês.
- [ ] Criar sinalizadores de elegibilidade para cada indicador.
- [ ] Calcular `duracao_horas` somente após validar granularidade; inicialmente, expectativa de 0,5 h.
- [ ] Preservar a GNRa oficial e criar colunas de energia em MWh somente após confirmar documentalmente as unidades e regras descritas na seção 4.
- [ ] Salvar base tratada em `data/processed/restricoes_eolicas_ce_2025_01.parquet`.
- [ ] Gerar relatório de qualidade: linhas de entrada/saída, nulos, duplicidades e rejeições justificadas.

**Critério de conclusão:** transformação repetível, sem perdas silenciosas de dados, com métricas de qualidade e regras documentadas.

### Fase 4 — Análise exploratória e indicadores (`src/metrics.py`)

- [ ] Contar linhas por mês, dia, hora, razão e origem de restrição.
- [ ] Criar série diária e mensal da geração verificada em MWh.
- [ ] Agregar a GNRa oficial somente após confirmar sua unidade e os registros elegíveis; manter uma conciliação separada com geração e referência.
- [ ] Contabilizar a cobertura das linhas elegíveis e as linhas sem referência.
- [ ] Criar ranking por `id_ons` + nome de exibição, indicando usina ou conjunto quando possível.
- [ ] Comparar razões `REL`, `CNF`, `ENE`, `PAR` e origens `LOC`, `SIS`.
- [ ] Identificar horários/dias com maiores valores do indicador exploratório.
- [ ] Anotar **três achados concretos**, com período, unidades, amostra e limitações.
- [ ] Conferir manualmente alguns cálculos com registros reais do CSV original.

**Critério de conclusão:** um notebook ou script produz os indicadores, os gráficos básicos e pelo menos três conclusões sustentadas por números verificáveis.

### Fase 5 — Banco PostgreSQL (Neon / Vercel) e API FastAPI (`sql/schema.sql` + `src/database.py` + `api/index.py`)

- [ ] Definir esquema PostgreSQL das tabelas (`fact_restricoes`, `dim_empreendimentos`, `etl_execucoes` e tabelas/views pré-agregadas) com chaves de unicidade e índices.
- [ ] Provisionar o banco PostgreSQL gratuito (Neon via Vercel Storage) e configurar `DATABASE_URL` (pooled) e `DIRECT_DATABASE_URL` no `.env` local e na Vercel.
- [ ] Implementar a carga idempotente (`ON CONFLICT ... DO UPDATE` / transação por período) da base tratada no PostgreSQL via `psycopg` v3 (executar duas vezes não deve duplicar linhas).
- [ ] Escrever consultas SQL parametrizadas para indicadores diários, mensais, motivos, ranking e qualidade.
- [ ] Criar índices para `instante`, `ons_id`, `estado_sigla` e códigos de restrição conforme necessidade.
- [ ] Implementar os endpoints de leitura FastAPI em `api/index.py` (`/api/overview`, `/api/timeseries`, `/api/enterprises`, `/api/reasons`, `/api/quality`) usando `DATABASE_URL` pooled e sem importar `pandas`.
- [ ] Comparar os totais SQL/API com os resultados do Pandas.

**Critério de conclusão:** as consultas PostgreSQL e os endpoints FastAPI reproduzem os mesmos totais do pipeline sem duplicações e respondem bem abaixo do timeout de 10 s da Vercel.

### Fase 6 — Dashboard web (`frontend/` hospedado na Vercel)

- [ ] Definir e documentar o contrato JSON dos endpoints FastAPI (`/api/*`) consumidos pelo frontend, sem permitir acesso direto do navegador ao PostgreSQL.
- [ ] Criar estrutura semântica e acessível em HTML com identidade visual, título, descrição e explicação do escopo.
- [ ] Criar estilos responsivos em CSS para telas grandes e dispositivos móveis.
- [ ] Implementar o comportamento e as visualizações em JavaScript, com estados explícitos de carregamento, erro e ausência de dados.
- [ ] Adicionar filtros de período, empreendimento/conjunto, razão e origem.
- [ ] Criar **aba 1 — Visão geral**: cartões de geração verificada, déficit estimado, intervalos com restrição e empreendimentos/conjuntos cobertos.
- [ ] Criar gráfico temporal diário/mensal do indicador de restrição.
- [ ] Criar **aba 2 — Empreendimentos**: ranking, busca por nome/`id_ons` e série de cada empreendimento.
- [ ] Criar **aba 3 — Motivos**: distribuição por razão e origem; detalhe descritivo quando disponível.
- [ ] Criar **aba 4 — Qualidade e metodologia**: fontes, períodos cobertos, nulos, alertas e definição dos indicadores.
- [ ] Exibir unidades em todos os gráficos: MWh, MWmed, contagem de intervalos, %.
- [ ] Mostrar data da última coleta e aviso de que registros podem ser revisados.
- [ ] Criar estados de interface para filtros sem resultado (não exibir zero falso).
- [ ] Evitar carregamentos repetidos e desnecessários; definir cache do navegador ou da camada de dados somente quando houver evidência de necessidade.
- [ ] Adicionar exportação CSV das agregações filtradas, se viável.

**Critério de conclusão:** alguém que nunca viu o código consegue responder às perguntas da seção 1.3 utilizando apenas o dashboard.

### Fase 7 — Testes e revisão

- [ ] Criar dados sintéticos pequenos para testar as fórmulas sem depender da internet.
- [ ] Testar que 100 MWmed em **um intervalo de 30 minutos** equivalem a **50 MWh**.
- [ ] Testar separadamente a conciliação da GNRa em MWmed e a conversão de potência média para MWh, sem misturar o valor oficial com uma fórmula substituta.
- [ ] Testar que `NaN` na referência não vira zero e não entra indevidamente no cálculo.
- [ ] Testar que linhas duplicadas não duplicam totais.
- [ ] Testar códigos desconhecidos e ausência de `ceg`.
- [ ] Testar meses sem dados, filtros sem resultado e uso de datas diferentes.
- [ ] Conferir totais em Pandas, SQL e dashboard para um período fixo.
- [ ] Fazer revisão ortográfica de títulos, legendas e metodologia.

**Critério de conclusão:** todos os testes passam, totais conciliam e as limitações aparecem claramente na interface.

### Fase 8 — Expansão do histórico e do escopo

- [ ] Processar janeiro a dezembro de 2025, mês a mês.
- [ ] Processar meses disponíveis de 2026 com indicação de possível incompletude/revisão.
- [ ] Adicionar comparação entre CE, RN, BA, PI, PE e outros estados conforme cobertura da base.
- [ ] Testar desempenho do pipeline com múltiplos meses.
- [ ] Investigar o conjunto ONS de detalhamento por usinas antes de chamar um conjunto de parque individual.
- [ ] Integrar ANEEL/SIGA por CEG **somente quando a correspondência for validada**.
- [ ] Avaliar a inclusão de fonte solar mediante novo dicionário e regras adequadas.
- [ ] Avaliar atualização automatizada (GitHub Actions) sem exceder limites de armazenamento/processamento.

**Critério de conclusão:** o projeto processa vários meses, reproduz resultados e permite comparações regionais com cobertura explícita.

### Fase 9 — Publicação profissional

- [ ] Escrever `README.md` com problema, objetivo, arquitetura, stack, metodologia resumida, fontes, execução e imagens.
- [ ] Incluir aviso de que o projeto **não é produto oficial do ONS/ANEEL**.
- [ ] Referenciar as instituições, páginas de dados e licenças.
- [ ] Incluir `docs/metodologia.md` com fórmulas, premissas, elegibilidade e limitações.
- [ ] Adicionar capturas reais do dashboard a `docs/imagens/`.
- [ ] Incluir instruções de `git clone`, instalação, ingestão e inicialização do app.
- [ ] Excluir bases brutas grandes, banco SQLite local, credenciais e arquivos temporários do Git.
- [ ] Criar exemplos pequenos e legalmente compatíveis apenas se necessários para reproduzir testes.
- [ ] Criar `LICENSE` para o **código próprio**, sem confundir a licença do código com a dos dados públicos.
- [ ] Fazer commits claros e publicar no GitHub.
- [ ] Hospedar a aplicação web, caso o volume e a infraestrutura permitam, documentando como os dados processados são publicados e atualizados.
- [ ] Testar o projeto em um ambiente limpo, seguindo somente o README.
- [ ] Adicionar ao portfólio e currículo: problema, stack e link do projeto.

**Critério de conclusão:** um recrutador pode acessar o repositório, entender o problema e reproduzir pelo menos a análise do MVP.

---

## 7. Ordem dos commits sugeridos

| Marco | Nome de commit sugerido | O que deve funcionar |
|---|---|---|
| 1 | `docs: add project plan and structure` | Plano e diretórios |
| 2 | `chore: setup python environment` | Ambiente e dependências |
| 3 | `feat: explore ONS wind curtailment data` | Leitura e análise inicial |
| 4 | `feat: automate ONS data ingestion` | Download de arquivo por mês |
| 5 | `feat: clean and validate raw records` | Dataset tratado e relatório de qualidade |
| 6 | `feat: calculate curtailment exploration metrics` | Métricas documentadas |
| 7 | `feat: persist data and add SQL queries` | Banco e consultas |
| 8 | `feat: build web dashboard` | Aplicação HTML, CSS e JavaScript navegável |
| 9 | `test: validate ETL and metric calculations` | Testes automatizados |
| 10 | `docs: publish methodology and dashboard` | README e evidências |

---

## 8. Contratos de execução a implementar

**Estes comandos são interfaces planejadas, não funcionalidades já prontas.** Implementar gradualmente na Fase 2 a 5.

```powershell
# Extrair um mês (previsto para a Fase 2)
python -m src.extract --year 2025 --month 1 --source eolica

# Tratar um mês (previsto para a Fase 3)
python -m src.transform --year 2025 --month 1 --state CE

# Executar pipeline completo (previsto para a Fase 5)
python -m src.pipeline --year 2025 --month 1 --state CE

# Abrir a fundação do frontend localmente
python -m http.server 8000 --directory frontend

# Testar (previsto para a Fase 7)
pytest -q
```

Ao escrever os scripts, usar parâmetros claros e configurar o caminho dos dados a partir da raiz do projeto; não embutir diretórios absolutos do computador.

---

## 9. Critérios de aceite do MVP (Definition of Done)

O MVP estará pronto quando:

- [ ] O período janeiro–março de 2025 puder ser baixado e processado novamente.
- [ ] A origem dos dados, revisão e data da coleta estiverem registradas.
- [ ] As colunas, unidades, chaves e regras de exclusão estiverem documentadas.
- [ ] Os registros elegíveis e não elegíveis para cálculos estiverem separados.
- [ ] O banco evitar duplicação ao reexecutar o pipeline.
- [ ] O dashboard tiver filtros funcionais e pelo menos três análises úteis.
- [ ] Todos os indicadores apresentarem unidades e notas metodológicas.
- [ ] Os testes de conversão e agregação passarem.
- [ ] O projeto rodar a partir de um clone limpo seguindo o README.
- [ ] O GitHub contiver código organizado, documentação e capturas reais.

---

## 10. Checklist — o que fazer agora (primeiro dia)

1. [x] Criar repositório e colocar este arquivo `plano.md` na raiz.
2. [x] Criar `.venv` e instalar `pandas`, `numpy`, `requests`, `pyarrow`, `pytest` e `jupyter`.
3. [x] Criar `data/raw/`, `data/processed/`, `notebooks/` e `src/`.
4. [x] Baixar **um CSV eólico de janeiro/2025** diretamente do portal do ONS.
5. [x] Ler o CSV no Pandas, descobrir delimitador/decimal e imprimir colunas, tipos e cinco linhas.
6. [x] Filtrar Ceará e identificar quantidade de `id_ons`, intervalo de datas, valores ausentes e razões de restrição.
7. [ ] Salvar as primeiras observações no notebook e dar o primeiro commit.

**Primeira entrega concreta:** notebook com inspeção de um mês, confirmação das colunas e um pequeno diagnóstico da cobertura no Ceará. **Não construir o dashboard antes de compreender a base.**

---

## 11. Riscos e decisões pendentes

| Risco / questão | Como vamos lidar |
|---|---|
| Portal muda URL ou formato | Descoberta por metadados/API; log de origem; fallback documentado |
| ONS revisa registros antigos | Registrar coleta/hash, reprocessar de maneira idempotente |
| `ceg` não existe para conjuntos | Manter `id_ons` e não realizar join forçado com ANEEL |
| Referência ausente ou incompatível | Não calcular indicador; exibir taxa de cobertura |
| Confusão entre MWmed e MWh | Converter com duração validada e testar cálculo |
| Diferença frente à referência não equivale a curtailment apurado | Nomear indicador como exploratório; validar metodologia do ONS |
| Dados antigos/novos com colunas distintas | Validar esquema por período; versionar regras de transformação |
| Séries incompletas em certos horários | Informar cobertura; não supor geração zero onde não houver registro |
| CSVs grandes tornam o app lento | Pré-agregar, armazenar Parquet/SQLite, usar cache e consultas filtradas |
| Custo para hospedagem | Manter opção de rodar localmente; avaliar limites do serviço antes de publicar |

---

## 12. Backlog futuro — diferenciais para portfólio

- [ ] **Mapa do Nordeste** com cobertura de empreendimentos (coordenadas apenas quando confiáveis).
- [ ] **Comparação eólica vs. solar** com padronização de unidades e categorias.
- [ ] **Séries temporais**: sazonalidade por mês, dia da semana e horário.
- [ ] **Detecção de anomalias** com limites estatísticos transparentes.
- [ ] **Automação da ingestão** com agendamento e alertas de falha.
- [ ] **API própria** para consultar indicadores resumidos.
- [ ] **Versão bilíngue PT/EN** do README e do dashboard.
- [ ] **Estudo técnico** em `docs/insights.md` com os achados e recomendações para investigação operacional.

---

## 13. Registro de decisões do projeto

Manter esta seção atualizada conforme a implementação:

| Data | Decisão | Motivo |
|---|---|---|
| 2026-11-22 | Começar por eólicas no Ceará, 1º trimestre de 2025 | Reduzir escopo inicial e garantir MVP executável |
| 2026-11-22 | Usar `id_ons` como chave de identificação operacional | ONS pode publicar conjuntos sem CEG |
| 2026-11-22 | Registrar como superada a premissa inicial de calcular déficit exploratório como indicador principal | O CSV revelou a GNRa oficial; o recálculo será mantido apenas para conciliação |
| 2026-11-22 | Priorizar a GNRa publicada pelo ONS e usar o recálculo apenas para conciliação | O CSV possui `val_geracaonaorealizadaapurada`, ausente da premissa inicial do plano |
| 2026-11-22 | Usar a API CKAN `package_show` para descobrir recursos mensais | A consulta oficial retornou um recurso único por período e formato, sem exigir URLs mensais manuais |
| 2026-11-22 | Adotar Vercel + FastAPI + Neon PostgreSQL gratuito no lugar de SQLite local | Permite hospedar gratuitamente aplicação web e API real em produção com separação entre runtime leve (`requirements.txt`) e pipeline ETL (`requirements-etl.txt`) |
| 2026-11-22 | Adotar commits em português e branch `teste` antes de PR na `main` | Padronizar fluxo de versionamento e revisão |
| A definir | Convenção de fuso horário e duração do intervalo | Confirmar na exploração e documentação |

---

## 14. Entrega final esperada

**Um projeto público com código funcional + pipeline de dados + SQL + dashboard + análise técnica escrita + testes + documentação.** O valor do projeto não estará só no visual: estará em extrair dados oficiais, garantir qualidade, construir métricas defensáveis e comunicar conclusões com responsabilidade.

**Próxima ação:** concluir a Fase 3 criando os sinalizadores de elegibilidade por indicador, validação de granularidade para `duracao_horas`, preservação da GNRa oficial, escrita do Parquet (`data/processed/restricoes_eolicas_ce_2025_01.parquet`) e geração do relatório consolidado de qualidade.
