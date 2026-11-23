"""Descoberta e download seguro de recursos oficiais no catálogo CKAN do ONS."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, TypedDict
from urllib.parse import urlparse

import requests

CKAN_ACTION_URL = "https://dados.ons.org.br/api/3/action"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_CHUNK_SIZE_BYTES = 65_536
DEFAULT_RAW_DIR = Path("data") / "raw"
SOURCE_DATASETS: Mapping[str, str] = {
    "eolica": "restricao_coff_eolica_usi",
}
_DATASET_TO_SOURCE: Mapping[str, str] = {
    dataset_id: source_name for source_name, dataset_id in SOURCE_DATASETS.items()
}
_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})
_DATASET_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_FORMAT_PATTERN = re.compile(r"^[A-Za-z0-9]+$")
_RESOURCE_PERIOD_PATTERN = re.compile(r"-(?P<year>\d{4})-(?P<month>\d{2})$")
_SHA256_PATTERN = re.compile(r"^[0-9A-Fa-f]{64}$")


class ResourceMetadata(TypedDict):
    """Metadados necessários para identificar uma versão de recurso CKAN."""

    id: str
    name: str
    format: str
    url: str
    created: str | None
    last_modified: str | None


class DownloadResult(TypedDict):
    """Resultado verificado de um download de arquivo bruto."""

    url: str
    destination_path: Path
    size_bytes: int
    sha256: str
    attempts: int


class RevisionHistoryEntry(TypedDict):
    """Entrada histórica que preserva metadados e arquivo arquivado de uma revisão substituída."""

    sha256: str
    size_bytes: int
    collected_at_utc: str | None
    ckan_resource_id: str | None
    ckan_last_modified: str | None
    archived_file_path: str


class CollectionMetadata(TypedDict):
    """Registro auditável da coleta, versão CKAN, hash SHA-256 e histórico de revisões."""

    source: str
    dataset: str
    year: int
    month: int
    file_format: str
    file_name: str
    file_path: str
    size_bytes: int
    sha256: str
    collected_at_utc: str
    ckan_resource_id: str
    ckan_resource_name: str
    source_url: str
    ckan_created: str | None
    ckan_last_modified: str | None
    previous_sha256: str | None
    previous_ckan_last_modified: str | None
    revision_history: list[RevisionHistoryEntry]


class MonthlyExtractionReport(TypedDict):
    """Resultado explícito da extração de um mês (baixado, inalterado ou recurso ausente no formato)."""

    year: int
    month: int
    period: str
    status: Literal["downloaded", "unchanged", "missing"]
    destination_path: Path | None
    size_bytes: int | None
    sha256: str | None
    attempts: int
    message: str


class ResourceDiscoveryError(RuntimeError):
    """Erro ao consultar ou interpretar o catálogo CKAN."""


class ResourceNotFoundError(ResourceDiscoveryError):
    """Nenhum recurso corresponde ao período e formato solicitados."""


class AmbiguousResourceError(ResourceDiscoveryError):
    """Mais de um recurso corresponde ao período e formato solicitados."""


class ResourceDownloadError(RuntimeError):
    """Erro ao baixar ou validar a integridade de um arquivo remoto."""


class ResourceRevisionConflictError(ResourceDownloadError):
    """O arquivo local já existe e pode divergir da revisão publicada no CKAN."""


def discover_resource(
    dataset: str,
    year: int,
    month: int,
    file_format: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    session: requests.Session | None = None,
) -> ResourceMetadata:
    """Descobre um único recurso mensal no catálogo CKAN do ONS.

    A função consulta apenas metadados. Nenhum arquivo de dados é baixado ou
    alterado.

    Args:
        dataset: Identificador exato do conjunto no CKAN.
        year: Ano do recurso, entre 1 e 9999.
        month: Mês do recurso, entre 1 e 12.
        file_format: Formato publicado, por exemplo ``csv`` ou ``parquet``.
        timeout: Limite em segundos para a consulta HTTP.
        session: Sessão opcional, usada para reutilização de conexão e testes.

    Returns:
        Metadados do único recurso compatível com período e formato.

    Raises:
        ValueError: Quando um argumento é inválido.
        ResourceNotFoundError: Quando não há recurso compatível.
        AmbiguousResourceError: Quando há mais de uma correspondência.
        ResourceDiscoveryError: Quando a API falha ou retorna dados inválidos.
    """

    # Valida e normaliza todos os parâmetros antes de iniciar qualquer chamada HTTP.
    normalized_dataset = _validate_dataset(dataset)
    normalized_year = _validate_year(year)
    normalized_month = _validate_month(month)
    normalized_format = _validate_format(file_format)
    normalized_timeout = _validate_timeout(timeout)

    resources = _fetch_ckan_resources(
        normalized_dataset,
        timeout=normalized_timeout,
        session=session,
    )
    return _select_unique_resource(
        resources,
        dataset=normalized_dataset,
        year=normalized_year,
        month=normalized_month,
        file_format=normalized_format,
    )


def download_resource_file(
    url: str,
    destination: Path | str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    chunk_size: int = DEFAULT_CHUNK_SIZE_BYTES,
    overwrite: bool = False,
    session: requests.Session | None = None,
) -> DownloadResult:
    """Baixa um arquivo remoto via HTTP/HTTPS com timeout, tentativas e validação.

    O download é gravado inicialmente em um arquivo temporário exclusivo no
    mesmo diretório do destino e só é promovido ao caminho final após a
    verificação completa do fluxo de bytes e do cabeçalho ``Content-Length``
    (quando não há ``Content-Encoding``). Assim, falhas de rede nunca deixam
    arquivos parciais ou corrompidos no destino.

    Args:
        url: Endereço HTTP ou HTTPS completo do arquivo a ser baixado.
        destination: Caminho local onde o arquivo final será salvo.
        timeout: Limite em segundos para a requisição HTTP.
        max_attempts: Número máximo de tentativas (mínimo 1).
        chunk_size: Tamanho em bytes de cada bloco lido do stream.
        overwrite: Se ``True``, permite substituir um arquivo existente.
        session: Sessão opcional para reutilização de conexões e testes.

    Returns:
        Metadados verificados do download (caminho, tamanho em bytes,
        hash SHA-256 em maiúsculas e quantidade de tentativas utilizadas).

    Raises:
        ValueError: Quando qualquer argumento de entrada é inválido.
        FileExistsError: Quando ``destination`` já existe e ``overwrite=False``.
        ResourceDownloadError: Quando o download falha após as tentativas
            permitidas ou quando o conteúdo recebido é vazio/incompleto.
    """

    # Valida todos os parâmetros antes de criar diretórios ou abrir conexões HTTP.
    normalized_url = _validate_download_url(url)
    normalized_timeout = _validate_timeout(timeout)
    normalized_max_attempts = _validate_max_attempts(max_attempts)
    normalized_chunk_size = _validate_chunk_size(chunk_size)
    normalized_overwrite = _validate_overwrite(overwrite)
    normalized_destination = _validate_destination(
        destination, overwrite=normalized_overwrite
    )

    # Garante que o diretório pai exista antes de iniciar as tentativas.
    normalized_destination.parent.mkdir(parents=True, exist_ok=True)

    owns_session = session is None
    client = session if session is not None else requests.Session()
    last_error_message = "motivo desconhecido"

    try:
        for attempt in range(1, normalized_max_attempts + 1):
            response: requests.Response | None = None
            try:
                # Inicia a requisição em modo streaming para não carregar arquivos grandes inteiros em RAM.
                response = client.get(
                    normalized_url,
                    timeout=normalized_timeout,
                    stream=True,
                )
                status_code = getattr(response, "status_code", None)
                if isinstance(status_code, int) and status_code >= 400:
                    if (
                        status_code in _RETRYABLE_STATUS_CODES
                        and attempt < normalized_max_attempts
                    ):
                        last_error_message = f"HTTP {status_code}"
                        continue
                    raise ResourceDownloadError(
                        f"Falha HTTP {status_code} ao baixar {normalized_url!r} "
                        f"na tentativa {attempt} de {normalized_max_attempts}."
                    )

                response.raise_for_status()

                # Lê o stream completo para um arquivo temporário e valida integridade/tamanho.
                size_bytes, sha256_hex = _stream_response_to_destination(
                    response=response,
                    destination=normalized_destination,
                    chunk_size=normalized_chunk_size,
                    overwrite=normalized_overwrite,
                )

                return {
                    "url": normalized_url,
                    "destination_path": normalized_destination,
                    "size_bytes": size_bytes,
                    "sha256": sha256_hex,
                    "attempts": attempt,
                }
            except requests.HTTPError as error:
                status_code = getattr(
                    getattr(error, "response", None), "status_code", None
                )
                if (
                    isinstance(status_code, int)
                    and status_code not in _RETRYABLE_STATUS_CODES
                ):
                    raise ResourceDownloadError(
                        f"Falha HTTP permanente ({status_code}) ao baixar "
                        f"{normalized_url!r} na tentativa {attempt} de "
                        f"{normalized_max_attempts}: {error}"
                    ) from error
                last_error_message = str(error) or error.__class__.__name__
                if attempt == normalized_max_attempts:
                    raise ResourceDownloadError(
                        f"Falha ao baixar {normalized_url!r} após "
                        f"{normalized_max_attempts} tentativa(s): {last_error_message}"
                    ) from error
            except (requests.RequestException, ResourceDownloadError) as error:
                # Se for um erro HTTP permanente já classificado acima, propaga imediatamente.
                if isinstance(error, ResourceDownloadError) and "Falha HTTP" in str(
                    error
                ):
                    raise
                last_error_message = str(error) or error.__class__.__name__
                if attempt == normalized_max_attempts:
                    raise ResourceDownloadError(
                        f"Falha ao baixar {normalized_url!r} após "
                        f"{normalized_max_attempts} tentativa(s): {last_error_message}"
                    ) from error
            finally:
                # Fecha a resposta da tentativa atual para liberar o socket HTTP.
                if response is not None and hasattr(response, "close"):
                    response.close()
    finally:
        if owns_session:
            client.close()

    raise ResourceDownloadError(
        f"Falha ao baixar {normalized_url!r} após "
        f"{normalized_max_attempts} tentativa(s): {last_error_message}"
    )


def resolve_dataset_id(source_or_dataset: str) -> tuple[str, str]:
    """Resolve um identificador curto de fonte ou dataset CKAN para ``(source, dataset_id)``.

    Aceita tanto o identificador curto do pipeline (ex.: ``"eolica"``) quanto o
    identificador exato do conjunto no catálogo CKAN do ONS
    (ex.: ``"restricao_coff_eolica_usi"``), garantindo que o nome local do
    arquivo use sempre o prefixo previsível da fonte.

    Args:
        source_or_dataset: Nome curto da fonte (``"eolica"``) ou ID do dataset CKAN.

    Returns:
        Tupla ``(source_slug, dataset_id)``, por exemplo
        ``("eolica", "restricao_coff_eolica_usi")``.

    Raises:
        ValueError: Quando a fonte/dataset não é uma string válida ou não está
            mapeada entre as fontes oficiais homologadas no projeto.
    """

    if not isinstance(source_or_dataset, str) or not source_or_dataset.strip():
        raise ValueError("source_or_dataset deve ser uma string não vazia.")

    normalized_key = _validate_dataset(source_or_dataset.strip()).lower()
    if normalized_key in SOURCE_DATASETS:
        return normalized_key, SOURCE_DATASETS[normalized_key]
    if normalized_key in _DATASET_TO_SOURCE:
        return _DATASET_TO_SOURCE[normalized_key], normalized_key

    supported = sorted(set(SOURCE_DATASETS.keys()) | set(_DATASET_TO_SOURCE.keys()))
    raise ValueError(
        f"Fonte ou dataset não suportado: {source_or_dataset!r}. "
        f"Valores válidos: {supported}."
    )


def build_raw_filename(
    source: str,
    year: int,
    month: int,
    file_format: str = "csv",
) -> str:
    """Gera o nome de arquivo local previsível no padrão ``ons_<source>_YYYY_MM.<ext>``.

    Para o escopo eólico em CSV, produz nomes como ``ons_eolica_2025_01.csv``.

    Args:
        source: Identificador da fonte (``"eolica"``) ou dataset CKAN homologado.
        year: Ano de referência (entre 1000 e 9999 para compor ``YYYY`` com 4 dígitos).
        month: Mês de referência (1 a 12).
        file_format: Formato/extensão do arquivo (padrão ``"csv"``).

    Returns:
        Nome de arquivo padronizado em letras minúsculas.

    Raises:
        ValueError: Quando qualquer parâmetro é inválido.
    """

    source_slug, _ = resolve_dataset_id(source)
    normalized_year = _validate_year(year)
    if normalized_year < 1000:
        raise ValueError("year deve ter 4 dígitos (entre 1000 e 9999) para o nome do arquivo.")
    normalized_month = _validate_month(month)
    extension = _validate_format(file_format).lower()

    return f"ons_{source_slug}_{normalized_year:04d}_{normalized_month:02d}.{extension}"


def build_raw_filepath(
    source: str,
    year: int,
    month: int,
    file_format: str = "csv",
    *,
    output_dir: Path | str = DEFAULT_RAW_DIR,
) -> Path:
    """Constrói o caminho local completo para salvar um arquivo bruto do ONS.

    Por padrão utiliza o diretório relativo ``data/raw``, produzindo
    ``data/raw/ons_eolica_YYYY_MM.csv``.

    Args:
        source: Identificador da fonte (``"eolica"``) ou dataset CKAN homologado.
        year: Ano de referência com 4 dígitos.
        month: Mês de referência (1 a 12).
        file_format: Formato/extensão do arquivo (padrão ``"csv"``).
        output_dir: Diretório de saída (relativo à raiz ou customizado para testes).

    Returns:
        Objeto ``Path`` combinando ``output_dir`` e o nome previsível do arquivo.

    Raises:
        ValueError: Quando ``output_dir`` ou qualquer parâmetro do nome é inválido.
    """

    normalized_dir = _validate_output_dir(output_dir)
    filename = build_raw_filename(source, year, month, file_format)
    return normalized_dir / filename


def build_metadata_filepath(raw_filepath: Path | str) -> Path:
    """Constrói o caminho do arquivo JSON de metadados/versão associado a um arquivo bruto.

    Para ``data/raw/ons_eolica_2025_01.csv``, retorna
    ``data/raw/ons_eolica_2025_01.csv.metadata.json``.

    Args:
        raw_filepath: Caminho do arquivo de dados bruto.

    Returns:
        Objeto ``Path`` para o manifesto de metadados correspondente.

    Raises:
        ValueError: Quando ``raw_filepath`` é vazio ou inválido.
    """

    if isinstance(raw_filepath, str):
        if not raw_filepath.strip():
            raise ValueError("raw_filepath não pode ser uma string vazia.")
        normalized_path = Path(raw_filepath.strip())
    elif isinstance(raw_filepath, Path):
        normalized_path = raw_filepath
    else:
        raise TypeError("raw_filepath deve ser um objeto Path ou uma string não vazia.")

    if not normalized_path.name:
        raise ValueError("raw_filepath deve incluir um nome de arquivo válido.")

    return normalized_path.with_name(f"{normalized_path.name}.metadata.json")


def build_archived_revision_filepath(
    raw_filepath: Path | str,
    sha256: str,
) -> Path:
    """Constrói o caminho de arquivo preservado para uma revisão anterior do ONS.

    Para ``data/raw/ons_eolica_2025_01.csv`` e hash ``2DBE2C423212...``, retorna
    ``data/raw/ons_eolica_2025_01.rev_2DBE2C423212.csv``, mantendo a cópia bruta
    da versão anterior intacta quando uma nova revisão é baixada com
    ``overwrite=True``.

    Args:
        raw_filepath: Caminho do arquivo bruto principal.
        sha256: Hash SHA-256 completo (64 caracteres hexadecimais) da revisão anterior.

    Returns:
        Caminho ``Path`` para o arquivo arquivado da revisão.

    Raises:
        ValueError: Quando ``raw_filepath`` ou ``sha256`` é inválido.
    """

    if isinstance(raw_filepath, str):
        if not raw_filepath.strip():
            raise ValueError("raw_filepath não pode ser uma string vazia.")
        normalized_path = Path(raw_filepath.strip())
    elif isinstance(raw_filepath, Path):
        normalized_path = raw_filepath
    else:
        raise TypeError("raw_filepath deve ser um objeto Path ou uma string não vazia.")

    if not normalized_path.name or not normalized_path.stem:
        raise ValueError("raw_filepath deve incluir um nome de arquivo válido.")

    normalized_sha = _validate_sha256_hex(sha256, field_name="sha256")
    short_hash = normalized_sha[:12]
    suffix = normalized_path.suffix
    return normalized_path.with_name(
        f"{normalized_path.stem}.rev_{short_hash}{suffix}"
    )


def compute_file_sha256(
    file_path: Path | str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE_BYTES,
) -> tuple[int, str]:
    """Calcula o tamanho em bytes e o hash SHA-256 (em maiúsculas) de um arquivo local.

    A leitura é feita em blocos (streaming) para não carregar arquivos grandes
    inteiros na memória RAM.

    Args:
        file_path: Caminho do arquivo local existente.
        chunk_size: Tamanho em bytes de cada bloco de leitura.

    Returns:
        Tupla ``(size_bytes, sha256_uppercase)``.

    Raises:
        ValueError: Quando ``file_path`` ou ``chunk_size`` é inválido, ou quando
            o caminho aponta para um diretório.
        FileNotFoundError: Quando o arquivo não existe.
    """

    normalized_chunk_size = _validate_chunk_size(chunk_size)
    if isinstance(file_path, str):
        if not file_path.strip():
            raise ValueError("file_path não pode ser uma string vazia.")
        path = Path(file_path.strip())
    elif isinstance(file_path, Path):
        path = file_path
    else:
        raise TypeError("file_path deve ser um objeto Path ou uma string não vazia.")

    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado para cálculo de hash: {path}.")
    if path.is_dir():
        raise ValueError(f"file_path aponta para um diretório, não um arquivo: {path}.")

    digest = hashlib.sha256()
    size_bytes = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(normalized_chunk_size)
            if not chunk:
                break
            digest.update(chunk)
            size_bytes += len(chunk)

    return size_bytes, digest.hexdigest().upper()


def read_collection_metadata(metadata_path: Path | str) -> CollectionMetadata | None:
    """Lê e valida um arquivo JSON de metadados de coleta, caso exista.

    Args:
        metadata_path: Caminho do arquivo ``.metadata.json``.

    Returns:
        Dicionário ``CollectionMetadata`` validado ou ``None`` se o arquivo não existir.

    Raises:
        ValueError: Quando o caminho é inválido.
        ResourceDownloadError: Quando o arquivo existe, mas contém JSON inválido
            ou campos obrigatórios ausentes/corrompidos.
    """

    if isinstance(metadata_path, str):
        if not metadata_path.strip():
            raise ValueError("metadata_path não pode ser uma string vazia.")
        path = Path(metadata_path.strip())
    elif isinstance(metadata_path, Path):
        path = metadata_path
    else:
        raise TypeError("metadata_path deve ser um objeto Path ou uma string não vazia.")

    if not path.exists():
        return None
    if path.is_dir():
        raise ValueError(f"metadata_path aponta para um diretório: {path}.")

    try:
        raw_payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ResourceDownloadError(
            f"Falha ao ler metadados de coleta em {path}: {error}"
        ) from error

    return _validate_collection_metadata_payload(raw_payload, path)


def write_collection_metadata(
    metadata_path: Path | str,
    metadata: CollectionMetadata,
) -> Path:
    """Grava de forma atômica o arquivo JSON com os metadados de versão e hash da coleta.

    Args:
        metadata_path: Caminho do arquivo ``.metadata.json`` a ser gravado.
        metadata: Estrutura ``CollectionMetadata`` validada.

    Returns:
        Caminho ``Path`` onde o arquivo foi gravado.

    Raises:
        ValueError: Quando ``metadata_path`` é inválido.
        ResourceDownloadError: Quando ``metadata`` não cumpre o contrato esperado.
    """

    if isinstance(metadata_path, str):
        if not metadata_path.strip():
            raise ValueError("metadata_path não pode ser uma string vazia.")
        path = Path(metadata_path.strip())
    elif isinstance(metadata_path, Path):
        path = metadata_path
    else:
        raise TypeError("metadata_path deve ser um objeto Path ou uma string não vazia.")

    if path.exists() and path.is_dir():
        raise ValueError(f"metadata_path aponta para um diretório existente: {path}.")

    validated = _validate_collection_metadata_payload(metadata, path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".part",
        dir=path.parent,
    )
    temp_path = Path(temp_name)

    try:
        serialized = json.dumps(validated, indent=2, ensure_ascii=False) + "\n"
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
        temp_path.replace(path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise

    return path


def download_monthly_resource(
    source: str,
    year: int,
    month: int,
    file_format: str = "csv",
    *,
    output_dir: Path | str = DEFAULT_RAW_DIR,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    chunk_size: int = DEFAULT_CHUNK_SIZE_BYTES,
    overwrite: bool = False,
    session: requests.Session | None = None,
) -> DownloadResult:
    """Descobre um recurso mensal no CKAN, verifica revisões/hashes e salva com nome previsível.

    Protege os arquivos brutos contra sobrescrita silenciosa:
    - Se o arquivo local não existir, faz o download e grava o manifesto
      ``<arquivo>.metadata.json`` com versão CKAN, tamanho e hash SHA-256.
    - Se o arquivo local já existir e ``overwrite=False``:
      - Verifica o hash SHA-256 real do arquivo em disco e compara com o
        manifesto local e com os metadados atuais do CKAN (``id``, ``url`` e
        ``last_modified`` não nulo).
      - Se a versão/hash local coincidir exatamente com a versão publicada no
        CKAN, reutiliza o arquivo verificado sem sobrescrevê-lo (`attempts=0`).
      - Se não houver manifesto local, se o arquivo local tiver sido alterado
        ou se o CKAN indicar uma revisão (novo ``last_modified``, ``id`` ou
        ``url``), lança ``ResourceRevisionConflictError`` com os hashes e
        timestamps para evitar perda silenciosa de evidência.
    - Se ``overwrite=True`` e já houver arquivo local, realiza o download da
      nova versão e preserva ``previous_sha256`` e
      ``previous_ckan_last_modified`` no manifesto atualizado.

    Args:
        source: Fonte (``"eolica"``) ou identificador do dataset CKAN.
        year: Ano de referência com 4 dígitos.
        month: Mês de referência (1 a 12).
        file_format: Formato solicitado (padrão ``"csv"``).
        output_dir: Diretório onde o arquivo ``ons_<source>_YYYY_MM.<ext>`` será salvo.
        timeout: Limite em segundos por requisição HTTP.
        max_attempts: Número máximo de tentativas de download.
        chunk_size: Tamanho em bytes de cada bloco lido no stream.
        overwrite: Se ``True``, autoriza atualizar um arquivo local existente,
            registrando o hash e a versão anteriores no manifesto.
        session: Sessão HTTP opcional para reutilização de conexão e testes.

    Returns:
        Resultado verificado do download contendo ``destination_path``,
        ``size_bytes``, ``sha256`` e ``attempts`` (``0`` quando o arquivo local
        já correspondia à mesma versão e hash verificados).

    Raises:
        ValueError: Quando qualquer argumento de entrada é inválido.
        ResourceRevisionConflictError: Quando o arquivo local já existe,
            ``overwrite=False`` e há conflito de versão/revisão ou ausência de
            manifesto verificável.
        ResourceDiscoveryError: Quando a consulta ao CKAN falha.
        ResourceDownloadError: Quando o download ou manifesto falha.
    """

    source_slug, dataset_id = resolve_dataset_id(source)
    normalized_year = _validate_year(year)
    normalized_month = _validate_month(month)
    normalized_format = _validate_format(file_format)
    normalized_overwrite = _validate_overwrite(overwrite)
    normalized_chunk_size = _validate_chunk_size(chunk_size)
    destination_path = build_raw_filepath(
        source_slug,
        normalized_year,
        normalized_month,
        normalized_format,
        output_dir=output_dir,
    )
    if destination_path.exists() and destination_path.is_dir():
        raise ValueError(
            f"destination aponta para um diretório existente: {destination_path}."
        )

    metadata_path = build_metadata_filepath(destination_path)
    owns_session = session is None
    client = session if session is not None else requests.Session()

    try:
        ckan_resource = discover_resource(
            dataset_id,
            normalized_year,
            normalized_month,
            normalized_format,
            timeout=timeout,
            session=client,
        )
        return _download_discovered_monthly_resource(
            source_slug=source_slug,
            dataset_id=dataset_id,
            year=normalized_year,
            month=normalized_month,
            file_format=normalized_format,
            ckan_resource=ckan_resource,
            destination_path=destination_path,
            metadata_path=metadata_path,
            timeout=timeout,
            max_attempts=max_attempts,
            chunk_size=normalized_chunk_size,
            overwrite=normalized_overwrite,
            session=client,
        )
    finally:
        if owns_session:
            client.close()


def iter_year_months(
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
) -> list[tuple[int, int]]:
    """Gera a sequência ordenada de pares ``(ano, mês)`` de uma faixa inclusiva.

    Suporta mês único (quando início e fim são iguais) e faixas que atravessam
    a virada de ano (por exemplo, ``2025-11`` até ``2026-02``).

    Args:
        start_year: Ano inicial com 4 dígitos (1000..9999).
        start_month: Mês inicial (1..12).
        end_year: Ano final com 4 dígitos (1000..9999).
        end_month: Mês final (1..12).

    Returns:
        Lista ordenada de tuplas ``(year, month)``.

    Raises:
        ValueError: Quando qualquer ano/mês é inválido ou quando o início é
            posterior ao fim.
    """

    s_year = _validate_year(start_year)
    e_year = _validate_year(end_year)
    if s_year < 1000 or e_year < 1000:
        raise ValueError("Os anos inicial e final devem ter 4 dígitos (1000 a 9999).")
    s_month = _validate_month(start_month)
    e_month = _validate_month(end_month)

    if (s_year, s_month) > (e_year, e_month):
        raise ValueError(
            f"Faixa de períodos inválida: início {s_year:04d}-{s_month:02d} é "
            f"posterior ao fim {e_year:04d}-{e_month:02d}."
        )

    periods: list[tuple[int, int]] = []
    current_year, current_month = s_year, s_month
    while (current_year, current_month) <= (e_year, e_month):
        periods.append((current_year, current_month))
        if current_month == 12:
            current_year += 1
            current_month = 1
        else:
            current_month += 1
    return periods


def download_period_range(
    source: str,
    start_year: int,
    start_month: int,
    end_year: int | None = None,
    end_month: int | None = None,
    file_format: str = "csv",
    *,
    output_dir: Path | str = DEFAULT_RAW_DIR,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    chunk_size: int = DEFAULT_CHUNK_SIZE_BYTES,
    overwrite: bool = False,
    allow_missing: bool = False,
    session: requests.Session | None = None,
) -> list[MonthlyExtractionReport]:
    """Baixa um mês único ou uma faixa de meses consultando o catálogo CKAN uma única vez.

    Antes de iniciar qualquer download em disco, resolve todos os períodos da
    faixa em memória a partir do catálogo CKAN obtido:
    - Com ``allow_missing=False`` (padrão), se qualquer mês da faixa não tiver
      recurso compatível para o conjunto, período e formato solicitados (ou
      tiver recurso ambíguo), lança ``ResourceNotFoundError`` /
      ``AmbiguousResourceError`` **antes** de baixar ou gravar qualquer arquivo,
      evitando efeitos parciais em disco.
    - Com ``allow_missing=True``, captura exclusivamente ``ResourceNotFoundError``
      e registra o período no relatório com ``status="missing"`` (indicando que
      não foi encontrado recurso compatível para o período e formato solicitados),
      sem silenciar erros de rede, ambiguidade, download ou conflitos de revisão.

    Args:
        source: Fonte (``"eolica"``) ou identificador do dataset CKAN.
        start_year: Ano inicial com 4 dígitos.
        start_month: Mês inicial (1..12).
        end_year: Ano final opcional; se omitido e ``end_month`` for informado,
            assume ``start_year``.
        end_month: Mês final opcional; se omitido junto com ``end_year``,
            baixa apenas ``(start_year, start_month)``.
        file_format: Formato solicitado (padrão ``"csv"``).
        output_dir: Diretório de destino (padrão ``data/raw``).
        timeout: Limite em segundos por requisição HTTP.
        max_attempts: Número máximo de tentativas de download por arquivo.
        chunk_size: Tamanho em bytes de cada bloco de streaming.
        overwrite: Se ``True``, permite atualizar revisões existentes.
        allow_missing: Se ``True``, registra meses sem recurso compatível para o
            período e formato solicitados como ``missing`` em vez de interromper.
        session: Sessão HTTP opcional para reutilização de conexão e testes.

    Returns:
        Lista ordenada de ``MonthlyExtractionReport`` com um item por mês da faixa.

    Raises:
        ValueError: Quando os limites de período ou parâmetros são inválidos.
        ResourceNotFoundError: Quando não há recurso compatível para algum período
            e formato solicitados e ``allow_missing=False``.
        ResourceDiscoveryError: Quando a consulta ao CKAN falha ou há ambiguidade.
        ResourceRevisionConflictError: Quando há conflito de revisão com ``overwrite=False``.
        ResourceDownloadError: Quando o download ou a gravação do manifesto falha.
    """

    if not isinstance(allow_missing, bool):
        raise TypeError("allow_missing deve ser um valor booleano (True ou False).")

    if end_year is not None and end_month is None:
        raise ValueError("Informe end_month quando end_year for especificado.")

    resolved_end_year = start_year if end_year is None else end_year
    resolved_end_month = start_month if end_month is None else end_month

    source_slug, dataset_id = resolve_dataset_id(source)
    normalized_format = _validate_format(file_format)
    normalized_timeout = _validate_timeout(timeout)
    normalized_max_attempts = _validate_max_attempts(max_attempts)
    normalized_chunk_size = _validate_chunk_size(chunk_size)
    normalized_overwrite = _validate_overwrite(overwrite)
    normalized_output_dir = _validate_output_dir(output_dir)
    periods = iter_year_months(
        start_year,
        start_month,
        resolved_end_year,
        resolved_end_month,
    )

    owns_session = session is None
    client = session if session is not None else requests.Session()
    reports: list[MonthlyExtractionReport] = []

    try:
        # 1) Consulta o catálogo CKAN uma única vez para toda a faixa solicitada.
        catalog_resources = _fetch_ckan_resources(
            dataset_id,
            timeout=normalized_timeout,
            session=client,
        )

        # 2) Pré-resolve todos os períodos em memória antes de iniciar qualquer download.
        #    Com allow_missing=False, falha antes de gravar qualquer arquivo em disco.
        planned_periods: list[tuple[int, int, ResourceMetadata | None, str | None]] = []
        for year, month in periods:
            try:
                ckan_resource = _select_unique_resource(
                    catalog_resources,
                    dataset=dataset_id,
                    year=year,
                    month=month,
                    file_format=normalized_format,
                )
                planned_periods.append((year, month, ckan_resource, None))
            except ResourceNotFoundError as error:
                if not allow_missing:
                    raise
                planned_periods.append((year, month, None, str(error)))

        # 3) Executa os downloads somente após toda a faixa estar validada no catálogo.
        for year, month, ckan_resource, missing_message in planned_periods:
            period_label = f"{year:04d}-{month:02d}"
            if ckan_resource is None:
                reports.append(
                    {
                        "year": year,
                        "month": month,
                        "period": period_label,
                        "status": "missing",
                        "destination_path": None,
                        "size_bytes": None,
                        "sha256": None,
                        "attempts": 0,
                        "message": missing_message
                        or (
                            f"Nenhum recurso compatível encontrado para dataset={dataset_id!r}, "
                            f"período={period_label} e formato={normalized_format}."
                        ),
                    }
                )
                continue

            destination_path = build_raw_filepath(
                source_slug,
                year,
                month,
                normalized_format,
                output_dir=normalized_output_dir,
            )
            if destination_path.exists() and destination_path.is_dir():
                raise ValueError(
                    f"destination aponta para um diretório existente: {destination_path}."
                )
            metadata_path = build_metadata_filepath(destination_path)

            result = _download_discovered_monthly_resource(
                source_slug=source_slug,
                dataset_id=dataset_id,
                year=year,
                month=month,
                file_format=normalized_format,
                ckan_resource=ckan_resource,
                destination_path=destination_path,
                metadata_path=metadata_path,
                timeout=normalized_timeout,
                max_attempts=normalized_max_attempts,
                chunk_size=normalized_chunk_size,
                overwrite=normalized_overwrite,
                session=client,
            )

            status: Literal["downloaded", "unchanged"] = (
                "unchanged" if result["attempts"] == 0 else "downloaded"
            )
            message = (
                "Arquivo local já corresponde à versão e hash verificados no CKAN."
                if status == "unchanged"
                else f"Download concluído em {result['attempts']} tentativa(s)."
            )
            reports.append(
                {
                    "year": year,
                    "month": month,
                    "period": period_label,
                    "status": status,
                    "destination_path": result["destination_path"],
                    "size_bytes": result["size_bytes"],
                    "sha256": result["sha256"],
                    "attempts": result["attempts"],
                    "message": message,
                }
            )
    finally:
        if owns_session:
            client.close()

    return reports


def build_argument_parser() -> argparse.ArgumentParser:
    """Constrói o parser CLI para ``python -m src.extract``."""
    parser = argparse.ArgumentParser(
        prog="python -m src.extract",
        description=(
            "Descobre e baixa arquivos mensais de restrição de geração do ONS "
            "para um mês ou faixa de meses, com verificação de versão e SHA-256."
        ),
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Ano inicial com 4 dígitos (ex.: 2025).",
    )
    parser.add_argument(
        "--month",
        type=int,
        required=True,
        help="Mês inicial entre 1 e 12 (ex.: 1).",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help="Ano final opcional da faixa (exige --end-month).",
    )
    parser.add_argument(
        "--end-month",
        type=int,
        default=None,
        help="Mês final opcional da faixa (1..12). Se --end-year for omitido, usa --year.",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="eolica",
        help="Fonte de dados (padrão: eolica) ou identificador CKAN homologado.",
    )
    parser.add_argument(
        "--format",
        dest="file_format",
        type=str,
        default="csv",
        help="Formato publicado no CKAN (padrão: csv).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_RAW_DIR,
        help="Diretório de saída relativo ou customizado (padrão: data/raw).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Timeout HTTP em segundos (padrão: {DEFAULT_TIMEOUT_SECONDS}).",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=DEFAULT_MAX_ATTEMPTS,
        help=f"Máximo de tentativas por arquivo (padrão: {DEFAULT_MAX_ATTEMPTS}).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Autoriza atualizar arquivos locais revisados preservando a versão anterior.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help=(
            "Registra períodos sem recurso compatível no formato solicitado "
            "como 'missing' em vez de falhar."
        ),
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    session: requests.Session | None = None,
) -> int:
    """Ponto de entrada CLI para extração de um mês ou faixa de meses do ONS.

    Args:
        argv: Lista opcional de argumentos (padrão ``sys.argv[1:]``).
        session: Sessão HTTP opcional para injeção em testes automatizados.

    Returns:
        Código de saída ``0`` em caso de sucesso ou ``1`` em caso de erro.
    """
    parser = build_argument_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        return code

    try:
        reports = download_period_range(
            args.source,
            args.year,
            args.month,
            end_year=args.end_year,
            end_month=args.end_month,
            file_format=args.file_format,
            output_dir=args.output_dir,
            timeout=args.timeout,
            max_attempts=args.max_attempts,
            overwrite=args.overwrite,
            allow_missing=args.allow_missing,
            session=session,
        )
    except (
        ValueError,
        FileExistsError,
        ResourceDiscoveryError,
        ResourceDownloadError,
    ) as error:
        print(f"Erro na extração: {error}", file=sys.stderr)
        return 1

    for report in reports:
        if report["status"] == "missing":
            print(f"[{report['status']}] {report['period']}: {report['message']}")
        else:
            print(
                f"[{report['status']}] {report['period']}: "
                f"{report['destination_path']} "
                f"({report['size_bytes']} bytes, sha256={report['sha256']})"
            )
    return 0


def _fetch_ckan_resources(
    dataset: str,
    *,
    timeout: float,
    session: requests.Session | None = None,
) -> list[Mapping[str, Any]]:
    """Consulta o endpoint ``package_show`` do CKAN e retorna a lista bruta de recursos."""
    owns_session = session is None
    client = session if session is not None else requests.Session()

    try:
        try:
            response = client.get(
                f"{CKAN_ACTION_URL}/package_show",
                params={"id": dataset},
                timeout=timeout,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise ResourceDiscoveryError(
                f"Falha ao consultar o conjunto CKAN {dataset!r}: {error}"
            ) from error

        try:
            payload = response.json()
        except ValueError as error:
            raise ResourceDiscoveryError("A API CKAN retornou JSON inválido.") from error
    finally:
        if owns_session:
            client.close()

    return _extract_resources(payload, dataset)


def _select_unique_resource(
    resources: Sequence[Mapping[str, Any]],
    *,
    dataset: str,
    year: int,
    month: int,
    file_format: str,
) -> ResourceMetadata:
    """Seleciona exatamente um recurso compatível com período e formato na lista CKAN."""
    matches = [
        resource
        for resource in resources
        if _matches_resource(
            resource,
            year=year,
            month=month,
            file_format=file_format,
        )
    ]

    period = f"{year:04d}-{month:02d}"
    if not matches:
        raise ResourceNotFoundError(
            f"Nenhum recurso encontrado para dataset={dataset!r}, "
            f"período={period} e formato={file_format}."
        )
    if len(matches) > 1:
        resource_ids = [str(resource.get("id", "<sem id>")) for resource in matches]
        raise AmbiguousResourceError(
            f"Foram encontrados {len(matches)} recursos para dataset={dataset!r}, "
            f"período={period} e formato={file_format}: {resource_ids}."
        )

    return _normalize_resource_metadata(matches[0])


def _download_discovered_monthly_resource(
    *,
    source_slug: str,
    dataset_id: str,
    year: int,
    month: int,
    file_format: str,
    ckan_resource: ResourceMetadata,
    destination_path: Path,
    metadata_path: Path,
    timeout: float,
    max_attempts: int,
    chunk_size: int,
    overwrite: bool,
    session: requests.Session,
) -> DownloadResult:
    """Executa verificação de revisão, download em staging e commit transacional de um mês."""
    previous_sha256: str | None = None
    previous_last_modified: str | None = None
    local_size: int | None = None
    local_sha256: str | None = None
    recorded_metadata: CollectionMetadata | None = None

    if destination_path.exists():
        local_size, local_sha256 = compute_file_sha256(
            destination_path,
            chunk_size=chunk_size,
        )
        recorded_metadata = read_collection_metadata(metadata_path)

        if not overwrite:
            _verify_existing_file_matches_remote_revision(
                destination_path=destination_path,
                local_size=local_size,
                local_sha256=local_sha256,
                recorded_metadata=recorded_metadata,
                ckan_resource=ckan_resource,
            )
            return {
                "url": ckan_resource["url"],
                "destination_path": destination_path,
                "size_bytes": local_size,
                "sha256": local_sha256,
                "attempts": 0,
            }

        previous_sha256 = local_sha256
        if recorded_metadata is not None:
            previous_last_modified = recorded_metadata["ckan_last_modified"]

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    staging_fd, staging_name = tempfile.mkstemp(
        prefix=f".{destination_path.name}.staging.",
        suffix=".tmp",
        dir=destination_path.parent,
    )
    os.close(staging_fd)
    staging_path = Path(staging_name)

    try:
        staging_result = download_resource_file(
            ckan_resource["url"],
            staging_path,
            timeout=timeout,
            max_attempts=max_attempts,
            chunk_size=chunk_size,
            overwrite=True,
            session=session,
        )

        new_sha256 = staging_result["sha256"]
        new_size = staging_result["size_bytes"]
        revision_history: list[RevisionHistoryEntry] = (
            list(recorded_metadata["revision_history"])
            if recorded_metadata is not None
            else []
        )

        archived_path: Path | None = None
        if (
            local_sha256 is not None
            and local_size is not None
            and local_sha256 != new_sha256
        ):
            archived_path = build_archived_revision_filepath(
                destination_path,
                local_sha256,
            )
            history_entry: RevisionHistoryEntry = {
                "sha256": local_sha256,
                "size_bytes": local_size,
                "collected_at_utc": (
                    recorded_metadata["collected_at_utc"]
                    if recorded_metadata is not None
                    else None
                ),
                "ckan_resource_id": (
                    recorded_metadata["ckan_resource_id"]
                    if recorded_metadata is not None
                    else None
                ),
                "ckan_last_modified": previous_last_modified,
                "archived_file_path": archived_path.as_posix(),
            }
            if not any(item["sha256"] == local_sha256 for item in revision_history):
                revision_history.append(history_entry)
        elif local_sha256 == new_sha256 and recorded_metadata is not None:
            previous_sha256 = recorded_metadata["previous_sha256"]
            previous_last_modified = recorded_metadata["previous_ckan_last_modified"]

        collection_record: CollectionMetadata = {
            "source": source_slug,
            "dataset": dataset_id,
            "year": year,
            "month": month,
            "file_format": file_format,
            "file_name": destination_path.name,
            "file_path": destination_path.as_posix(),
            "size_bytes": new_size,
            "sha256": new_sha256,
            "collected_at_utc": datetime.now(UTC).isoformat(),
            "ckan_resource_id": ckan_resource["id"],
            "ckan_resource_name": ckan_resource["name"],
            "source_url": ckan_resource["url"],
            "ckan_created": ckan_resource["created"],
            "ckan_last_modified": ckan_resource["last_modified"],
            "previous_sha256": previous_sha256,
            "previous_ckan_last_modified": previous_last_modified,
            "revision_history": revision_history,
        }

        _commit_staged_raw_and_metadata(
            staging_path=staging_path,
            destination_path=destination_path,
            metadata_path=metadata_path,
            collection_record=collection_record,
            archived_path=archived_path,
        )
    finally:
        staging_path.unlink(missing_ok=True)

    return {
        "url": staging_result["url"],
        "destination_path": destination_path,
        "size_bytes": staging_result["size_bytes"],
        "sha256": staging_result["sha256"],
        "attempts": staging_result["attempts"],
    }


def _validate_dataset(dataset: str) -> str:
    """Valida o identificador do conjunto CKAN.

    Garante que o nome do dataset seja uma string não vazia contendo apenas
    caracteres alfanuméricos, hífen ou sublinhado, prevenindo injeção na rota.
    """
    if not isinstance(dataset, str) or not dataset:
        raise ValueError("dataset deve ser uma string não vazia.")
    if not _DATASET_PATTERN.fullmatch(dataset):
        raise ValueError(
            "dataset deve conter somente letras, números, hífen e sublinhado."
        )
    return dataset


def _validate_year(year: int) -> int:
    """Valida o ano de referência do recurso.

    Rejeita valores booleanos (já que ``bool`` é subclasse de ``int`` em Python)
    e garante que o ano esteja no intervalo calendário válido (1 a 9999).
    """
    if isinstance(year, bool) or not isinstance(year, int) or not 1 <= year <= 9999:
        raise ValueError("year deve ser um número inteiro entre 1 e 9999.")
    return year


def _validate_month(month: int) -> int:
    """Valida o mês de referência do recurso.

    Rejeita valores booleanos e garante que o mês esteja entre 1 (janeiro)
    e 12 (dezembro).
    """
    if isinstance(month, bool) or not isinstance(month, int) or not 1 <= month <= 12:
        raise ValueError("month deve ser um número inteiro entre 1 e 12.")
    return month


def _validate_format(file_format: str) -> str:
    """Valida e padroniza o formato do arquivo solicitado.

    Exige uma string alfanumérica não vazia e retorna o formato em letras
    maiúsculas (ex.: ``"csv"`` -> ``"CSV"``) para comparação uniforme.
    """
    if not isinstance(file_format, str) or not file_format:
        raise ValueError("file_format deve ser uma string não vazia.")
    if not _FORMAT_PATTERN.fullmatch(file_format):
        raise ValueError("file_format deve conter somente letras e números.")
    return file_format.upper()


def _validate_timeout(timeout: float) -> float:
    """Valida o tempo limite (timeout) em segundos para a requisição HTTP.

    Rejeita booleanos e exige um número inteiro ou de ponto flutuante
    estritamente positivo, convertendo-o para ``float``.
    """
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("timeout deve ser um número maior que zero.")
    return float(timeout)


def _extract_resources(payload: Any, dataset: str) -> list[Mapping[str, Any]]:
    """Extrai e valida a lista bruta de recursos do payload JSON do CKAN.

    Verifica a estrutura do envelope da resposta (``success == True``, presença
    do objeto ``result`` e da lista ``resources`` com objetos válidos) antes de
    permitir a filtragem dos recursos.
    """
    if not isinstance(payload, Mapping):
        raise ResourceDiscoveryError("A resposta CKAN não é um objeto JSON.")
    if payload.get("success") is not True:
        raise ResourceDiscoveryError(
            f"A API CKAN informou falha para o conjunto {dataset!r}: "
            f"{payload.get('error', 'erro não detalhado')!r}."
        )

    result = payload.get("result")
    if not isinstance(result, Mapping):
        raise ResourceDiscoveryError("A resposta CKAN não contém um objeto result válido.")

    resources = result.get("resources")
    if not isinstance(resources, list):
        raise ResourceDiscoveryError("A resposta CKAN não contém uma lista resources válida.")
    if not all(isinstance(resource, Mapping) for resource in resources):
        raise ResourceDiscoveryError("A lista resources contém item que não é um objeto.")
    return resources


def _matches_resource(
    resource: Mapping[str, Any],
    *,
    year: int,
    month: int,
    file_format: str,
) -> bool:
    """Verifica se um recurso do catálogo corresponde ao ano, mês e formato.

    Inspeciona o sufixo ``-AAAA-MM`` no campo ``name`` do recurso CKAN e
    compara o campo ``format`` de maneira insensível a maiúsculas/minúsculas.
    """
    name = resource.get("name")
    resource_format = resource.get("format")
    if not isinstance(name, str) or not isinstance(resource_format, str):
        return False

    # Extrai o ano e o mês do final do nome do recurso (ex.: Restricoes_coff_eolicas-2025-01).
    period_match = _RESOURCE_PERIOD_PATTERN.search(name)
    if period_match is None:
        return False

    return (
        int(period_match.group("year")) == year
        and int(period_match.group("month")) == month
        and resource_format.strip().upper() == file_format
    )


def _normalize_resource_metadata(resource: Mapping[str, Any]) -> ResourceMetadata:
    """Valida campos obrigatórios e normaliza os metadados do recurso CKAN.

    Garante que ``id``, ``name``, ``format`` e ``url`` sejam strings não vazias,
    verifica se a URL possui esquema ``http`` ou ``https`` com domínio válido
    e preserva os carimbos temporais ``created`` e ``last_modified``.
    """
    required_fields = ("id", "name", "format", "url")
    invalid_fields = [
        field
        for field in required_fields
        if not isinstance(resource.get(field), str) or not resource[field].strip()
    ]
    if invalid_fields:
        raise ResourceDiscoveryError(
            f"O recurso CKAN possui campos obrigatórios inválidos: {invalid_fields}."
        )

    # Confirma que a URL do recurso é um endereço HTTP/HTTPS completo e válido.
    resource_url = resource["url"].strip()
    parsed_url = urlparse(resource_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ResourceDiscoveryError(f"O recurso CKAN possui URL inválida: {resource_url!r}.")

    created = resource.get("created")
    last_modified = resource.get("last_modified")
    if created is not None and not isinstance(created, str):
        raise ResourceDiscoveryError("O campo created do recurso não é texto nem nulo.")
    if last_modified is not None and not isinstance(last_modified, str):
        raise ResourceDiscoveryError("O campo last_modified do recurso não é texto nem nulo.")

    return {
        "id": resource["id"].strip(),
        "name": resource["name"].strip(),
        "format": resource["format"].strip().upper(),
        "url": resource_url,
        "created": created,
        "last_modified": last_modified,
    }


def _validate_download_url(url: str) -> str:
    """Valida a URL de origem do arquivo a ser baixado.

    Exige uma string não vazia com esquema ``http`` ou ``https`` e domínio
    (``netloc``) explícito.
    """
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url deve ser uma string não vazia.")
    normalized_url = url.strip()
    parsed = urlparse(normalized_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"url deve usar esquema http ou https válido: {url!r}.")
    return normalized_url


def _validate_max_attempts(max_attempts: int) -> int:
    """Valida a quantidade máxima de tentativas de download.

    Rejeita booleanos e exige um número inteiro maior ou igual a 1.
    """
    if (
        isinstance(max_attempts, bool)
        or not isinstance(max_attempts, int)
        or max_attempts < 1
    ):
        raise ValueError("max_attempts deve ser um número inteiro maior ou igual a 1.")
    return max_attempts


def _validate_chunk_size(chunk_size: int) -> int:
    """Valida o tamanho em bytes de cada bloco de leitura em streaming.

    Rejeita booleanos e exige um número inteiro estritamente positivo.
    """
    if (
        isinstance(chunk_size, bool)
        or not isinstance(chunk_size, int)
        or chunk_size < 1
    ):
        raise ValueError("chunk_size deve ser um número inteiro maior que zero.")
    return chunk_size


def _validate_overwrite(overwrite: bool) -> bool:
    """Valida o sinalizador booleano de permissão de sobrescrita."""
    if not isinstance(overwrite, bool):
        raise TypeError("overwrite deve ser um valor booleano (True ou False).")
    return overwrite


def _validate_output_dir(output_dir: Path | str) -> Path:
    """Valida o diretório de saída para armazenamento de arquivos brutos.

    Aceita ``Path`` ou ``str`` não vazia e falha caso o caminho já exista no
    sistema de arquivos como um arquivo comum em vez de diretório.
    """
    if isinstance(output_dir, str):
        if not output_dir.strip():
            raise ValueError("output_dir não pode ser uma string vazia.")
        normalized_dir = Path(output_dir.strip())
    elif isinstance(output_dir, Path):
        normalized_dir = output_dir
    else:
        raise TypeError("output_dir deve ser um objeto Path ou uma string não vazia.")

    if normalized_dir.exists() and not normalized_dir.is_dir():
        raise ValueError(
            f"output_dir aponta para um arquivo existente, não um diretório: {normalized_dir}."
        )
    return normalized_dir


def _validate_destination(destination: Path | str, *, overwrite: bool) -> Path:
    """Valida o caminho local de destino antes de iniciar o download.

    Aceita ``Path`` ou ``str`` não vazia, rejeita diretórios existentes e
    impede sobrescrita silenciosa de arquivos quando ``overwrite=False``.
    """
    if isinstance(destination, str):
        if not destination.strip():
            raise ValueError("destination não pode ser uma string vazia.")
        normalized_destination = Path(destination)
    elif isinstance(destination, Path):
        normalized_destination = destination
    else:
        raise TypeError("destination deve ser um objeto Path ou uma string não vazia.")

    if normalized_destination.exists():
        if normalized_destination.is_dir():
            raise ValueError(
                f"destination aponta para um diretório existente: {normalized_destination}."
            )
        if not overwrite:
            raise FileExistsError(
                f"O arquivo de destino já existe e overwrite=False: {normalized_destination}."
            )

    return normalized_destination


def _expected_content_length(headers: Mapping[str, Any] | None) -> int | None:
    """Extrai o tamanho esperado em bytes a partir dos cabeçalhos HTTP.

    Ignora ``Content-Length`` quando ``Content-Encoding`` está presente, pois
    servidores podem informar o tamanho comprimido enquanto ``iter_content``
    entrega os bytes descomprimidos. Falha se ``Content-Length`` for inválido.
    """
    if not isinstance(headers, Mapping):
        return None

    normalized_headers = {
        str(key).lower(): str(value).strip()
        for key, value in headers.items()
        if value is not None
    }
    content_encoding = normalized_headers.get("content-encoding", "").lower()
    if content_encoding and content_encoding != "identity":
        return None

    raw_length = normalized_headers.get("content-length")
    if not raw_length:
        return None

    try:
        parsed_length = int(raw_length)
    except ValueError as error:
        raise ResourceDownloadError(
            f"Cabeçalho Content-Length inválido recebido no download: {raw_length!r}."
        ) from error

    if parsed_length < 0:
        raise ResourceDownloadError(
            f"Cabeçalho Content-Length negativo recebido no download: {parsed_length}."
        )
    return parsed_length


def _iter_response_chunks(response: Any, chunk_size: int) -> Iterator[bytes]:
    """Itera sobre os blocos de bytes de uma resposta HTTP em streaming.

    Valida que a resposta oferece ``iter_content`` e que cada bloco não vazio
    é do tipo ``bytes``.
    """
    iter_content = getattr(response, "iter_content", None)
    if not callable(iter_content):
        raise ResourceDownloadError(
            "O objeto de resposta HTTP não suporta leitura em streaming (iter_content)."
        )

    for chunk in iter_content(chunk_size=chunk_size):
        if not chunk:
            continue
        if not isinstance(chunk, (bytes, bytearray)):
            raise ResourceDownloadError(
                "O stream HTTP retornou conteúdo que não está em bytes."
            )
        yield bytes(chunk)


def _stream_response_to_destination(
    *,
    response: Any,
    destination: Path,
    chunk_size: int,
    overwrite: bool,
) -> tuple[int, str]:
    """Grava o stream HTTP em arquivo temporário, valida integridade e move ao destino.

    Calcula o hash SHA-256 incrementalmente durante a escrita, verifica se o
    arquivo não está vazio e confere se o total de bytes coincide com
    ``Content-Length`` (quando aplicável). Se qualquer erro ocorrer, o arquivo
    temporário é removido antes de propagar a exceção.
    """
    expected_length = _expected_content_length(getattr(response, "headers", None))
    digest = hashlib.sha256()
    size_bytes = 0

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".part",
        dir=destination.parent,
    )
    temp_path = Path(temp_name)

    try:
        with os.fdopen(fd, "wb") as temp_file:
            for chunk in _iter_response_chunks(response, chunk_size):
                temp_file.write(chunk)
                digest.update(chunk)
                size_bytes += len(chunk)
            temp_file.flush()

        if size_bytes == 0:
            raise ResourceDownloadError(
                f"O download para {destination} retornou 0 bytes (arquivo vazio)."
            )

        if expected_length is not None and size_bytes != expected_length:
            raise ResourceDownloadError(
                f"Download incompleto para {destination}: recebidos {size_bytes} bytes, "
                f"esperados {expected_length} bytes (Content-Length)."
            )

        # Verifica novamente antes da substituição atômica para evitar condição de corrida.
        if destination.exists() and not overwrite:
            raise FileExistsError(
                f"O arquivo de destino já existe e overwrite=False: {destination}."
            )

        temp_path.replace(destination)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise

    return size_bytes, digest.hexdigest().upper()


def _validate_sha256_hex(value: Any, *, field_name: str) -> str:
    """Valida que um valor é uma string hexadecimal SHA-256 de 64 caracteres."""
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value.strip()):
        raise ValueError(
            f"{field_name} deve ser um hash SHA-256 com 64 caracteres hexadecimais."
        )
    return value.strip().upper()


def _validate_utc_iso_timestamp(value: Any, *, field_name: str) -> str:
    """Valida que uma string está em formato ISO-8601 válido com fuso UTC."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} deve ser um carimbo ISO-8601 UTC não vazio.")
    normalized = value.strip()
    candidate = normalized[:-1] + "+00:00" if normalized.endswith("Z") else normalized
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as error:
        raise ValueError(
            f"{field_name} não é uma data/hora ISO-8601 válida: {value!r}."
        ) from error

    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError(
            f"{field_name} deve possuir fuso horário UTC explícito (+00:00 ou Z): {value!r}."
        )
    return normalized


