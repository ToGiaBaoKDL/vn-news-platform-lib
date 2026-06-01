from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from typing import Any

import yaml


@dataclass(frozen=True)
class TableSpec:
    namespace: str
    name: str
    bucket: str
    partitioning: list[str]
    fields: dict[str, str]

    @property
    def qualified_name(self) -> str:
        return f"{self.namespace}.{self.name}"


def load_table_specs(spec_dir: Any | None = None) -> list[TableSpec]:
    table_dir = spec_dir or files("news_platform.contracts").joinpath("table_specs")
    tables: list[TableSpec] = []
    for path in sorted(table_dir.iterdir(), key=lambda item: item.name):
        if not path.name.endswith(".yaml"):
            continue
        spec = load_yaml(path)
        namespace = spec["namespace"]
        bucket = spec["bucket"]
        for table_name, table in spec["tables"].items():
            tables.append(
                TableSpec(
                    namespace=namespace,
                    name=table_name,
                    bucket=bucket,
                    partitioning=table.get("partitioning", []),
                    fields=flatten_fields(table["fields"]),
                )
            )
    return tables


def load_yaml(path: Any) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        msg = f"Expected YAML mapping in {path}"
        raise ValueError(msg)
    return data


def flatten_fields(fields: list[dict[str, str]]) -> dict[str, str]:
    flattened: dict[str, str] = {}
    for field in fields:
        duplicate_fields = set(flattened).intersection(field)
        if duplicate_fields:
            msg = f"Duplicate table fields: {sorted(duplicate_fields)}"
            raise ValueError(msg)
        flattened.update(field)
    return flattened
