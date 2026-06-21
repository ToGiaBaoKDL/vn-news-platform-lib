from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from news_platform.contracts.tables import IcebergTableContract, get_table_contract


class SparkJobDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    driver_memory: str = Field(pattern=r"^[1-9][0-9]*[kmgt]$")
    executor_memory: str = Field(pattern=r"^[1-9][0-9]*[kmgt]$")
    executor_cores: int = Field(ge=1)
    total_executor_cores: int = Field(ge=1)
    shuffle_partitions: int = Field(ge=1)

    @property
    def session_options(self) -> tuple[tuple[str, str], ...]:
        return (("spark.sql.shuffle.partitions", str(self.shuffle_partitions)),)

    @model_validator(mode="after")
    def validate_executor_cores(self) -> Self:
        if self.total_executor_cores % self.executor_cores:
            raise ValueError("spark.total_executor_cores must be divisible by executor_cores")
        return self


class PipelineOutputDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: str = Field(min_length=1)
    table: str = Field(min_length=1)
    dedupe_order_fields: tuple[str, ...] = ()

    @property
    def contract(self) -> IcebergTableContract:
        return get_table_contract(self.table)

    @model_validator(mode="after")
    def validate_contract_fields(self) -> Self:
        try:
            field_names = set(self.contract.field_names())
        except KeyError as error:
            raise ValueError(str(error)) from error
        unknown_order_fields = set(self.dedupe_order_fields) - field_names
        if unknown_order_fields:
            raise ValueError(
                f"{self.table} has unknown dedupe order fields: {sorted(unknown_order_fields)}"
            )
        return self


class PipelineJobDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal[1]
    name: str = Field(min_length=1)
    input_topic_key: str = Field(min_length=1)
    checkpoint_name: str = Field(min_length=1)
    spark: SparkJobDefinition | None = None
    outputs: dict[str, PipelineOutputDefinition]
    audit_table: str = Field(min_length=1)

    @property
    def audit_contract(self) -> IcebergTableContract:
        return get_table_contract(self.audit_table)

    @property
    def output_kinds(self) -> frozenset[str]:
        return frozenset(output.kind for output in self.outputs.values())

    def output(self, name: str) -> PipelineOutputDefinition:
        try:
            return self.outputs[name]
        except KeyError as error:
            raise KeyError(f"Pipeline {self.name!r} has no output {name!r}") from error

    @model_validator(mode="after")
    def validate_definition(self) -> Self:
        if not self.outputs:
            raise ValueError("pipeline outputs must not be empty")
        if len(self.output_kinds) != len(self.outputs):
            raise ValueError("pipeline output kinds must be unique")
        try:
            get_table_contract(self.audit_table)
        except KeyError as error:
            raise ValueError(str(error)) from error
        return self