def _validate_revision_history_entry(
    entry: Any,
    metadata_path: Path,
) -> RevisionHistoryEntry:
    """Valida uma entrada individual do histórico de revisões do manifesto."""
    if not isinstance(entry, Mapping):
        raise ResourceDownloadError(
            f"Item de revision_history inválido em {metadata_path}: esperado objeto JSON."
        )

    try:
        sha256_hex = _validate_sha256_hex(
            entry.get("sha256"),
            field_name="revision_history.sha256",
        )
    except ValueError as error:
        raise ResourceDownloadError(f"Erro em {metadata_path}: {error}") from error

    size_bytes = entry.get("size_bytes")
    if isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or size_bytes <= 0:
        raise ResourceDownloadError(
            f"Campo revision_history.size_bytes inválido em {metadata_path}."
        )

    archived_file_path = entry.get("archived_file_path")
    if not isinstance(archived_file_path, str) or not archived_file_path.strip():
        raise ResourceDownloadError(
            f"Campo revision_history.archived_file_path inválido em {metadata_path}."
        )

    collected_at_utc = entry.get("collected_at_utc")
    if collected_at_utc is not None:
        try:
            collected_at_utc = _validate_utc_iso_timestamp(
                collected_at_utc,
                field_name="revision_history.collected_at_utc",
            )
        except ValueError as error:
            raise ResourceDownloadError(f"Erro em {metadata_path}: {error}") from error

    for opt_field in ("ckan_resource_id", "ckan_last_modified"):
        opt_val = entry.get(opt_field)
        if opt_val is not None and (not isinstance(opt_val, str) or not opt_val.strip()):
            raise ResourceDownloadError(
                f"Campo revision_history.{opt_field} inválido em {metadata_path}."
            )

    return {
        "sha256": sha256_hex,
        "size_bytes": int(size_bytes),
        "collected_at_utc": collected_at_utc,
        "ckan_resource_id": (
            str(entry["ckan_resource_id"]).strip()
            if isinstance(entry.get("ckan_resource_id"), str)
            else None
        ),
        "ckan_last_modified": (
            str(entry["ckan_last_modified"]).strip()
            if isinstance(entry.get("ckan_last_modified"), str)
            else None
        ),
        "archived_file_path": archived_file_path.strip(),
    }


