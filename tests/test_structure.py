"""Verificações mínimas da estrutura criada na Fase 0."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_required_project_directories_exist() -> None:
    required_directories = (
        "src",
        "data/raw",
        "data/processed",
        "database",
        "notebooks",
        "sql",
        "tests",
        "docs/imagens",
        "frontend/assets/css",
        "frontend/assets/js",
    )

    missing = [path for path in required_directories if not (PROJECT_ROOT / path).is_dir()]

    assert not missing, f"Diretórios obrigatórios ausentes: {missing}"


def test_frontend_entrypoint_and_assets_exist() -> None:
    required_files = (
        "frontend/index.html",
        "frontend/assets/css/styles.css",
        "frontend/assets/js/app.js",
    )

    missing = [path for path in required_files if not (PROJECT_ROOT / path).is_file()]

    assert not missing, f"Arquivos obrigatórios do frontend ausentes: {missing}"
