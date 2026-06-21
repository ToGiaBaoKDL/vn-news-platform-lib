from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

ICEBERG_TRANSFORM_BY_CONTRACT_TRANSFORM = {
    "bucket": "bucket",
    "day": "day",
    "days": "day",
    "hour": "hour",
    "hours": "hour",
    "identity": "identity",
    "month": "month",
    "months": "month",
    "truncate": "truncate",
    "year": "year",
    "years": "year",
}

ICEBERG_DEFAULT_PROPERTIES: Mapping[str, str] = {
    "write.format.default": "parquet",
    "write.parquet.compression-codec": "zstd",
    "write.target-file-size-bytes": "134217728",
    "commit.retry.num-retries": "4",
}

PARTITION_EXPRESSION_RE = re.compile(
    r"^(?P<transform>[A-Za-z][A-Za-z0-9_]*)\((?P<field>[A-Za-z_][A-Za-z0-9_]*)\)$"
)


@dataclass(frozen=True)
class TableField:
    name: str
    data_type: str
    required: bool = False
    description: str = ""


@dataclass(frozen=True)
class TablePartition:
    transform: str
    field_name: str

    @property
    def name(self) -> str:
        if self.transform == "identity":
            return self.field_name
        return f"{self.field_name}_{self.transform}"


@dataclass(frozen=True)
class IcebergTableContract:
    namespace: str
    name: str
    fields: tuple[TableField, ...]
    key_fields: tuple[str, ...]
    partition_by: tuple[str, ...] = ()
    properties: Mapping[str, str] = field(default_factory=lambda: ICEBERG_DEFAULT_PROPERTIES)

    @property
    def identifier(self) -> str:
        return f"{self.namespace}.{self.name}"

    @property
    def required_fields(self) -> tuple[str, ...]:
        return tuple(field.name for field in self.fields if field.required)

    def field_names(self) -> tuple[str, ...]:
        return tuple(field.name for field in self.fields)

    def partition_fields(self) -> tuple[TablePartition, ...]:
        return tuple(parse_partition_expression(expression) for expression in self.partition_by)

    def validate(self) -> None:
        field_names = self.field_names()
        if len(field_names) != len(set(field_names)):
            raise ValueError(f"{self.identifier} has duplicate fields")
        missing_keys = sorted(set(self.key_fields) - set(field_names))
        if missing_keys:
            raise ValueError(f"{self.identifier} keys are missing from fields: {missing_keys}")
        missing_required_keys = sorted(set(self.key_fields) - set(self.required_fields))
        if missing_required_keys:
            raise ValueError(
                f"{self.identifier} keys must be required fields: {missing_required_keys}"
            )
        missing_partition_fields = sorted(
            {partition.field_name for partition in self.partition_fields()} - set(field_names)
        )
        if missing_partition_fields:
            raise ValueError(
                f"{self.identifier} partitions are missing from fields: {missing_partition_fields}"
            )

    def validate_row(self, row: Mapping[str, object]) -> None:
        expected_fields = set(self.field_names())
        actual_fields = set(row)
        missing_fields = sorted(expected_fields - actual_fields)
        extra_fields = sorted(actual_fields - expected_fields)
        if missing_fields or extra_fields:
            raise ValueError(
                f"{self.identifier} row fields do not match contract: "
                f"missing={missing_fields}, extra={extra_fields}"
            )

        empty_required_fields = [
            field_name
            for field_name in self.required_fields
            if is_empty_required_value(row[field_name])
        ]
        if empty_required_fields:
            raise ValueError(
                f"{self.identifier} row has empty required fields: {empty_required_fields}"
            )


def is_empty_required_value(value: object) -> bool:
    if value is None:
        return True
    return isinstance(value, str) and not value.strip()


def parse_partition_expression(expression: str) -> TablePartition:
    match = PARTITION_EXPRESSION_RE.fullmatch(expression)
    if not match:
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expression):
            return TablePartition(transform="identity", field_name=expression)
        raise ValueError(f"Unsupported partition expression: {expression}")

    transform = match.group("transform").lower()
    try:
        iceberg_transform = ICEBERG_TRANSFORM_BY_CONTRACT_TRANSFORM[transform]
    except KeyError as error:
        raise ValueError(f"Unsupported partition transform: {transform}") from error
    return TablePartition(transform=iceberg_transform, field_name=match.group("field"))