def _validate_collection_metadata_payload(
    payload: Any,
    metadata_path: Path,
) -> CollectionMetadata:
    """Valida estritamente a estrutura, tipos e domínio de um manifesto de coleta.

    Verifica:
    - presença de todos os campos obrigatórios;
    - correspondência entre ``source`` e ``dataset`` homologados;
    - ``year`` de 4 dígitos (1000..9999), ``month`` entre 1 e 12 e ``size_bytes > 0``;
    - ``sha256`` e ``previous_sha256`` com exatos 64 caracteres hexadecimais;
    - ``collected_at_utc`` em formato ISO-8601 com fuso UTC explícito;
    - ``source_url`` com esquema ``http`` ou ``https`` e domínio válido;
    - integridade de todas as entradas em ``revision_history``.
    """
    if not isinstance(payload, Mapping):
        raise ResourceDownloadError(
            f"O manifesto de metadados em {metadata_path} não é um objeto JSON."
        )

    required_str_fields = (
        "source",
        "dataset",
        "file_format",
        "file_name",
        "file_path",
        "sha256",
        "collected_at_utc",
        "ckan_resource_id",
        "ckan_resource_name",
        "source_url",
    )
    for field in required_str_fields:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ResourceDownloadError(
                f"Campo obrigatório ausente ou inválido em {metadata_path}: {field!r}."
            )

    for int_field in ("year", "month", "size_bytes"):
        value = payload.get(int_field)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ResourceDownloadError(
                f"Campo numérico inválido em {metadata_path}: {int_field!r}."
            )

    try:
        resolved_source, resolved_dataset = resolve_dataset_id(str(payload["source"]))
        if str(payload["dataset"]).strip().lower() != resolved_dataset:
            raise ValueError(
                f"dataset {payload['dataset']!r} não corresponde à fonte {resolved_source!r}."
            )
        normalized_year = _validate_year(int(payload["year"]))
        if normalized_year < 1000:
            raise ValueError("year deve ter 4 dígitos (entre 1000 e 9999).")
        normalized_month = _validate_month(int(payload["month"]))
        normalized_format = _validate_format(str(payload["file_format"]).strip())
        normalized_sha256 = _validate_sha256_hex(
            payload.get("sha256"),
            field_name="sha256",
        )
        normalized_collected_at = _validate_utc_iso_timestamp(
            payload.get("collected_at_utc"),
            field_name="collected_at_utc",
        )
        normalized_source_url = _validate_download_url(str(payload["source_url"]))
    except ValueError as error:
        raise ResourceDownloadError(
            f"Metadados inválidos em {metadata_path}: {error}"
        ) from error

    optional_str_fields = (
        "ckan_created",
        "ckan_last_modified",
        "previous_sha256",
        "previous_ckan_last_modified",
    )
    for field in optional_str_fields:
        value = payload.get(field)
        if value is not None and not isinstance(value, str):
            raise ResourceDownloadError(
                f"Campo opcional inválido em {metadata_path}: {field!r} deve ser string ou null."
            )

    normalized_previous_sha256: str | None = None
    if payload.get("previous_sha256") is not None:
        try:
            normalized_previous_sha256 = _validate_sha256_hex(
                payload.get("previous_sha256"),
                field_name="previous_sha256",
            )
        except ValueError as error:
            raise ResourceDownloadError(
                f"Metadados inválidos em {metadata_path}: {error}"
            ) from error

    raw_history = payload.get("revision_history", [])
    if not isinstance(raw_history, list):
        raise ResourceDownloadError(
            f"Campo revision_history inválido em {metadata_path}: esperado uma lista."
        )
    validated_history = [
        _validate_revision_history_entry(item, metadata_path) for item in raw_history
    ]

    return {
        "source": resolved_source,
        "dataset": resolved_dataset,
        "year": normalized_year,
        "month": normalized_month,
        "file_format": normalized_format,
        "file_name": str(payload["file_name"]).strip(),
        "file_path": str(payload["file_path"]).strip(),
        "size_bytes": int(payload["size_bytes"]),
        "sha256": normalized_sha256,
        "collected_at_utc": normalized_collected_at,
        "ckan_resource_id": str(payload["ckan_resource_id"]).strip(),
        "ckan_resource_name": str(payload["ckan_resource_name"]).strip(),
        "source_url": normalized_source_url,
        "ckan_created": payload.get("ckan_created"),
        "ckan_last_modified": payload.get("ckan_last_modified"),
        "previous_sha256": normalized_previous_sha256,
        "previous_ckan_last_modified": payload.get("previous_ckan_last_modified"),
        "revision_history": validated_history,
    }


