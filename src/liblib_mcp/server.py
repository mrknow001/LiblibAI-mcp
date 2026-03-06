from __future__ import annotations

import contextlib
from typing import Any, Literal

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from .client import (
    IMG1_INPAINT_TEMPLATE,
    IMG1_TEMPLATE,
    KLING_IMAGE_TEMPLATE,
    KLING_MULTI_TEMPLATE,
    KLING_OMNI_TEMPLATE,
    KLING_TEXT_TEMPLATE,
    KONTEXT_IMAGE_TEMPLATE,
    KONTEXT_TEXT_TEMPLATE,
    LIBDREAM_TEMPLATE,
    LIBEDIT_TEMPLATE,
    QWEN_CHECKPOINT,
    QWEN_TEMPLATE,
    STANDARD_STATUS_ENDPOINT,
    STAR3_IMAGE_TEMPLATE,
    STAR3_TEXT_TEMPLATE,
    WEBUI_STATUS_ENDPOINT,
    LiblibClient,
)
from .config import Settings
from .models import GenerationSubmission

settings = Settings.from_env()
client = LiblibClient(settings)

mcp = FastMCP(
    "LiblibAI MCP Server",
    instructions=(
        "LiblibAI image and video generation server. "
        "Use upload_file for local assets, submit generation tools, then poll_generation "
        "to wait for results and download generated files to the mounted output directory."
    ),
    stateless_http=True,
    json_response=True,
)


def _submission(
    endpoint: str,
    status_endpoint: str,
    template_uuid: str,
    payload: dict[str, Any],
    response: dict[str, Any],
    uploads: list[Any],
) -> GenerationSubmission:
    data = response.get("data") or {}
    return GenerationSubmission(
        endpoint=endpoint,
        status_endpoint=status_endpoint,
        template_uuid=template_uuid,
        generate_uuid=data["generateUuid"],
        request_body=payload,
        uploaded_inputs=uploads,
    )


async def _submit(
    endpoint: str,
    status_endpoint: str,
    template_uuid: str,
    generate_params: dict[str, Any],
) -> GenerationSubmission:
    payload = {"templateUuid": template_uuid, "generateParams": generate_params}
    resolved_payload, uploads = await client.resolve_media_inputs(payload)
    response = await client.submit_generation(endpoint, resolved_payload)
    return _submission(endpoint, status_endpoint, template_uuid, resolved_payload, response, uploads)


@mcp.tool()
async def server_info() -> dict[str, Any]:
    """Return deployment and output-directory information."""
    return {
        "base_url": settings.base_url,
        "output_dir": str(settings.output_dir),
        "mcp_path": settings.mcp_path,
        "auto_download_results": settings.auto_download_results,
    }


@mcp.tool()
async def upload_file(local_path: str, copy_to_output: bool = False) -> dict[str, Any]:
    """Upload a local image or video to LiblibAI and return its online URL."""
    result = await client.upload_file(local_path, copy_to_output=copy_to_output)
    return result.model_dump(by_alias=True)


@mcp.tool()
async def submit_generation(
    endpoint: str,
    template_uuid: str,
    generate_params: dict[str, Any],
    status_endpoint: str = STANDARD_STATUS_ENDPOINT,
) -> dict[str, Any]:
    """Generic generation tool for any LiblibAI endpoint."""
    payload = {"templateUuid": template_uuid, "generateParams": generate_params}
    resolved_payload, uploads = await client.resolve_media_inputs(payload)
    response = await client.submit_generation(endpoint, resolved_payload)
    data = response.get("data") or {}
    return {
        "endpoint": endpoint,
        "status_endpoint": status_endpoint,
        "template_uuid": template_uuid,
        "generate_uuid": data.get("generateUuid"),
        "request_body": resolved_payload,
        "uploaded_inputs": [item.model_dump(by_alias=True) for item in uploads],
    }


