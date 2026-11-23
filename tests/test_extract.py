"""Testes da descoberta CKAN e do download de recursos com respostas sintéticas."""

import hashlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import requests

from src.extract import (
    DEFAULT_RAW_DIR,
    AmbiguousResourceError,
    ResourceDiscoveryError,
    ResourceDownloadError,
    ResourceNotFoundError,
    ResourceRevisionConflictError,
    build_archived_revision_filepath,
    build_metadata_filepath,
    build_raw_filename,
    build_raw_filepath,
    compute_file_sha256,
    discover_resource,
    download_monthly_resource,
    download_period_range,
    download_resource_file,
    iter_year_months,
    main,
    read_collection_metadata,
    resolve_dataset_id,
    write_collection_metadata,
)

JANUARY_CSV = {
    "id": "csv-resource-id",
    "name": "Restricoes_coff_eolicas-2025-01",
    "format": "CSV",
    "url": "https://example.test/RESTRICAO_COFF_EOLICA_2025_01.csv",
    "created": "2025-01-02T15:05:23",
    "last_modified": "2026-09-11T17:48:09",
}


class FakeResponse:
    """Resposta HTTP sintética usada exclusivamente nos testes."""

    def __init__(
        self,
        payload: Any,
        *,
        request_error: requests.RequestException | None = None,
        invalid_json: bool = False,
    ) -> None:
        self.payload = payload
        self.request_error = request_error
        self.invalid_json = invalid_json

    def raise_for_status(self) -> None:
        if self.request_error is not None:
            raise self.request_error

    def json(self) -> Any:
        if self.invalid_json:
            raise ValueError("JSON sintético inválido")
        return self.payload


class FakeSession:
    """Cliente HTTP sintético que registra a consulta recebida."""

    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, *, params: dict[str, str], timeout: float) -> FakeResponse:
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return self.response


def ckan_payload(resources: list[dict[str, Any]]) -> dict[str, Any]:
    """Cria uma resposta CKAN sintética identificada para os testes."""

    return {"success": True, "result": {"resources": resources}}


def test_discovers_unique_resource_and_returns_normalized_metadata() -> None:
    parquet = {**JANUARY_CSV, "id": "parquet-id", "format": "PARQUET"}
    february = {
        **JANUARY_CSV,
        "id": "february-id",
        "name": "Restricoes_coff_eolicas-2025-02",
    }
    session = FakeSession(FakeResponse(ckan_payload([parquet, february, JANUARY_CSV])))

    resource = discover_resource(
        "restricao_coff_eolica_usi",
        2025,
        1,
        "csv",
        timeout=12,
        session=session,  # type: ignore[arg-type]
    )

    assert resource == JANUARY_CSV
    assert session.calls == [
        {
            "url": "https://dados.ons.org.br/api/3/action/package_show",
            "params": {"id": "restricao_coff_eolica_usi"},
            "timeout": 12.0,
        }
    ]


@pytest.mark.parametrize(
    ("year", "month", "file_format"),
    [(True, 1, "csv"), (2025, 0, "csv"), (2025, 13, "csv"), (2025, 1, "csv?")],
)
def test_rejects_invalid_selection_arguments(
    year: int, month: int, file_format: str
) -> None:
    session = FakeSession(FakeResponse(ckan_payload([JANUARY_CSV])))

    with pytest.raises(ValueError):
        discover_resource(
            "restricao_coff_eolica_usi",
            year,
            month,
            file_format,
            session=session,  # type: ignore[arg-type]
        )

    assert session.calls == []


def test_raises_clear_error_when_resource_is_missing() -> None:
    session = FakeSession(FakeResponse(ckan_payload([JANUARY_CSV])))

    with pytest.raises(ResourceNotFoundError, match="período=2025-02"):
        discover_resource(
            "restricao_coff_eolica_usi", 2025, 2, "csv", session=session  # type: ignore[arg-type]
        )


def test_raises_clear_error_when_resource_is_ambiguous() -> None:
    duplicate = {**JANUARY_CSV, "id": "second-csv-id"}
    session = FakeSession(FakeResponse(ckan_payload([JANUARY_CSV, duplicate])))

    with pytest.raises(AmbiguousResourceError, match="2 recursos"):
        discover_resource(
            "restricao_coff_eolica_usi", 2025, 1, "csv", session=session  # type: ignore[arg-type]
        )


def test_raises_clear_error_when_ckan_reports_failure() -> None:
    payload = {"success": False, "error": {"message": "Dataset not found"}}
    session = FakeSession(FakeResponse(payload))

    with pytest.raises(ResourceDiscoveryError, match="informou falha"):
        discover_resource(
            "dataset_inexistente", 2025, 1, "csv", session=session  # type: ignore[arg-type]
        )


