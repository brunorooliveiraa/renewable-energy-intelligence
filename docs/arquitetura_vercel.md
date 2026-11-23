# Arquitetura de Servidor Gratuito — Vercel + FastAPI + Neon PostgreSQL

Este documento registra a decisão arquitetural tomada em 2026-11-22 de reestruturar a camada de persistência e entrega do projeto para rodar em um servidor real gratuito: **Vercel (Hobby Plan)** para o frontend estático e a API serverless em **FastAPI**, integrados ao banco gerenciado **PostgreSQL (Neon)** oferecido no ecossistema Vercel Storage.

## 1. Por que separar o ETL da API serverless

O plano gratuito da Vercel impõe restrições objetivas às funções Python serverless (conforme [documentação oficial da Vercel](https://vercel.com/docs/functions/limitations)):
- **Duração máxima por requisição (Hobby Plan, com Fluid Compute):** até **300 segundos** (ainda assim, as rotas da API devem responder em poucos centenas de milissegundos para boa experiência do usuário);
- **Tamanho máximo do bundle serverless:** 250 MB;
- **Payload máximo de resposta:** 4,5 MB;
- **Conexões concorrentes:** funções efêmeras exigem *connection pooling* (PgBouncer do Neon).

O pipeline ETL do ONS baixa CSVs de ~36 MB/mês e processa 232 mil linhas por mês com `pandas` e `pyarrow`. Por isso:

1. **O ETL nunca roda dentro de uma rota HTTP da Vercel.** Ele executa localmente (ou agendado no GitHub Actions), usando `requirements-etl.txt`, e grava os dados validados no PostgreSQL (`DIRECT_DATABASE_URL` / `DATABASE_URL`).
2. **A API serverless (`api/index.py`) usa apenas `requirements.txt` leve** (atualmente apenas `fastapi`; o driver `psycopg[binary]` será adicionado somente na Fase 5, quando a camada PostgreSQL for implementada), **sem importar `pandas` nem `pyarrow`**, garantindo *cold start* rápido e bundle muito abaixo de 250 MB.
3. **O frontend (`frontend/`) nunca acessa o banco diretamente.** Consome apenas rotas JSON (`/api/*`) com contratos explícitos, paginação/agregação no SQL e unidades visíveis.

## 2. Topologia do sistema

```text
  ONS Dados Abertos (API CKAN + CSV no S3)
                     │
                     ▼  (local ou GitHub Actions — requirements-etl.txt)
  Pipeline ETL Python: src/extract.py → src/transform.py → src/validate.py → src/database.py
                     │
                     ├──► data/processed/*.parquet (auditoria local)
                     │
                     ▼  (carga idempotente em lote via psycopg)
  PostgreSQL Gerenciado (Neon / Vercel Storage — 1 GB grátis, 100 CU-hours/mês)
                     │
                     ▼  (leitura leve via Pooled DATABASE_URL, sem pandas)
  API Serverless FastAPI na Vercel (api/index.py — requirements.txt)
                     │
                     ▼  (HTTPS JSON validado)
  Frontend Estático na Vercel (frontend/index.html + assets/css + assets/js)
```

## 3. Contrato de rotas planejado para a API (`api/index.py`)

| Rota | Estado atual | Finalidade |
|---|---|---|
| `GET /api/health` | **Implementada** | Verifica saúde da função serverless e presença de `DATABASE_URL` |
| `GET /api/overview` | Planejada (Fase 5/6) | Cartões consolidados de geração verificada (MWh), cobertura e restrições |
| `GET /api/timeseries` | Planejada (Fase 5/6) | Série diária/mensal pré-agregada por UF e período |
| `GET /api/enterprises` | Planejada (Fase 5/6) | Ranking e busca por `ons_id` / nome da usina ou conjunto |
| `GET /api/reasons` | Planejada (Fase 5/6) | Distribuição por razão (`REL`, `CNF`, `ENE`, `PAR`) e origem (`LOC`, `SIS`) |
| `GET /api/quality` | Planejada (Fase 5/6) | Relatório de qualidade, cobertura, última coleta e revisões registradas |

## 4. Variáveis de ambiente e segurança

- `DATABASE_URL`: string **Pooled** (`-pooler` / PgBouncer) do Neon PostgreSQL, usada pela API serverless FastAPI na Vercel.
- `DIRECT_DATABASE_URL`: string **Direta** (unpooled) do Neon PostgreSQL, usada pelo pipeline ETL e migrações (`sql/schema.sql`).
- Nunca commitar `.env` nem senhas no repositório; usar `.env.example` como modelo e configurar as variáveis no painel da Vercel (Environment Variables).

## 5. Como rodar localmente antes do deploy

```powershell
# 1. Instalar dependências completas (API + ETL + testes)
python -m pip install -r requirements-etl.txt

# 2. Subir a API FastAPI localmente (documentação interativa em /api/docs)
uvicorn api.index:app --reload --port 8000

# 3. Verificar o endpoint de saúde
# http://localhost:8000/api/health
```
