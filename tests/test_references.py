"""Validação das referências oficiais preservadas no repositório."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = PROJECT_ROOT / "docs" / "referencias" / "ons"
DICTIONARY_STEM = "DicionarioDados_RestricaoContrainedoff_UsiEolicas"


def test_ons_dictionary_pdf_has_valid_signature() -> None:
    pdf_path = REFERENCE_DIR / f"{DICTIONARY_STEM}.pdf"

    assert pdf_path.read_bytes().startswith(b"%PDF-")


def test_ons_dictionary_json_has_24_unique_fields() -> None:
    json_path = REFERENCE_DIR / f"{DICTIONARY_STEM}.json"
    dictionary = json.loads(json_path.read_text(encoding="utf-8-sig"))
    fields = dictionary["dicionario_simplificado"]
    codes = [field["codigo"] for field in fields]

    assert len(codes) == 24
    assert len(codes) == len(set(codes))