def test_wraps_http_error_with_dataset_context() -> None:
    response = FakeResponse({}, request_error=requests.Timeout("tempo esgotado"))
    session = FakeSession(response)

    with pytest.raises(ResourceDiscoveryError, match="restricao_coff_eolica_usi"):
        discover_resource(
            "restricao_coff_eolica_usi", 2025, 1, "csv", session=session  # type: ignore[arg-type]
        )


def test_rejects_resource_with_invalid_url() -> None:
    invalid = {**JANUARY_CSV, "url": "arquivo-local.csv"}
    session = FakeSession(FakeResponse(ckan_payload([invalid])))

    with pytest.raises(ResourceDiscoveryError, match="URL inválida"):
        discover_resource(
            "restricao_coff_eolica_usi", 2025, 1, "csv", session=session  # type: ignore[arg-type]
        )


class FakeDownloadResponse:
    """Resposta HTTP sintética para simular streams de download nos testes."""

    def __init__(
        self,
        chunks: list[bytes],
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        stream_error: requests.RequestException | None = None,
    ) -> None:
        self.chunks = chunks
        self.status_code = status_code
        self.headers = headers or {}
        self.stream_error = stream_error
        self.closed = False

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            response = requests.Response()
            response.status_code = self.status_code
            raise requests.HTTPError(f"HTTP {self.status_code}", response=response)

    def iter_content(self, chunk_size: int = 1) -> Iterator[bytes]:
        assert chunk_size >= 1
        yield from self.chunks
        if self.stream_error is not None:
            raise self.stream_error

    def close(self) -> None:
        self.closed = True


class FakeDownloadSession:
    """Sessão HTTP sintética que retorna uma fila de respostas ou exceções."""

    def __init__(
        self, outcomes: list[FakeDownloadResponse | requests.RequestException]
    ) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []

    def get(
        self, url: str, *, timeout: float, stream: bool = False
    ) -> FakeDownloadResponse:
        self.calls.append({"url": url, "timeout": timeout, "stream": stream})
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, requests.RequestException):
            raise outcome
        return outcome


def test_downloads_file_in_chunks_and_computes_sha256(tmp_path: Path) -> None:
    content_chunks = [b"id_ons;val_geracao\n", b"CE01;12.5\n"]
    full_bytes = b"".join(content_chunks)
    expected_sha256 = hashlib.sha256(full_bytes).hexdigest().upper()
    response = FakeDownloadResponse(
        content_chunks,
        headers={"Content-Length": str(len(full_bytes))},
    )
    session = FakeDownloadSession([response])
    destination = tmp_path / "raw" / "ons_eolica_2025_01.csv"

    result = download_resource_file(
        JANUARY_CSV["url"],
        destination,
        timeout=15,
        max_attempts=3,
        chunk_size=8,
        session=session,  # type: ignore[arg-type]
    )

    assert destination.read_bytes() == full_bytes
    assert response.closed is True
    assert result == {
        "url": JANUARY_CSV["url"],
        "destination_path": destination,
        "size_bytes": len(full_bytes),
        "sha256": expected_sha256,
        "attempts": 1,
    }
    assert session.calls == [
        {"url": JANUARY_CSV["url"], "timeout": 15.0, "stream": True}
    ]


def test_retries_transient_failures_and_succeeds_without_leaving_temp_files(
    tmp_path: Path,
) -> None:
    payload = b"id_ons;val_geracao\nCE01;10.0\n"
    interrupted_stream = FakeDownloadResponse(
        [b"id_ons;"],
        stream_error=requests.ConnectionError("queda no meio do stream"),
    )
    server_busy = FakeDownloadResponse([], status_code=503)
    success = FakeDownloadResponse(
        [payload],
        headers={"Content-Length": str(len(payload))},
    )
    session = FakeDownloadSession([interrupted_stream, server_busy, success])
    destination = tmp_path / "ons_eolica_2025_01.csv"

    result = download_resource_file(
        JANUARY_CSV["url"],
        destination,
        max_attempts=3,
        session=session,  # type: ignore[arg-type]
    )

    assert result["attempts"] == 3
    assert result["size_bytes"] == len(payload)
    assert destination.read_bytes() == payload
    assert list(tmp_path.glob("*.part")) == []


def test_raises_clear_error_after_exhausting_max_attempts(tmp_path: Path) -> None:
    session = FakeDownloadSession(
        [
            requests.Timeout("timeout 1"),
            requests.Timeout("timeout 2"),
        ]
    )
    destination = tmp_path / "ons_eolica_2025_01.csv"

    with pytest.raises(ResourceDownloadError, match="após 2 tentativa\\(s\\)"):
        download_resource_file(
            JANUARY_CSV["url"],
            destination,
            max_attempts=2,
            session=session,  # type: ignore[arg-type]
        )

    assert not destination.exists()
    assert len(session.calls) == 2


