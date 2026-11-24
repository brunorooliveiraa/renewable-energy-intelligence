# Renewable Energy Intelligence

Projeto de engenharia e análise de dados para investigar restrições de geração eólica (*constrained-off* / *curtailment*) no Brasil a partir de dados abertos oficiais do ONS.

A aplicação foi estruturada para rodar em produção gratuita na **Vercel**, com:
- **Pipeline ETL Python** (`src/extract.py`, `src/transform.py`, `src/validate.py`, `src/metrics.py`, `src/database.py`) executado localmente ou via GitHub Actions;
- **Banco de dados PostgreSQL gerenciado** (Neon integrado à Vercel Storage);
- **API Serverless em FastAPI** (`api/index.py`) leve e sem dependência de `pandas`/`pyarrow`;
- **Dashboard Web estático** (`frontend/`) em HTML5, CSS3 e JavaScript puro consumindo apenas rotas `/api/*`.

**Escopo inicial do MVP:** Ceará (`CE`), 1º trimestre de 2025.
**Status atual:** Fases 0, 1, 2, 3 e 4 concluídas (extração CKAN, transformação/validação Parquet, métricas, gráficos exploratórios básicos em `docs/imagens/fase4/` e achados documentados em `docs/achados_mvp.md`). A Fase 5 está em andamento, com esquema PostgreSQL e camada inicial de conexão implementados; a carga idempotente e as rotas analíticas FastAPI ainda estão pendentes.

## Ambiente local

Requer Python 3.11 ou superior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-etl.txt
```

- `requirements.txt` contém apenas as dependências leves efetivamente usadas pelo runtime da API serverless na Vercel (`fastapi` e `psycopg[binary]`, sem `pandas`/`pyarrow`).
- `requirements-etl.txt` inclui `-r requirements.txt` mais as dependências de engenharia de dados, análise e testes (`pandas`, `numpy`, `requests`, `pyarrow`, `pytest`, `jupyter`, `uvicorn`, `httpx`).

Copie `.env.example` para `.env` e configure `DATABASE_URL` (string *pooled* do Neon) e `DIRECT_DATABASE_URL` (string direta do Neon) quando for conectar ao PostgreSQL.

## Execução local (ETL, API e Testes)

```powershell
# Executar a suíte de testes automatizados
python -m pytest -q

# O teste E2E do frontend é incluído no pytest e requer Node.js 22+ e
# Chrome/Chromium; use CHROME_BIN caso o navegador não esteja em um caminho padrão.

# Extrair dados brutos oficiais do ONS via API CKAN
python -m src.extract --year 2025 --month 1 --source eolica

# Subir a API FastAPI localmente (Swagger em http://localhost:8000/api/docs)
uvicorn api.index:app --reload --port 8000

# Visualizar o frontend estático isoladamente
python -m http.server 8001 --directory frontend
```

Consulte [plano.md](plano.md) para o roadmap completo e [docs/arquitetura_vercel.md](docs/arquitetura_vercel.md) para os detalhes de deploy na Vercel + Neon PostgreSQL.

## Aviso

Este projeto não é um produto oficial do ONS ou da ANEEL. Nenhum resultado analítico deve ser tratado como oficial sem validação da metodologia e dos dados de origem.
