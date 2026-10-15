from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    start_year: int = Field(ge=1940, strict=True)
    end_year: int = Field(ge=1940, strict=True)
    hazard: Literal["heatwave"] = "heatwave"

    @model_validator(mode="after")
    def validate_years(self):
        latest = datetime.now(timezone.utc).year - 1
        if self.start_year > self.end_year:
            raise ValueError("Start year must not exceed end year.")
        if self.end_year > latest:
            raise ValueError(f"Use complete calendar years through {latest}.")
        return self