def test_does_not_retry_permanent_http_404_error(tmp_path: Path) -> None:
    not_found = FakeDownloadResponse([], status_code=404)
    session = FakeDownloadSession([not_found])
    destination = tmp_path / "ons_eolica_2025_01.csv"

    with pytest.raises(ResourceDownloadError, match="Falha HTTP 404"):
        download_resource_file(
            JANUARY_CSV["url"],
            destination,
            max_attempts=3,
            session=session,  # type: ignore[arg-type]
        )

    assert len(session.calls) == 1
    assert not destination.exists()


def test_rejects_truncated_download_when_content_length_mismatches(
    tmp_path: Path,
) -> None:
    truncated = FakeDownloadResponse(
        [b"parcial"],
        headers={"Content-Length": "100"},
    )
    session = FakeDownloadSession([truncated])
    destination = tmp_path / "ons_eolica_2025_01.csv"

    with pytest.raises(ResourceDownloadError, match="Download incompleto"):
        download_resource_file(
            JANUARY_CSV["url"],
            destination,
            max_attempts=1,
            session=session,  # type: ignore[arg-type]
        )

    assert not destination.exists()
    assert list(tmp_path.glob("*.part")) == []


def test_ignores_compressed_content_length_when_content_encoding_is_present(
    tmp_path: Path,
) -> None:
    uncompressed = b"id_ons;val_geracao\nCE01;50.0\n"
    response = FakeDownloadResponse(
        [uncompressed],
        headers={"Content-Length": "12", "Content-Encoding": "gzip"},
    )
    session = FakeDownloadSession([response])
    destination = tmp_path / "ons_eolica_2025_01.csv"

    result = download_resource_file(
        JANUARY_CSV["url"],
        destination,
        max_attempts=1,
        session=session,  # type: ignore[arg-type]
    )

    assert result["size_bytes"] == len(uncompressed)
    assert destination.read_bytes() == uncompressed


def test_rejects_empty_downloaded_file(tmp_path: Path) -> None:
    empty = FakeDownloadResponse([b""])
    session = FakeDownloadSession([empty])
    destination = tmp_path / "ons_eolica_2025_01.csv"

    with pytest.raises(ResourceDownloadError, match="0 bytes"):
        download_resource_file(
            JANUARY_CSV["url"],
            destination,
            max_attempts=1,
            session=session,  # type: ignore[arg-type]
        )

    assert not destination.exists()


def test_refuses_to_overwrite_existing_file_by_default(tmp_path: Path) -> None:
    destination = tmp_path / "ons_eolica_2025_01.csv"
    destination.write_bytes(b"original")
    session = FakeDownloadSession([])

    with pytest.raises(FileExistsError, match="overwrite=False"):
        download_resource_file(
            JANUARY_CSV["url"],
            destination,
            overwrite=False,
            session=session,  # type: ignore[arg-type]
        )

    assert destination.read_bytes() == b"original"
    assert session.calls == []


@pytest.mark.parametrize(
    ("url", "timeout", "max_attempts", "chunk_size", "overwrite"),
    [
        ("ftp://example.test/file.csv", 10.0, 3, 1024, False),
        ("", 10.0, 3, 1024, False),
        (JANUARY_CSV["url"], 0, 3, 1024, False),
        (JANUARY_CSV["url"], 10.0, 0, 1024, False),
        (JANUARY_CSV["url"], 10.0, True, 1024, False),
        (JANUARY_CSV["url"], 10.0, 3, 0, False),
        (JANUARY_CSV["url"], 10.0, 3, 1024, "sim"),  # type: ignore[list-item]
    ],
)
def test_rejects_invalid_download_arguments(
    tmp_path: Path,
    url: str,
    timeout: float,
    max_attempts: int,
    chunk_size: int,
    overwrite: bool,
) -> None:
    session = FakeDownloadSession([])

    with pytest.raises((ValueError, TypeError)):
        download_resource_file(
            url,
            tmp_path / "out.csv",
            timeout=timeout,
            max_attempts=max_attempts,
            chunk_size=chunk_size,
            overwrite=overwrite,
            session=session,  # type: ignore[arg-type]
        )

    assert session.calls == []


class FakeCombinedSession:
    """Sessão HTTP sintética que atende tanto package_show quanto o download S3."""

    def __init__(
        self,
        ckan_response: FakeResponse,
        download_response: FakeDownloadResponse,
    ) -> None:
        self.ckan_response = ckan_response
        self.download_response = download_response
        self.calls: list[dict[str, Any]] = []

    def get(
        self,
        url: str,
        *,
        params: dict[str, str] | None = None,
        timeout: float,
        stream: bool = False,
    ) -> FakeResponse | FakeDownloadResponse:
        self.calls.append(
            {"url": url, "params": params, "timeout": timeout, "stream": stream}
        )
        if params is not None:
            return self.ckan_response
        return self.download_response