def _commit_staged_raw_and_metadata(
    *,
    staging_path: Path,
    destination_path: Path,
    metadata_path: Path,
    collection_record: CollectionMetadata,
    archived_path: Path | None,
) -> None:
    """Promove de forma transacional o CSV baixado e seu manifesto de metadados.

    Se um arquivo bruto anterior já existir:
    - Caso ``archived_path`` seja fornecido (conteúdo revisado com hash distinto),
      move o arquivo antigo para ``archived_path`` (ou para um backup temporário
      se ``archived_path`` já existir).
    - Caso contrário (mesmo hash rebaixado com ``overwrite=True``), move o
      arquivo antigo para um backup temporário de rollback.
    Em seguida, move ``staging_path`` para ``destination_path`` e grava
    ``metadata_path``. Se a gravação do manifesto falhar, restaura o arquivo
    bruto anterior (ou remove o arquivo novo se não havia versão anterior) antes
    de relançar a exceção, garantindo que CSV e manifesto nunca fiquem
    inconsistentes.
    """
    had_existing_file = destination_path.exists()
    backup_path: Path | None = None
    created_archive = False

    if had_existing_file:
        if archived_path is not None and not archived_path.exists():
            destination_path.replace(archived_path)
            backup_path = archived_path
            created_archive = True
        else:
            backup_fd, backup_name = tempfile.mkstemp(
                prefix=f".{destination_path.name}.backup.",
                suffix=".bak",
                dir=destination_path.parent,
            )
            os.close(backup_fd)
            backup_path = Path(backup_name)
            destination_path.replace(backup_path)

    try:
        staging_path.replace(destination_path)
        write_collection_metadata(metadata_path, collection_record)
    except BaseException:
        # Rollback: garante que o CSV novo não fique órfão ou desalinhado do manifesto antigo.
        if destination_path.exists():
            destination_path.unlink(missing_ok=True)
        if backup_path is not None and backup_path.exists():
            backup_path.replace(destination_path)
        raise
    else:
        if backup_path is not None and not created_archive and backup_path.exists():
            backup_path.unlink(missing_ok=True)


