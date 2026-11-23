# Renewable Energy Intelligence

Projeto de engenharia e análise de dados para investigar restrições de geração eólica no Brasil a partir de dados abertos oficiais do ONS. O dashboard será uma aplicação web construída com HTML, CSS e JavaScript, alimentada por resultados validados do pipeline Python.

O escopo inicial é o Ceará, entre janeiro e março de 2025. O projeto está na Fase 0 (preparação do ambiente); pipeline, banco e dashboard ainda não foram implementados.

## Ambiente local

Requer Python 3.11 ou superior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Consulte [plano.md](plano.md) para o escopo, a metodologia proposta e o roadmap.

## Interface web

A fundação do frontend está em `frontend/`. Nesta fase ela informa corretamente que ainda não há dados processados; gráficos e filtros serão implementados somente depois da validação das fontes, chaves e métricas.

Para visualizar a página sem depender de extensões do editor:

```powershell
python -m http.server 8000 --directory frontend
```

Depois, acesse `http://localhost:8000`.

## Aviso

Este projeto não é um produto oficial do ONS ou da ANEEL. Nenhum resultado analítico deve ser tratado como oficial sem validação da metodologia e dos dados de origem.