@pytest.mark.parametrize(
    ("raw_input", "expected"),
    [
        ("eolica", ("eolica", "restricao_coff_eolica_usi")),
        ("EOLICA", ("eolica", "restricao_coff_eolica_usi")),
        ("restricao_coff_eolica_usi", ("eolica", "restricao_coff_eolica_usi")),
        ("RESTRICAO_COFF_EOLICA_USI", ("eolica", "restricao_coff_eolica_usi")),
    ],
)
def test_resolves_supported_source_and_dataset_identifiers(
    raw_input: str, expected: tuple[str, str]
) -> None:
    assert resolve_dataset_id(raw_input) == expected


@pytest.mark.parametrize("invalid_source", ["", "   ", "solar", "hidrica", "eolica?"])
def test_rejects_unsupported_or_invalid_source(invalid_source: str) -> None:
    with pytest.raises(ValueError):
        resolve_dataset_id(invalid_source)


def test_builds_predictable_raw_filename_for_source_and_dataset() -> None:
    assert build_raw_filename("eolica", 2025, 1, "CSV") == "ons_eolica_2025_01.csv"
    assert (
        build_raw_filename("restricao_coff_eolica_usi", 2025, 12, "parquet")
        == "ons_eolica_2025_12.parquet"
    )


def test_rejects_years_with_fewer_than_four_digits_in_filename() -> None:
    with pytest.raises(ValueError, match="4 dígitos"):
        build_raw_filename("eolica", 999, 1, "csv")


def test_builds_predictable_raw_filepath_with_default_and_custom_dir(
    tmp_path: Path,
) -> None:
    default_path = build_raw_filepath("eolica", 2025, 1)
    custom_path = build_raw_filepath("eolica", 2025, 1, output_dir=tmp_path)

    assert default_path == DEFAULT_RAW_DIR / "ons_eolica_2025_01.csv"
    assert not default_path.is_absolute()
    assert custom_path == tmp_path / "ons_eolica_2025_01.csv"


def test_rejects_output_dir_when_it_points_to_existing_file(tmp_path: Path) -> None:
    existing_file = tmp_path / "arquivo.txt"
    existing_file.write_text("conteudo", encoding="utf-8")

    with pytest.raises(ValueError, match="arquivo existente"):
        build_raw_filepath("eolica", 2025, 1, output_dir=existing_file)


def test_download_monthly_resource_saves_file_with_predictable_name(
    tmp_path: Path,
) -> None:
    csv_bytes = b"id_ons;din_instante;val_geracao\nCE01;2025-01-01 00:00:00;15.0\n"
    session = FakeCombinedSession(
        ckan_response=FakeResponse(ckan_payload([JANUARY_CSV])),
        download_response=FakeDownloadResponse(
            [csv_bytes],
            headers={"Content-Length": str(len(csv_bytes))},
        ),
    )

    result = download_monthly_resource(
        "eolica",
        2025,
        1,
        "csv",
        output_dir=tmp_path,
        timeout=20,
        session=session,  # type: ignore[arg-type]
    )

    expected_path = tmp_path / "ons_eolica_2025_01.csv"
    metadata_path = tmp_path / "ons_eolica_2025_01.csv.metadata.json"
    assert result["destination_path"] == expected_path
    assert expected_path.read_bytes() == csv_bytes
    assert metadata_path.is_file()
    recorded = read_collection_metadata(metadata_path)
    assert recorded is not None
    assert recorded["sha256"] == result["sha256"]
    assert recorded["size_bytes"] == len(csv_bytes)
    assert recorded["ckan_resource_id"] == JANUARY_CSV["id"]
    assert recorded["ckan_last_modified"] == JANUARY_CSV["last_modified"]
    assert recorded["previous_sha256"] is None
    assert len(session.calls) == 2
    assert session.calls[0]["params"] == {"id": "restricao_coff_eolica_usi"}
    assert session.calls[1]["url"] == JANUARY_CSV["url"]


def test_download_monthly_resource_rejects_untracked_existing_file_without_overwrite(
    tmp_path: Path,
) -> None:
    existing_path = tmp_path / "ons_eolica_2025_01.csv"
    existing_path.write_bytes(b"dados-existentes")
    session = FakeCombinedSession(
        ckan_response=FakeResponse(ckan_payload([JANUARY_CSV])),
        download_response=FakeDownloadResponse([b"novos-dados"]),
    )

    with pytest.raises(
        ResourceRevisionConflictError, match="não possui manifesto de metadados"
    ):
        download_monthly_resource(
            "eolica",
            2025,
            1,
            output_dir=tmp_path,
            overwrite=False,
            session=session,  # type: ignore[arg-type]
        )

    assert len(session.calls) == 1
    assert existing_path.read_bytes() == b"dados-existentes"


