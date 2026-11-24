"""Executa os fluxos E2E do dashboard em um navegador Chromium real."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_all_dashboard_buttons_and_critical_frontend_flows() -> None:
    node = shutil.which("node")
    assert node is not None, "Node.js é obrigatório para executar o E2E do frontend."

    result = subprocess.run(
        [node, "--test", "tests/frontend_e2e.test.mjs"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )

    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    assert result.returncode == 0, f"E2E do frontend falhou:\n{output}"
