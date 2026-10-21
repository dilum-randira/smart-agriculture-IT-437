"""Original-unit HTTP contract; no labels or future observations are inputs."""
from datetime import datetime, timedelta
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from ..preprocessing.pipeline import NUMERIC

ModelID = Literal['lstm', 'gru', 'attention_bilstm']
NodeID = Literal['NODE_01', 'NODE_02']
FiniteNumber = Annotated[float, Field(strict=True, allow_inf_nan=False)]
LOCAL_ZONE = ZoneInfo('Asia/Colombo')


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, hide_input_in_errors=True)


class HistoricalObservation(Contract):
    timestamp: AwareDatetime
    soil_moisture_avg_index: Annotated[FiniteNumber, Field(ge=0)]
    air_temperature_c: FiniteNumber
    relative_humidity_pct: Annotated[FiniteNumber, Field(ge=0, le=100)]
    record_status: Literal['OK', 'WARN', 'INVALID'] = 'OK'
    is_anomaly: Annotated[bool, Field(strict=True)] = False
    is_imputed: Annotated[bool, Field(strict=True)] = False
    imputed_fields: str = Field(default='', max_length=1024)
    quality_score: Annotated[FiniteNumber, Field(ge=0, le=1)] | None = None

    @field_validator('timestamp', mode='before')
    @classmethod
    def explicit_iso_timestamp(cls, value):
        if not isinstance(value, (str, datetime)):
            raise ValueError('Use a timezone-aware ISO 8601 timestamp')
        return value

    @field_validator('timestamp')
    @classmethod
    def hourly_local_timestamp(cls, value):
        value = value.astimezone(LOCAL_ZONE)
        if value.minute or value.second or value.microsecond:
            raise ValueError('Timestamps must be whole hours in Asia/Colombo (UTC+05:30)')
        return value

    @field_validator('imputed_fields', mode='before')
    @classmethod
    def empty_imputation_metadata(cls, value):
        return '' if value is None else value

    @field_validator('imputed_fields')
    @classmethod
    def trim_imputation_metadata(cls, value):
        return value.strip()

    @model_validator(mode='after')
    def consistent_quality(self):
        if bool(self.imputed_fields) != self.is_imputed:
            raise ValueError('is_imputed and nonempty imputed_fields must agree')
        if self.imputed_fields and set(self.imputed_fields.split(',')) - set(NUMERIC):
            raise ValueError('imputed_fields contains an unsupported source feature')
        if (self.is_anomaly or self.is_imputed) and self.record_status == 'OK':
            raise ValueError('Anomalous or supplied-imputed observations must be WARN or INVALID')
        return self


class ForecastRequest(Contract):
    model: ModelID
    node_id: NodeID
    observations: list[HistoricalObservation] = Field(min_length=336, max_length=336)
    forecast_origin: AwareDatetime | None = None
    data_origin: Literal['synthetic', 'user_supplied_unverified'] = 'user_supplied_unverified'

    @model_validator(mode='after')
    def consecutive_history(self):
        times = [observation.timestamp for observation in self.observations]
        if any(b-a != timedelta(hours=1) for a,b in zip(times,times[1:])):
            raise ValueError('Provide 336 unique, ordered, consecutive hourly observations; gaps and reordering are unsupported')
        if self.forecast_origin is not None and self.forecast_origin != times[-1]:
            raise ValueError('forecast_origin must equal the final historical timestamp; no forecast-period observations are accepted')
        try:
            times[-1] + timedelta(hours=168)
        except OverflowError as exc:
            raise ValueError('Timestamp range must accommodate all 168 forecast hours') from exc
        return self


class ForecastStep(Contract):
    lead_hour: int = Field(ge=1, le=168)
    timestamp: AwareDatetime
    soil_moisture_avg_index: FiniteNumber
    air_temperature_c: FiniteNumber
    relative_humidity_pct: FiniteNumber


class ForecastSlice(Contract):
    hours: Literal[24, 72, 168]
    start_index: Literal[0] = 0
    end_index_exclusive: int
    first_timestamp: AwareDatetime
    last_timestamp: AwareDatetime


class HistorySummary(Contract):
    start: AwareDatetime
    end: AwareDatetime
    observations: Literal[336] = 336
    timezone: str = 'Asia/Colombo (UTC+05:30)'
    eligible_under_declared_quality: int
    causally_filled_rows: int
    history_valid_mask: list[bool] = Field(min_length=336, max_length=336)
    quality_metadata_rows: int
    quality_policy: str


class Provenance(Contract):
    model_artifact_id: str
    checkpoint_sha256: str
    scaler_artifact_id: str
    scaler_sha256: str
    training_data: str
    scaler_fit_policy: str
    inference_mode: str
    declared_input_origin: str
    limitations: list[str]


class ForecastResponse(Contract):
    model: ModelID
    node_id: NodeID
    history: HistorySummary
    forecast_origin: AwareDatetime
    forecast_hours: Literal[168] = 168
    feature_order: list[str]
    target_order: list[str]
    units: dict[str, str]
    predictions: list[ForecastStep] = Field(min_length=168, max_length=168)
    slices: list[ForecastSlice] = Field(min_length=3, max_length=3)
    provenance: Provenance
    evaluation_label: str


class DemoInput(Contract):
    request: ForecastRequest
    demo: dict[str, str | int | bool]
    evaluation_label: str