def test_download_monthly_resource_reuses_existing_file_when_version_and_hash_match(
    tmp_path: Path,
) -> None:
    csv_bytes = b"id_ons;din_instante;val_geracao\nCE01;2025-01-01 00:00:00;15.0\n"
    first_session = FakeCombinedSession(
        ckan_response=FakeResponse(ckan_payload([JANUARY_CSV])),
        download_response=FakeDownloadResponse(
            [csv_bytes],
            headers={"Content-Length": str(len(csv_bytes))},
        ),
    )
    first_result = download_monthly_resource(
        "eolica",
        2025,
        1,
        output_dir=tmp_path,
        session=first_session,  # type: ignore[arg-type]
    )

    second_session = FakeCombinedSession(
        ckan_response=FakeResponse(ckan_payload([JANUARY_CSV])),
        download_response=FakeDownloadResponse([b"nao-deveria-ser-baixado"]),
    )
    second_result = download_monthly_resource(
        "eolica",
        2025,
        1,
        output_dir=tmp_path,
        overwrite=False,
        session=second_session,  # type: ignore[arg-type]
    )

    assert second_result["attempts"] == 0
    assert second_result["sha256"] == first_result["sha256"]
    assert len(second_session.calls) == 1
    assert (tmp_path / "ons_eolica_2025_01.csv").read_bytes() == csv_bytes


def test_download_monthly_resource_detects_remote_ckan_revision_and_blocks_overwrite(
    tmp_path: Path,
) -> None:
    original_bytes = b"id_ons;val_geracao\nCE01;10.0\n"
    first_session = FakeCombinedSession(
        ckan_response=FakeResponse(ckan_payload([JANUARY_CSV])),
        download_response=FakeDownloadResponse([original_bytes]),
    )
    download_monthly_resource(
        "eolica",
        2025,
        1,
        output_dir=tmp_path,
        session=first_session,  # type: ignore[arg-type]
    )

    revised_ckan_resource = {
        **JANUARY_CSV,
        "last_modified": "2026-10-05T09:30:00",
    }
    second_session = FakeCombinedSession(
        ckan_response=FakeResponse(ckan_payload([revised_ckan_resource])),
        download_response=FakeDownloadResponse([b"id_ons;val_geracao\nCE01;12.0\n"]),
    )

    with pytest.raises(
        ResourceRevisionConflictError, match="Detectada possível revisão no CKAN"
    ):
        download_monthly_resource(
            "eolica",
            2025,
            1,
            output_dir=tmp_path,
            overwrite=False,
            session=second_session,  # type: ignore[arg-type]
        )

    assert len(second_session.calls) == 1
    assert (tmp_path / "ons_eolica_2025_01.csv").read_bytes() == original_bytes


def test_download_monthly_resource_detects_local_file_tampering_against_manifest(
    tmp_path: Path,
) -> None:
    original_bytes = b"id_ons;val_geracao\nCE01;10.0\n"
    first_session = FakeCombinedSession(
        ckan_response=FakeResponse(ckan_payload([JANUARY_CSV])),
        download_response=FakeDownloadResponse([original_bytes]),
    )
    download_monthly_resource(
        "eolica",
        2025,
        1,
        output_dir=tmp_path,
        session=first_session,  # type: ignore[arg-type]
    )

    # Altera o arquivo em disco sem atualizar o manifesto.
    (tmp_path / "ons_eolica_2025_01.csv").write_bytes(b"adulterado")

    second_session = FakeCombinedSession(
        ckan_response=FakeResponse(ckan_payload([JANUARY_CSV])),
        download_response=FakeDownloadResponse([original_bytes]),
    )

    with pytest.raises(
        ResourceRevisionConflictError, match="modificado em relação ao manifesto"
    ):
        download_monthly_resource(
            "eolica",
            2025,
            1,
            output_dir=tmp_path,
            overwrite=False,
            session=second_session,  # type: ignore[arg-type]
        )