@mcp.tool()
async def star3_text_to_image(
    prompt: str,
    aspect_ratio: Literal["square", "portrait", "landscape"] = "portrait",
    image_size: dict[str, int] | None = None,
    img_count: int = 1,
    steps: int = 30,
    prompt_magic: int | None = None,
    controlnet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Star-3 Alpha text-to-image with simplified defaults."""
    generate_params: dict[str, Any] = {
        "prompt": prompt,
        "imgCount": img_count,
        "steps": steps,
    }
    if image_size:
        generate_params["imageSize"] = image_size
    else:
        generate_params["aspectRatio"] = aspect_ratio
    if prompt_magic is not None:
        generate_params["promptMagic"] = prompt_magic
    if controlnet:
        generate_params["controlnet"] = controlnet
    submission = await _submit(
        "/api/generate/webui/text2img/ultra",
        WEBUI_STATUS_ENDPOINT,
        STAR3_TEXT_TEMPLATE,
        generate_params,
    )
    return submission.model_dump()


@mcp.tool()
async def star3_image_to_image(
    prompt: str,
    source_image: str,
    img_count: int = 1,
    controlnet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Star-3 Alpha image-to-image. Local source_image paths are uploaded automatically."""
    generate_params: dict[str, Any] = {
        "prompt": prompt,
        "sourceImage": source_image,
        "imgCount": img_count,
    }
    if controlnet:
        generate_params["controlnet"] = controlnet
    submission = await _submit(
        "/api/generate/webui/img2img/ultra",
        WEBUI_STATUS_ENDPOINT,
        STAR3_IMAGE_TEMPLATE,
        generate_params,
    )
    return submission.model_dump()


@mcp.tool()
async def qwen_text_to_image(
    prompt: str,
    negative_prompt: str | None = None,
    width: int = 1328,
    height: int = 1328,
    img_count: int = 1,
    clip_skip: int = 2,
    sampler: int = 1,
    steps: int = 30,
    cfg_scale: float = 4.0,
    randn_source: int = 0,
    seed: int = -1,
    additional_network: list[dict[str, Any]] | None = None,
    control_net: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Qwen Image text-to-image with documented defaults."""
    generate_params: dict[str, Any] = {
        "checkPointId": QWEN_CHECKPOINT,
        "prompt": prompt,
        "clipSkip": clip_skip,
        "sampler": sampler,
        "steps": steps,
        "cfgScale": cfg_scale,
        "width": width,
        "height": height,
        "imgCount": img_count,
        "randnSource": randn_source,
        "seed": seed,
    }
    if negative_prompt:
        generate_params["negativePrompt"] = negative_prompt
    if additional_network:
        generate_params["additionalNetwork"] = additional_network
    if control_net:
        generate_params["controlNet"] = control_net
    submission = await _submit(
        "/api/generate/webui/text2img",
        STANDARD_STATUS_ENDPOINT,
        QWEN_TEMPLATE,
        generate_params,
    )
    return submission.model_dump()


@mcp.tool()
async def kontext_text_to_image(
    prompt: str,
    model: Literal["pro", "max"] = "pro",
    aspect_ratio: str = "1:1",
    img_count: int = 1,
    guidance_scale: float = 3.5,
) -> dict[str, Any]:
    """F.1 Kontext text-to-image with minimal required/default parameters."""
    submission = await _submit(
        "/api/generate/kontext/text2img",
        STANDARD_STATUS_ENDPOINT,
        KONTEXT_TEXT_TEMPLATE,
        {
            "prompt": prompt,
            "model": model,
            "aspect_ratio": aspect_ratio,
            "imgCount": img_count,
            "guidance_scale": guidance_scale,
        },
    )
    return submission.model_dump()


@mcp.tool()
async def kontext_image_to_image(
    prompt: str,
    input_images: list[str],
    model: Literal["pro", "max"] = "pro",
    guidance_scale: float = 3.5,
) -> dict[str, Any]:
    """F.1 Kontext image editing / multi-image reference."""
    submission = await _submit(
        "/api/generate/kontext/img2img",
        STANDARD_STATUS_ENDPOINT,
        KONTEXT_IMAGE_TEMPLATE,
        {
            "prompt": prompt,
            "model": model,
            "input_images": input_images,
            "guidance_scale": guidance_scale,
        },
    )
    return submission.model_dump()


@mcp.tool()
async def img1_generate(
    prompt: str,
    image_list: list[str] | None = None,
    style: str | None = None,
    aspect_ratio: str = "1:1",
) -> dict[str, Any]:
    """IMG1 generation."""
    generate_params: dict[str, Any] = {"prompt": prompt, "aspect_ratio": aspect_ratio}
    if image_list:
        generate_params["image_list"] = image_list
    if style:
        generate_params["style"] = style
    submission = await _submit(
        "/api/generate/smart-img1/generate",
        STANDARD_STATUS_ENDPOINT,
        IMG1_TEMPLATE,
        generate_params,
    )
    return submission.model_dump()


@mcp.tool()
async def img1_inpaint(
    prompt: str,
    source_image: str,
    mask_image: str,
) -> dict[str, Any]:
    """IMG1 inpaint."""
    submission = await _submit(
        "/api/generate/smart-img1/inpaint",
        STANDARD_STATUS_ENDPOINT,
        IMG1_INPAINT_TEMPLATE,
        {
            "prompt": prompt,
            "sourceImage": source_image,
            "maskImage": mask_image,
        },
    )
    return submission.model_dump()


@mcp.tool()
async def libdream_text_to_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    img_count: int = 1,
    guidance_scale: float = 2.5,
    seed: int = -1,
) -> dict[str, Any]:
    """LibDream text-to-image with optional advanced params."""
    submission = await _submit(
        "/api/generate/libDream",
        STANDARD_STATUS_ENDPOINT,
        LIBDREAM_TEMPLATE,
        {
            "prompt": prompt,
            "aspectRatio": aspect_ratio,
            "imgCount": img_count,
            "guidanceScale": guidance_scale,
            "seed": seed,
        },
    )
    return submission.model_dump()


@mcp.tool()
async def libedit_image_edit(
    prompt: str,
    source_image: str,
    reference_images: list[str] | None = None,
) -> dict[str, Any]:
    """LibEdit instruction editing."""
    generate_params: dict[str, Any] = {
        "prompt": prompt,
        "sourceImage": source_image,
    }
    if reference_images:
        generate_params["referenceImages"] = reference_images
    submission = await _submit(
        "/api/generate/libEdit",
        STANDARD_STATUS_ENDPOINT,
        LIBEDIT_TEMPLATE,
        generate_params,
    )
    return submission.model_dump()


@mcp.tool()
async def kling_text_to_video(
    prompt: str,
    model: str = "kling-v2-1-master",
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = "16:9",
    duration: Literal["5", "10"] = "5",
    mode: Literal["std", "pro"] = "std",
    prompt_magic: int = 1,
    sound: Literal["on", "off"] | None = None,
) -> dict[str, Any]:
    """Kling text-to-video."""
    generate_params: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "promptMagic": prompt_magic,
        "aspectRatio": aspect_ratio,
        "duration": duration,
        "mode": mode,
    }
    if sound:
        generate_params["sound"] = sound
    submission = await _submit(
        "/api/generate/video/kling/text2video",
        STANDARD_STATUS_ENDPOINT,
        KLING_TEXT_TEMPLATE,
        generate_params,
    )
    return submission.model_dump()


@mcp.tool()
async def kling_image_to_video(
    prompt: str,
    image: str | None = None,
    start_frame: str | None = None,
    end_frame: str | None = None,
    model: str = "kling-v1-6",
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = "16:9",
    duration: Literal["5", "10"] = "5",
    mode: Literal["std", "pro"] = "std",
    prompt_magic: int = 1,
    sound: Literal["on", "off"] | None = None,
) -> dict[str, Any]:
    """Kling image-to-video. For kling-v2-6 use image; for kling-v1-6 you can use start_frame/end_frame."""
    generate_params: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "promptMagic": prompt_magic,
        "aspectRatio": aspect_ratio,
        "duration": duration,
        "mode": mode,
    }
    if image is not None:
        generate_params["image"] = image
    if start_frame is not None:
        generate_params["startFrame"] = start_frame
    if end_frame is not None:
        generate_params["endFrame"] = end_frame
    if sound is not None:
        generate_params["sound"] = sound
    submission = await _submit(
        "/api/generate/video/kling/img2video",
        STANDARD_STATUS_ENDPOINT,
        KLING_IMAGE_TEMPLATE,
        generate_params,
    )
    return submission.model_dump()


@mcp.tool()
async def kling_multi_image_to_video(
    prompt: str,
    reference_images: list[str],
    model: str = "kling-v1-6",
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = "16:9",
    duration: Literal["5", "10"] = "5",
    mode: Literal["std", "pro"] = "std",
    prompt_magic: int = 1,
) -> dict[str, Any]:
    """Kling multi-image reference video generation."""
    submission = await _submit(
        "/api/generate/video/kling/multiImg2video",
        STANDARD_STATUS_ENDPOINT,
        KLING_MULTI_TEMPLATE,
        {
            "model": model,
            "prompt": prompt,
            "promptMagic": prompt_magic,
            "referenceImages": reference_images,
            "aspectRatio": aspect_ratio,
            "duration": duration,
            "mode": mode,
        },
    )
    return submission.model_dump()


@mcp.tool()
async def kling_omni_video(
    prompt: str,
    images: list[dict[str, Any]] | None = None,
    videos: list[dict[str, Any]] | None = None,
    model: str = "kling-video-o1",
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = "16:9",
    duration: Literal["5", "10"] = "5",
    mode: Literal["pro", "std"] = "pro",
) -> dict[str, Any]:
    """Kling Omni-Video V1 for multimodal video generation and editing."""
    generate_params: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "aspectRatio": aspect_ratio,
        "duration": duration,
        "mode": mode,
    }
    if images:
        generate_params["images"] = images
    if videos:
        generate_params["videos"] = videos
    submission = await _submit(
        "/api/generate/video/kling/omni-video",
        STANDARD_STATUS_ENDPOINT,
        KLING_OMNI_TEMPLATE,
        generate_params,
    )
    return submission.model_dump()


@mcp.tool()
async def get_generation_status(
    generate_uuid: str,
    status_endpoint: str = STANDARD_STATUS_ENDPOINT,
    download_results: bool = False,
) -> dict[str, Any]:
    """Query generation status. Optionally download generated files to the mounted output dir."""
    status = await client.get_status(status_endpoint, generate_uuid)
    if download_results and status.generate_status == 5:
        await client.download_status_media(status)
    return status.model_dump()


@mcp.tool()
async def poll_generation(
    generate_uuid: str,
    status_endpoint: str = STANDARD_STATUS_ENDPOINT,
    poll_interval_seconds: float = 5.0,
    timeout_seconds: float = 900.0,
    download_results: bool = True,
) -> dict[str, Any]:
    """Wait for completion, then optionally download outputs while preserving remote URLs."""
    status = await client.wait_for_result(
        generate_uuid=generate_uuid,
        status_endpoint=status_endpoint,
        poll_interval_seconds=poll_interval_seconds,
        timeout_seconds=timeout_seconds,
        download_results=download_results,
    )
    return status.model_dump()


async def healthcheck(_: Any) -> JSONResponse:
    return JSONResponse({"ok": True, "mcp_path": settings.mcp_path})


@contextlib.asynccontextmanager
async def lifespan(_: Starlette):
    async with mcp.session_manager.run():
        yield
    await client.aclose()


app = Starlette(
    routes=[
        Route("/healthz", healthcheck),
        Mount("/", app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan,
)


def main() -> None:
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
