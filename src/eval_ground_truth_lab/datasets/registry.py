from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_SCHEMA_VERSION = "1.0"
REQUIRED_CASE_FIELDS = ("id", "input", "expected")
ALLOWED_CASE_FIELDS = frozenset({*REQUIRED_CASE_FIELDS, "metadata"})
ALLOWED_YAML_DATASET_FIELDS = frozenset({"cases", "dataset_id", "schema_version"})


class _DuplicateJsonKeyError(ValueError):
    pass


class _UniqueKeySafeLoader(yaml.SafeLoader):
    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
        self.flatten_mapping(node)
        mapping: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as exc:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found an unhashable mapping key",
                    key_node.start_mark,
                ) from exc
            if duplicate:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


class DatasetValidationError(ValueError):
    """Raised when an eval dataset does not match the required case schema."""

    def __init__(self, *, case_id: str | None, field: str, message: str) -> None:
        self.case_id = case_id
        self.field = field
        super().__init__(message)


@dataclass(frozen=True)
class DatasetCase:
    id: str
    input: Any
    expected: Any
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: dict[str, Any], *, line_number: int | None = None) -> DatasetCase:
        case_id = _string_or_none(raw.get("id"))
        case_ref = case_id or (f"line {line_number}" if line_number is not None else None)

        unknown_fields = sorted(set(raw) - ALLOWED_CASE_FIELDS)
        if unknown_fields:
            raise DatasetValidationError(
                case_id=case_ref,
                field="case",
                message=(
                    f"Dataset case {case_ref or '<unknown>'} contains unknown fields: "
                    + ", ".join(unknown_fields)
                ),
            )

        for required_field in REQUIRED_CASE_FIELDS:
            if required_field not in raw:
                raise DatasetValidationError(
                    case_id=case_ref,
                    field=required_field,
                    message=(
                        f"Dataset case {case_ref or '<unknown>'} is missing "
                        f"required field '{required_field}'"
                    ),
                )

        if not case_id:
            raise DatasetValidationError(
                case_id=case_ref,
                field="id",
                message=f"Dataset case {case_ref or '<unknown>'} has an empty or non-string id",
            )

        metadata = raw.get("metadata", {})
        if not isinstance(metadata, dict):
            raise DatasetValidationError(
                case_id=case_id,
                field="metadata",
                message=f"Dataset case {case_id} field 'metadata' must be an object",
            )

        return cls(
            id=case_id,
            input=raw["input"],
            expected=raw["expected"],
            metadata=dict(metadata),
        )

    def to_canonical_mapping(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "input": self.input,
            "expected": self.expected,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class DatasetMetadata:
    dataset_id: str
    schema_version: str
    case_count: int
    dataset_hash: str
    source_path: Path


@dataclass(frozen=True)
class Dataset:
    metadata: DatasetMetadata
    cases: tuple[DatasetCase, ...]


def load_dataset(path: str | Path) -> Dataset:
    source_path = Path(path)
    return load_dataset_bytes(source_path.read_bytes(), source_path=source_path)


def load_dataset_bytes(payload: bytes, *, source_path: str | Path) -> Dataset:
    """Load a dataset from one immutable byte snapshot.

    Callers that must bind validation and later packaging to the same input can
    read a file or package resource once and pass those exact bytes here.
    """

    source_path = Path(source_path)
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DatasetValidationError(
            case_id=None,
            field="encoding",
            message=f"Dataset {source_path} must be UTF-8",
        ) from exc
    if source_path.suffix.lower() in {".yaml", ".yml"}:
        dataset_id, schema_version, raw_cases = _load_yaml_text(text, source_path)
    elif source_path.suffix.lower() == ".jsonl":
        dataset_id, schema_version, raw_cases = _load_jsonl_text(text, source_path)
    else:
        raise ValueError(f"Unsupported dataset extension for {source_path}")

    cases = tuple(
        DatasetCase.from_mapping(raw_case, line_number=index)
        for index, raw_case in enumerate(raw_cases, start=1)
    )
    dataset_hash = _dataset_hash(schema_version=schema_version, cases=cases)
    return Dataset(
        metadata=DatasetMetadata(
            dataset_id=dataset_id,
            schema_version=schema_version,
            case_count=len(cases),
            dataset_hash=dataset_hash,
            source_path=source_path,
        ),
        cases=cases,
    )


def _load_jsonl_text(text: str, path: Path) -> tuple[str, str, list[dict[str, Any]]]:
    raw_cases: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            raw = json.loads(stripped, object_pairs_hook=_reject_duplicate_json_keys)
        except (json.JSONDecodeError, _DuplicateJsonKeyError) as exc:
            raise DatasetValidationError(
                case_id=f"line {line_number}",
                field="json",
                message=f"Dataset line {line_number} is not valid JSON: {exc}",
            ) from exc
        if not isinstance(raw, dict):
            raise DatasetValidationError(
                case_id=f"line {line_number}",
                field="case",
                message=f"Dataset line {line_number} must be a JSON object",
            )
        raw_cases.append(raw)
    return path.stem, DEFAULT_SCHEMA_VERSION, raw_cases


def _load_yaml_text(text: str, path: Path) -> tuple[str, str, list[dict[str, Any]]]:
    try:
        raw = yaml.load(text, Loader=_UniqueKeySafeLoader)
    except yaml.YAMLError as exc:
        raise DatasetValidationError(
            case_id=None,
            field="yaml",
            message=f"Dataset {path} is not valid YAML: {exc}",
        ) from exc

    if isinstance(raw, list):
        return path.stem, DEFAULT_SCHEMA_VERSION, _validate_raw_case_list(raw)

    if not isinstance(raw, dict):
        raise DatasetValidationError(
            case_id=None,
            field="dataset",
            message="YAML dataset must be an object with a 'cases' list or a list of cases",
        )

    unknown_fields = sorted(set(raw) - ALLOWED_YAML_DATASET_FIELDS)
    if unknown_fields:
        raise DatasetValidationError(
            case_id=None,
            field="dataset",
            message="YAML dataset contains unknown fields: " + ", ".join(unknown_fields),
        )

    raw_cases = raw.get("cases")
    if not isinstance(raw_cases, list):
        raise DatasetValidationError(
            case_id=None,
            field="cases",
            message="YAML dataset field 'cases' must be a list",
        )

    dataset_id = _string_or_none(raw.get("dataset_id")) or path.stem
    schema_version = _string_or_none(raw.get("schema_version")) or DEFAULT_SCHEMA_VERSION
    return dataset_id, schema_version, _validate_raw_case_list(raw_cases)


def _validate_raw_case_list(raw_cases: list[Any]) -> list[dict[str, Any]]:
    normalized_cases: list[dict[str, Any]] = []
    for index, raw_case in enumerate(raw_cases, start=1):
        if not isinstance(raw_case, dict):
            raise DatasetValidationError(
                case_id=f"case {index}",
                field="case",
                message=f"Dataset case {index} must be an object",
            )
        normalized_cases.append(raw_case)
    return normalized_cases


def _dataset_hash(*, schema_version: str, cases: tuple[DatasetCase, ...]) -> str:
    canonical = {
        "schema_version": schema_version,
        "cases": [case.to_canonical_mapping() for case in cases],
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _string_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key, value in pairs:
        if key in mapping:
            raise _DuplicateJsonKeyError(f"duplicate key {key!r}")
        mapping[key] = value
    return mapping