def test_download_monthly_resource_with_overwrite_preserves_multi_revision_history_and_archived_files(
    tmp_path: Path,
) -> None:
    v1_bytes = b"id_ons;val_geracao\nCE01;10.0\n"
    v2_bytes = b"id_ons;val_geracao\nCE01;11.5\n"
    v3_bytes = b"id_ons;val_geracao\nCE01;14.0\n"

    first_session = FakeCombinedSession(
        ckan_response=FakeResponse(ckan_payload([JANUARY_CSV])),
        download_response=FakeDownloadResponse([v1_bytes]),
    )
    v1_result = download_monthly_resource(
        "eolica",
        2025,
        1,
        output_dir=tmp_path,
        session=first_session,  # type: ignore[arg-type]
    )

    revised_ckan_v2 = {**JANUARY_CSV, "last_modified": "2026-10-01T12:00:00"}
    second_session = FakeCombinedSession(
        ckan_response=FakeResponse(ckan_payload([revised_ckan_v2])),
        download_response=FakeDownloadResponse([v2_bytes]),
    )
    v2_result = download_monthly_resource(
        "eolica",
        2025,
        1,
        output_dir=tmp_path,
        overwrite=True,
        session=second_session,  # type: ignore[arg-type]
    )

    revised_ckan_v3 = {**JANUARY_CSV, "last_modified": "2026-11-01T12:00:00"}
    third_session = FakeCombinedSession(
        ckan_response=FakeResponse(ckan_payload([revised_ckan_v3])),
        download_response=FakeDownloadResponse([v3_bytes]),
    )
    v3_result = download_monthly_resource(
        "eolica",
        2025,
        1,
        output_dir=tmp_path,
        overwrite=True,
        session=third_session,  # type: ignore[arg-type]
    )

    raw_path = tmp_path / "ons_eolica_2025_01.csv"
    metadata_path = build_metadata_filepath(raw_path)
    recorded = read_collection_metadata(metadata_path)
    assert recorded is not None
    assert recorded["sha256"] == v3_result["sha256"]
    assert recorded["previous_sha256"] == v2_result["sha256"]
    assert recorded["previous_ckan_last_modified"] == "2026-10-01T12:00:00"
    assert recorded["ckan_last_modified"] == "2026-11-01T12:00:00"
    assert len(recorded["revision_history"]) == 2
    assert recorded["revision_history"][0]["sha256"] == v1_result["sha256"]
    assert recorded["revision_history"][1]["sha256"] == v2_result["sha256"]

    archived_v1 = build_archived_revision_filepath(raw_path, v1_result["sha256"])
    archived_v2 = build_archived_revision_filepath(raw_path, v2_result["sha256"])
    assert archived_v1.read_bytes() == v1_bytes
    assert archived_v2.read_bytes() == v2_bytes
    assert raw_path.read_bytes() == v3_bytes


def test_download_monthly_resource_rolls_back_csv_if_metadata_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    v1_bytes = b"id_ons;val_geracao\nCE01;10.0\n"
    v2_bytes = b"id_ons;val_geracao\nCE01;99.0\n"
    first_session = FakeCombinedSession(
        ckan_response=FakeResponse(ckan_payload([JANUARY_CSV])),
        download_response=FakeDownloadResponse([v1_bytes]),
    )
    v1_result = download_monthly_resource(
        "eolica",
        2025,
        1,
        output_dir=tmp_path,
        session=first_session,  # type: ignore[arg-type]
    )

    def fail_metadata_write(*args: Any, **kwargs: Any) -> Path:
        raise ResourceDownloadError("falha simulada ao gravar manifesto")

    monkeypatch.setattr("src.extract.write_collection_metadata", fail_metadata_write)

    revised_ckan = {**JANUARY_CSV, "last_modified": "2026-11-01T12:00:00"}
    second_session = FakeCombinedSession(
        ckan_response=FakeResponse(ckan_payload([revised_ckan])),
        download_response=FakeDownloadResponse([v2_bytes]),
    )

    with pytest.raises(ResourceDownloadError, match="falha simulada ao gravar manifesto"):
        download_monthly_resource(
            "eolica",
            2025,
            1,
            output_dir=tmp_path,
            overwrite=True,
            session=second_session,  # type: ignore[arg-type]
        )

    raw_path = tmp_path / "ons_eolica_2025_01.csv"
    metadata_path = build_metadata_filepath(raw_path)
    recorded = read_collection_metadata(metadata_path)
    assert raw_path.read_bytes() == v1_bytes
    assert recorded is not None
    assert recorded["sha256"] == v1_result["sha256"]


def test_download_monthly_resource_removes_new_csv_if_initial_metadata_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_metadata_write(*args: Any, **kwargs: Any) -> Path:
        raise ResourceDownloadError("disco cheio ao gravar manifesto inicial")

    monkeypatch.setattr("src.extract.write_collection_metadata", fail_metadata_write)

    session = FakeCombinedSession(
        ckan_response=FakeResponse(ckan_payload([JANUARY_CSV])),
        download_response=FakeDownloadResponse([b"id_ons;val_geracao\nCE01;10.0\n"]),
    )

    with pytest.raises(
        ResourceDownloadError, match="disco cheio ao gravar manifesto inicial"
    ):
        download_monthly_resource(
            "eolica",
            2025,
            1,
            output_dir=tmp_path,
            session=session,  # type: ignore[arg-type]
        )

    assert not (tmp_path / "ons_eolica_2025_01.csv").exists()
    assert not (tmp_path / "ons_eolica_2025_01.csv.metadata.json").exists()


