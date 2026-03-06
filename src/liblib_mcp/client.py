from __future__ import annotations

import base64
import copy
import hashlib
import hmac
import mimetypes
import os
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import httpx

from .config import Settings
from .models import GenerationStatusResult, MediaArtifact, UploadResult, output_child


WEBUI_STATUS_ENDPOINT = "/api/generate/webui/status"
STANDARD_STATUS_ENDPOINT = "/api/generate/status"
COMFY_STATUS_ENDPOINT = "/api/generate/comfy/status"

STAR3_TEXT_TEMPLATE = "5d7e67009b344550bc1aa6ccbfa1d7f4"
STAR3_IMAGE_TEMPLATE = "07e00af4fc464c7ab55ff906f8acf1b7"
QWEN_TEMPLATE = "bf085132c7134622895b783b520b39ff"
QWEN_CHECKPOINT = "75e0be0c93b34dd8baeec9c968013e0c"
KONTEXT_TEXT_TEMPLATE = "fe9928fde1b4491c9b360dd24aa2b115"
KONTEXT_IMAGE_TEMPLATE = "1c0a9712b3d84e1b8a9f49514a46d88c"
IMG1_TEMPLATE = "86c58ea26e9a45bd9f562c6306c17c0f"
IMG1_INPAINT_TEMPLATE = "0fb3ddb15a094e74b1241fbda5db3199"
LIBDREAM_TEMPLATE = "aa835a39c1a14cfca47c6fc941137c51"
LIBEDIT_TEMPLATE = "cd3a6751086b4483ba5f0523aef53a79"
KLING_TEXT_TEMPLATE = "61cd8b60d340404394f2a545eeaf197a"
KLING_IMAGE_TEMPLATE = "180f33c6748041b48593030156d2a71d"
KLING_MULTI_TEMPLATE = "ca01e798b4424587b0dfdb98b089da05"
KLING_OMNI_TEMPLATE = "9f3a7c4e8b2d4f1a9c6e5d7b0a2e4c81"

UPLOADABLE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
    "mp4",
    "mov",
    "webm",
}


class LiblibApiError(RuntimeError):
    pass


class LiblibClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.http = httpx.AsyncClient(
            base_url=settings.base_url,
            timeout=settings.request_timeout_seconds,
            follow_redirects=True,
        )

    async def aclose(self) -> None:
        await self.http.aclose()

    def _signature_query(self, endpoint: str) -> dict[str, str]:
        timestamp = str(int(time.time() * 1000))
        nonce = uuid.uuid4().hex
        content = "&".join((endpoint, timestamp, nonce))
        digest = hmac.new(
            self.settings.secret_key.encode("utf-8"),
            content.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        signature = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")
        return {
            "AccessKey": self.settings.access_key,
            "Signature": signature,
            "Timestamp": timestamp,
            "SignatureNonce": nonce,
        }

    async def _post_json(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self.http.post(
            endpoint,
            params=self._signature_query(endpoint),
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            raise LiblibApiError(f"{endpoint} failed: code={data.get('code')} msg={data.get('msg')}")
        return data

    async def submit_generation(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post_json(endpoint, payload)

    async def get_status(self, endpoint: str, generate_uuid: str) -> GenerationStatusResult:
        raw = await self._post_json(endpoint, {"generateUuid": generate_uuid})
        data = raw.get("data") or {}
        images = [
            MediaArtifact(
                kind="image",
                remote_url=item["imageUrl"],
                audit_status=item.get("auditStatus"),
                seed=item.get("seed"),
            )
            for item in data.get("images", [])
            if item.get("imageUrl")
        ]
        videos = [
            MediaArtifact(
                kind="video",
                remote_url=item["videoUrl"],
                cover_url=item.get("coverPath"),
                audit_status=item.get("auditStatus"),
            )
            for item in data.get("videos", [])
            if item.get("videoUrl")
        ]
        return GenerationStatusResult(
            status_endpoint=endpoint,
            code=raw.get("code", -1),
            msg=raw.get("msg", ""),
            generate_uuid=data.get("generateUuid"),
            generate_status=data.get("generateStatus"),
            generate_msg=data.get("generateMsg"),
            percent_completed=data.get("percentCompleted"),
            points_cost=data.get("pointsCost"),
            account_balance=data.get("accountBalance"),
            images=images,
            videos=videos,
            raw=raw,
        )

    async def create_upload_signature(self, file_name: str, extension: str) -> dict[str, Any]:
        return await self._post_json(
            "/api/generate/upload/signature",
            {"name": file_name, "extension": extension},
        )

    async def upload_file(
        self,
        local_path: str,
        copy_to_output: bool = False,
        output_subdir: str = "uploads",
    ) -> UploadResult:
        path = Path(local_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Local file not found: {path}")

        extension = path.suffix.lstrip(".").lower()
        if extension not in UPLOADABLE_EXTENSIONS:
            raise ValueError(f"Unsupported file extension: .{extension}")

        signature_raw = await self.create_upload_signature(path.stem, extension)
        signature = signature_raw["data"]
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

        with path.open("rb") as file_handle:
            files = [
                ("key", (None, signature["key"])),
                ("policy", (None, signature["policy"])),
                ("x-oss-date", (None, str(signature["xOssDate"]))),
                ("x-oss-expires", (None, str(signature["xOssExpires"]))),
                ("x-oss-signature", (None, signature["xOssSignature"])),
                ("x-oss-credential", (None, signature["xOssCredential"])),
                ("x-oss-signature-version", (None, signature["xOssSignatureVersion"])),
                ("file", (path.name, file_handle, mime_type)),
            ]
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as upload_http:
                response = await upload_http.post(signature["postUrl"], files=files)
                response.raise_for_status()

        online_url = f"{signature['postUrl'].rstrip('/')}/{signature['key'].lstrip('/')}"
        mirrored_path: str | None = None

        if copy_to_output:
            target = output_child(self.settings.output_dir, output_subdir, path.name)
            target.write_bytes(path.read_bytes())
            mirrored_path = str(target)

        return UploadResult(
            key=signature["key"],
            postUrl=signature["postUrl"],
            online_url=online_url,
            local_path=mirrored_path,
            signature=signature,
        )

    async def resolve_media_inputs(self, payload: dict[str, Any]) -> tuple[dict[str, Any], list[UploadResult]]:
        copied = copy.deepcopy(payload)
        uploads: list[UploadResult] = []

        async def maybe_upload(value: Any, key: str | None = None) -> Any:
            if isinstance(value, str) and key in {
                "sourceImage",
                "controlImage",
                "maskImage",
                "image_url",
                "video_url",
                "image",
                "imageUrl",
                "startFrame",
                "endFrame",
            }:
                if self._is_url(value):
                    return value
                upload = await self.upload_file(value)
                uploads.append(upload)
                return upload.online_url

            if isinstance(value, list) and key in {"referenceImages", "image_list", "input_images"}:
                result = []
                for item in value:
                    if isinstance(item, str) and not self._is_url(item):
                        upload = await self.upload_file(item)
                        uploads.append(upload)
                        result.append(upload.online_url)
                    else:
                        result.append(item)
                return result

            if isinstance(value, list):
                return [await maybe_upload(item) for item in value]

            if isinstance(value, dict):
                resolved: dict[str, Any] = {}
                for child_key, child_value in value.items():
                    resolved[child_key] = await maybe_upload(child_value, child_key)
                return resolved

            return value

        resolved = await maybe_upload(copied)
        return resolved, uploads

    async def wait_for_result(
        self,
        generate_uuid: str,
        status_endpoint: str,
        poll_interval_seconds: float | None = None,
        timeout_seconds: float | None = None,
        download_results: bool | None = None,
    ) -> GenerationStatusResult:
        poll_interval = poll_interval_seconds or self.settings.default_poll_interval_seconds
        timeout = timeout_seconds or self.settings.default_poll_timeout_seconds
        should_download = (
            self.settings.auto_download_results if download_results is None else download_results
        )

        start = time.monotonic()
        while time.monotonic() - start <= timeout:
            status = await self.get_status(status_endpoint, generate_uuid)
            if status.generate_status in {5, 6, 7}:
                if should_download and status.generate_status == 5:
                    await self.download_status_media(status)
                return status
            await self._sleep(poll_interval)

        raise TimeoutError(f"Timed out waiting for generation result: {generate_uuid}")

    async def download_status_media(self, status: GenerationStatusResult) -> GenerationStatusResult:
        if not status.generate_uuid:
            return status

        for index, artifact in enumerate(status.images):
            artifact.local_path = await self._download_remote_file(
                artifact.remote_url,
                output_child(
                    self.settings.output_dir,
                    status.generate_uuid,
                    "images",
                    f"{index}_{self._file_name_from_url(artifact.remote_url)}",
                ),
            )

        for index, artifact in enumerate(status.videos):
            artifact.local_path = await self._download_remote_file(
                artifact.remote_url,
                output_child(
                    self.settings.output_dir,
                    status.generate_uuid,
                    "videos",
                    f"{index}_{self._file_name_from_url(artifact.remote_url)}",
                ),
            )
            if artifact.cover_url:
                artifact.cover_local_path = await self._download_remote_file(
                    artifact.cover_url,
                    output_child(
                        self.settings.output_dir,
                        status.generate_uuid,
                        "covers",
                        f"{index}_{self._file_name_from_url(artifact.cover_url)}",
                    ),
                )

        return status

    async def _download_remote_file(self, remote_url: str, target_path: Path) -> str:
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as download_http:
            response = await download_http.get(remote_url)
            response.raise_for_status()
            target_path.write_bytes(response.content)
        return str(target_path)

    @staticmethod
    def _is_url(value: str) -> bool:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    @staticmethod
    def _file_name_from_url(remote_url: str) -> str:
        path = urlparse(remote_url).path
        name = os.path.basename(path)
        if not name:
            name = quote(remote_url, safe="").replace("%", "_")
        return name

    @staticmethod
    async def _sleep(seconds: float) -> None:
        import asyncio

        await asyncio.sleep(seconds)