NEWS_ARTICLE_VERSION = IcebergTableContract(
    namespace="curated",
    name="news_article_version",
    key_fields=("article_id", "source_document_id", "content_hash"),
    partition_by=("days(ingest_date)",),
    fields=(
        TableField("article_id", "string", required=True),
        TableField("source_id", "string", required=True),
        TableField("source_document_id", "string", required=True),
        TableField("requested_url", "string", required=True),
        TableField("canonical_url", "string", required=True),
        TableField("title", "string", required=True),
        TableField("summary", "string"),
        TableField("body_text", "string", required=True),
        TableField("author", "string"),
        TableField("published_at", "timestamp"),
        TableField("language", "string", required=True),
        TableField("content_hash", "string", required=True),
        TableField("extraction_status", "string", required=True),
        TableField("run_id", "string", required=True),
        TableField("ingest_date", "date", required=True),
        TableField("event_id", "string", required=True),
        TableField("event_time", "timestamp", required=True),
        TableField("source_payload_uri", "string", required=True),
        TableField("extracted_payload_uri", "string"),
        TableField("extractor_version", "string", required=True),
        TableField("created_at", "timestamp", required=True),
    ),
)

NEWS_ARTICLE = IcebergTableContract(
    namespace="curated",
    name="news_article",
    key_fields=("article_id",),
    partition_by=("days(ingest_date)",),
    fields=(
        TableField("article_id", "string", required=True),
        TableField("source_id", "string", required=True),
        TableField("canonical_url", "string", required=True),
        TableField("title", "string", required=True),
        TableField("summary", "string"),
        TableField("author", "string"),
        TableField("published_at", "timestamp"),
        TableField("language", "string", required=True),
        TableField("latest_source_document_id", "string", required=True),
        TableField("latest_content_hash", "string", required=True),
        TableField("latest_event_id", "string", required=True),
        TableField("latest_event_time", "timestamp", required=True),
        TableField("ingest_date", "date", required=True),
        TableField("updated_at", "timestamp", required=True),
        TableField("created_at", "timestamp", required=True),
    ),
)

PIPELINE_RUN_AUDIT = IcebergTableContract(
    namespace="curated",
    name="pipeline_run_audit",
    key_fields=("job_name", "run_id"),
    fields=(
        TableField("job_name", "string", required=True),
        TableField("run_id", "string", required=True),
        TableField("started_at", "timestamp", required=True),
        TableField("finished_at", "timestamp"),
        TableField("status", "string", required=True),
        TableField("input_topic", "string", required=True),
        TableField("input_start_offsets", "string", required=True),
        TableField("input_end_offsets", "string", required=True),
        TableField("input_records", "long", required=True),
        TableField("valid_records", "long", required=True),
        TableField("invalid_records", "long", required=True),
        TableField("inserted_versions", "long", required=True),
        TableField("updated_articles", "long", required=True),
        TableField("error_count", "long", required=True),
    ),
)

PIPELINE_ERROR = IcebergTableContract(
    namespace="curated",
    name="pipeline_error",
    key_fields=("error_id",),
    partition_by=("days(ingest_date)",),
    fields=(
        TableField("error_id", "string", required=True),
        TableField("job_name", "string", required=True),
        TableField("run_id", "string", required=True),
        TableField("input_topic", "string", required=True),
        TableField("source_partition", "int"),
        TableField("source_offset", "long"),
        TableField("event_id", "string"),
        TableField("source_id", "string"),
        TableField("article_id", "string"),
        TableField("error_class", "string", required=True),
        TableField("error_message", "string", required=True),
        TableField("raw_event_json", "string", required=True),
        TableField("ingest_date", "date", required=True),
        TableField("created_at", "timestamp", required=True),
    ),
)

CURATED_TABLE_CONTRACTS: tuple[IcebergTableContract, ...] = (
    NEWS_ARTICLE_VERSION,
    NEWS_ARTICLE,
    PIPELINE_RUN_AUDIT,
    PIPELINE_ERROR,
)

TABLE_CONTRACTS: Mapping[str, IcebergTableContract] = {
    contract.identifier: contract for contract in CURATED_TABLE_CONTRACTS
}


def get_table_contract(identifier: str) -> IcebergTableContract:
    try:
        return TABLE_CONTRACTS[identifier]
    except KeyError as error:
        raise KeyError(f"Unknown table contract: {identifier}") from error


for contract in CURATED_TABLE_CONTRACTS:
    contract.validate()