def test_compute_file_sha256_and_corrupted_metadata_handling(tmp_path: Path) -> None:
    sample = tmp_path / "sample.csv"
    sample.write_bytes(b"abc")
    size, sha256 = compute_file_sha256(sample, chunk_size=2)
    assert size == 3
    assert sha256 == hashlib.sha256(b"abc").hexdigest().upper()

    bad_metadata = tmp_path / "sample.csv.metadata.json"
    bad_metadata.write_text("{json-invalido", encoding="utf-8")
    with pytest.raises(ResourceDownloadError, match="Falha ao ler metadados"):
        read_collection_metadata(bad_metadata)

    with pytest.raises(ResourceDownloadError, match="Campo obrigatório ausente"):
        write_collection_metadata(bad_metadata, {"source": "eolica"})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("override_field", "invalid_value", "expected_match"),
    [
        ("month", 13, "month deve ser um número inteiro entre 1 e 12"),
        ("year", 99, "year deve ter 4 dígitos"),
        ("sha256", "ABC123", "sha256 deve ser um hash SHA-256 com 64 caracteres"),
        (
            "previous_sha256",
            "INVALIDO",
            "previous_sha256 deve ser um hash SHA-256 com 64 caracteres",
        ),
        (
            "collected_at_utc",
            "2026-11-22T20:00:00",
            "collected_at_utc deve possuir fuso horário UTC explícito",
        ),
        (
            "collected_at_utc",
            "2026-11-22T20:00:00-03:00",
            "collected_at_utc deve possuir fuso horário UTC explícito",
        ),
        (
            "source_url",
            "ftp://example.test/file.csv",
            "url deve usar esquema http ou https válido",
        ),
        (
            "dataset",
            "outro_dataset",
            "não corresponde à fonte",
        ),
    ],
)
def test_strict_validation_of_collection_metadata_fields(
    tmp_path: Path,
    override_field: str,
    invalid_value: Any,
    expected_match: str,
) -> None:
    valid_base = {
        "source": "eolica",
        "dataset": "restricao_coff_eolica_usi",
        "year": 2025,
        "month": 1,
        "file_format": "CSV",
        "file_name": "ons_eolica_2025_01.csv",
        "file_path": "data/raw/ons_eolica_2025_01.csv",
        "size_bytes": 120,
        "sha256": "A" * 64,
        "collected_at_utc": "2026-11-22T23:00:00+00:00",
        "ckan_resource_id": "csv-resource-id",
        "ckan_resource_name": "Restricoes_coff_eolicas-2025-01",
        "source_url": "https://example.test/RESTRICAO_COFF_EOLICA_2025_01.csv",
        "ckan_created": "2025-01-02T15:05:23",
        "ckan_last_modified": "2026-09-11T17:48:09",
        "previous_sha256": None,
        "previous_ckan_last_modified": None,
        "revision_history": [],
    }
    invalid_payload = {**valid_base, override_field: invalid_value}
    metadata_path = tmp_path / "ons_eolica_2025_01.csv.metadata.json"

    with pytest.raises(ResourceDownloadError, match=expected_match):
        write_collection_metadata(metadata_path, invalid_payload)  # type: ignore[arg-type]


class FakeRangeSession:
    """Sessão HTTP sintética para testar múltiplos meses com 1 consulta CKAN."""

    def __init__(
        self,
        ckan_response: FakeResponse,
        downloads_by_url: dict[str, FakeDownloadResponse],
    ) -> None:
        self.ckan_response = ckan_response
        self.downloads_by_url = downloads_by_url
        self.ckan_calls = 0
        self.download_calls: list[str] = []

    def get(
        self,
        url: str,
        *,
        params: dict[str, str] | None = None,
        timeout: float,
        stream: bool = False,
    ) -> FakeResponse | FakeDownloadResponse:
        assert timeout > 0
        if params is not None:
            self.ckan_calls += 1
            return self.ckan_response
        self.download_calls.append(url)
        return self.downloads_by_url[url]


def test_iter_year_months_handles_single_month_range_and_year_rollover() -> None:
    assert iter_year_months(2025, 1, 2025, 1) == [(2025, 1)]
    assert iter_year_months(2025, 1, 2025, 3) == [(2025, 1), (2025, 2), (2025, 3)]
    assert iter_year_months(2025, 11, 2026, 2) == [
        (2025, 11),
        (2025, 12),
        (2026, 1),
        (2026, 2),
    ]


def test_iter_year_months_rejects_inverted_range() -> None:
    with pytest.raises(ValueError, match="Faixa de períodos inválida"):
        iter_year_months(2025, 4, 2025, 2)


def test_download_period_range_fetches_catalog_once_and_downloads_multiple_months(
    tmp_path: Path,
) -> None:
    feb_csv = {
        **JANUARY_CSV,
        "id": "feb-id",
        "name": "Restricoes_coff_eolicas-2025-02",
        "url": "https://example.test/RESTRICAO_COFF_EOLICA_2025_02.csv",
    }
    mar_csv = {
        **JANUARY_CSV,
        "id": "mar-id",
        "name": "Restricoes_coff_eolicas-2025-03",
        "url": "https://example.test/RESTRICAO_COFF_EOLICA_2025_03.csv",
    }
    session = FakeRangeSession(
        ckan_response=FakeResponse(ckan_payload([JANUARY_CSV, feb_csv, mar_csv])),
        downloads_by_url={
            JANUARY_CSV["url"]: FakeDownloadResponse([b"jan-data"]),
            feb_csv["url"]: FakeDownloadResponse([b"feb-data"]),
            mar_csv["url"]: FakeDownloadResponse([b"mar-data"]),
        },
    )

    reports = download_period_range(
        "eolica",
        2025,
        1,
        end_month=3,
        output_dir=tmp_path,
        session=session,  # type: ignore[arg-type]
    )

    assert session.ckan_calls == 1
    assert len(session.download_calls) == 3
    assert [r["period"] for r in reports] == ["2025-01", "2025-02", "2025-03"]
    assert all(r["status"] == "downloaded" for r in reports)
    assert (tmp_path / "ons_eolica_2025_01.csv").read_bytes() == b"jan-data"
    assert (tmp_path / "ons_eolica_2025_02.csv").read_bytes() == b"feb-data"
    assert (tmp_path / "ons_eolica_2025_03.csv").read_bytes() == b"mar-data"


