from __future__ import annotations

from pydantic import BaseModel, Field


class InfoRequest(BaseModel):
    url: str = Field(..., min_length=1)


class JobCreateRequest(BaseModel):
    url: str = Field(..., min_length=1)
    format_id: str = Field(default="bestvideo+bestaudio/best")
    output_type: str = Field(default="video")
    preset_key: str | None = Field(
        default=None,
        description="Optional: best | p1080 | p720 | audio — server maps to format_id",
    )