def _verify_existing_file_matches_remote_revision(
    *,
    destination_path: Path,
    local_size: int,
    local_sha256: str,
    recorded_metadata: CollectionMetadata | None,
    ckan_resource: ResourceMetadata,
) -> None:
    """Verifica se um arquivo local existente corresponde à revisão atual publicada no CKAN.

    Lança ``ResourceRevisionConflictError`` se:
    - não houver manifesto ``.metadata.json`` que comprove a versão de origem;
    - o hash ou tamanho real do arquivo em disco divergir do manifesto local;
    - o ID, a URL ou o carimbo ``last_modified`` do recurso no CKAN tiver mudado,
      ou se ``last_modified`` estiver ausente (impedindo garantir que não houve revisão).
    """
    if recorded_metadata is None:
        raise ResourceRevisionConflictError(
            f"O arquivo local {destination_path} já existe (SHA-256={local_sha256}), "
            f"mas não possui manifesto de metadados para comprovar sua versão frente ao "
            f"recurso CKAN {ckan_resource['id']!r} (last_modified={ckan_resource['last_modified']!r}). "
            f"Use overwrite=True para atualizar e registrar a versão/hash."
        )

    if (
        local_sha256 != recorded_metadata["sha256"]
        or local_size != recorded_metadata["size_bytes"]
    ):
        raise ResourceRevisionConflictError(
            f"O arquivo local {destination_path} foi modificado em relação ao manifesto "
            f"registrado: disco=(size={local_size}, sha256={local_sha256}) vs "
            f"manifesto=(size={recorded_metadata['size_bytes']}, sha256={recorded_metadata['sha256']}). "
            f"Use overwrite=True para rebaixar e atualizar o registro."
        )

    remote_last_modified = ckan_resource["last_modified"]
    recorded_last_modified = recorded_metadata["ckan_last_modified"]
    if (
        ckan_resource["id"] != recorded_metadata["ckan_resource_id"]
        or ckan_resource["url"] != recorded_metadata["source_url"]
        or remote_last_modified is None
        or remote_last_modified != recorded_last_modified
    ):
        raise ResourceRevisionConflictError(
            f"Detectada possível revisão no CKAN para {destination_path} "
            f"(SHA-256 local={local_sha256}): versão local "
            f"(id={recorded_metadata['ckan_resource_id']!r}, "
            f"last_modified={recorded_last_modified!r}) difere da versão remota "
            f"(id={ckan_resource['id']!r}, last_modified={remote_last_modified!r}). "
            f"Use overwrite=True para baixar a nova revisão e preservar o hash anterior."
        )


if __name__ == "__main__":
    raise SystemExit(main())
