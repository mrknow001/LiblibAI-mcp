from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class UploadResult(BaseModel):
    key: str
    post_url: str = Field(alias="postUrl")
    online_url: str
    local_path: str | None = None
    signature: dict[str, Any]


class MediaArtifact(BaseModel):
    kind: str
    remote_url: str
    local_path: str | None = None
    audit_status: int | None = None
    seed: int | None = None
    cover_url: str | None = None
    cover_local_path: str | None = None


class GenerationSubmission(BaseModel):
    endpoint: str
    status_endpoint: str
    template_uuid: str
    generate_uuid: str
    request_body: dict[str, Any]
    uploaded_inputs: list[UploadResult] = Field(default_factory=list)


class GenerationStatusResult(BaseModel):
    status_endpoint: str
    code: int
    msg: str
    generate_uuid: str | None = None
    generate_status: int | None = None
    generate_msg: str | None = None
    percent_completed: float | None = None
    points_cost: int | None = None
    account_balance: int | None = None
    images: list[MediaArtifact] = Field(default_factory=list)
    videos: list[MediaArtifact] = Field(default_factory=list)
    raw: dict[str, Any]


class DownloadedFile(BaseModel):
    remote_url: str
    local_path: str


def output_child(output_dir: Path, *parts: str) -> Path:
    path = output_dir.joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
