from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

Role = Literal['admin', 'researcher', 'viewer']


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', hide_input_in_errors=True, allow_inf_nan=False, str_strip_whitespace=True)


class Login(Contract):
    username: str = Field(min_length=3, max_length=64, pattern=r'^[a-zA-Z0-9_.-]+$')
    password: SecretStr = Field(min_length=1, max_length=128)


class NewUser(Login):
    password: SecretStr = Field(min_length=12, max_length=128)
    role: Role


class Register(Login):
    """Public registration cannot accept a privileged role or farm membership."""
    password: SecretStr = Field(min_length=12, max_length=128)


class UserUpdate(Contract):
    role: Role
    active: bool = Field(strict=True)


class FarmWrite(Contract):
    farm_name: str = Field(min_length=2, max_length=100)
    district: str = Field(min_length=2, max_length=80)
    latitude: float | None = Field(default=None, ge=-90, le=90, strict=True)
    longitude: float | None = Field(default=None, ge=-180, le=180, strict=True)
    timezone: str = Field(default='Asia/Colombo', max_length=64)
    crop_type: str = Field(min_length=2, max_length=80)
    growth_stage: str | None = Field(default=None, min_length=2, max_length=80)

    @field_validator('timezone')
    @classmethod
    def valid_zone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError('Use a valid IANA timezone') from exc
        return value

    @model_validator(mode='after')
    def coordinate_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError('Supply both coordinates or neither')
        return self


class NewFarm(FarmWrite):
    is_demo: bool = Field(default=False, strict=True)


class SiteWrite(Contract):
    site_name: str = Field(min_length=2, max_length=100)


class NodeWrite(Contract):
    node_id: str = Field(min_length=3, max_length=40, pattern=r'^[A-Za-z0-9_-]+$')
    sensor_metadata: str = Field(default='Not supplied', max_length=500)
    calibration_reference: str | None = Field(default=None, max_length=200)


class Assignment(Contract):
    site_id: str = Field(min_length=1, max_length=64)


class Membership(Contract):
    granted: bool = Field(strict=True)


class ForecastSelection(Assignment):
    node_id: str = Field(min_length=3, max_length=40)
    model: Literal['lstm', 'gru', 'attention_bilstm'] = 'attention_bilstm'