def test_download_period_range_raises_explicitly_on_missing_month_without_partial_writes(
    tmp_path: Path,
) -> None:
    session = FakeRangeSession(
        ckan_response=FakeResponse(ckan_payload([JANUARY_CSV])),
        downloads_by_url={JANUARY_CSV["url"]: FakeDownloadResponse([b"jan-data"])},
    )

    with pytest.raises(ResourceNotFoundError, match="período=2025-02"):
        download_period_range(
            "eolica",
            2025,
            1,
            end_month=2,
            output_dir=tmp_path,
            allow_missing=False,
            session=session,  # type: ignore[arg-type]
        )

    assert session.ckan_calls == 1
    assert session.download_calls == []
    assert list(tmp_path.iterdir()) == []


def test_download_period_range_reports_missing_month_explicitly_when_allowed(
    tmp_path: Path,
) -> None:
    mar_csv = {
        **JANUARY_CSV,
        "id": "mar-id",
        "name": "Restricoes_coff_eolicas-2025-03",
        "url": "https://example.test/RESTRICAO_COFF_EOLICA_2025_03.csv",
    }
    session = FakeRangeSession(
        ckan_response=FakeResponse(ckan_payload([JANUARY_CSV, mar_csv])),
        downloads_by_url={
            JANUARY_CSV["url"]: FakeDownloadResponse([b"jan-data"]),
            mar_csv["url"]: FakeDownloadResponse([b"mar-data"]),
        },
    )

    reports = download_period_range(
        "eolica",
        2025,
        1,
        end_month=3,
        output_dir=tmp_path,
        allow_missing=True,
        session=session,  # type: ignore[arg-type]
    )

    assert [(r["period"], r["status"]) for r in reports] == [
        ("2025-01", "downloaded"),
        ("2025-02", "missing"),
        ("2025-03", "downloaded"),
    ]
    assert reports[1]["destination_path"] is None
    assert reports[1]["sha256"] is None
    assert "2025-02" in reports[1]["message"]


def test_download_period_range_does_not_silence_revision_conflict_when_allow_missing_is_true(
    tmp_path: Path,
) -> None:
    (tmp_path / "ons_eolica_2025_01.csv").write_bytes(b"arquivo-sem-manifesto")
    session = FakeRangeSession(
        ckan_response=FakeResponse(ckan_payload([JANUARY_CSV])),
        downloads_by_url={JANUARY_CSV["url"]: FakeDownloadResponse([b"jan-data"])},
    )

    with pytest.raises(ResourceRevisionConflictError):
        download_period_range(
            "eolica",
            2025,
            1,
            output_dir=tmp_path,
            allow_missing=True,
            session=session,  # type: ignore[arg-type]
        )


def test_download_period_range_rejects_end_year_without_end_month(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="Informe end_month"):
        download_period_range(
            "eolica",
            2025,
            1,
            end_year=2025,
            end_month=None,
            output_dir=tmp_path,
        )


def test_cli_main_downloads_single_month_and_prints_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = FakeRangeSession(
        ckan_response=FakeResponse(ckan_payload([JANUARY_CSV])),
        downloads_by_url={JANUARY_CSV["url"]: FakeDownloadResponse([b"cli-csv-data"])},
    )

    exit_code = main(
        [
            "--year",
            "2025",
            "--month",
            "1",
            "--source",
            "eolica",
            "--output-dir",
            str(tmp_path),
        ],
        session=session,  # type: ignore[arg-type]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[downloaded] 2025-01:" in captured.out
    assert "ons_eolica_2025_01.csv" in captured.out
    assert captured.err == ""


def test_cli_main_returns_nonzero_and_prints_error_for_missing_month(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = FakeRangeSession(
        ckan_response=FakeResponse(ckan_payload([JANUARY_CSV])),
        downloads_by_url={},
    )

    exit_code = main(
        [
            "--year",
            "2025",
            "--month",
            "2",
            "--source",
            "eolica",
            "--output-dir",
            str(tmp_path),
        ],
        session=session,  # type: ignore[arg-type]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Erro na extração:" in captured.err
    assert "período=2025-02" in captured.err
