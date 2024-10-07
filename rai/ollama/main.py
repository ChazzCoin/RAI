import asyncio
import json
import logging
import os
import random
import re
import time
from typing import Optional, Union
from urllib.parse import urlparse

import aiohttp
import requests
from rai.models.models import Models
# from rai.config import (
#     AIOHTTP_CLIENT_TIMEOUT,
#     ENABLE_MODEL_FILTER,
#     ENABLE_OLLAMA_API,
#     MODEL_FILTER_LIST,
#     OLLAMA_BASE_URLS,
#     UPLOAD_DIR,
# )
from rai.constants import ERROR_MESSAGES
from rai.env import SRC_LOG_LEVELS
from fastapi import File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from starlette.background import BackgroundTask


from rai.utils.misc import (
    calculate_sha256,
)
from rai.utils.payload import (
    apply_model_params_to_body_ollama,
    apply_model_params_to_body_openai,
    apply_model_system_prompt_to_body,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OLLAMA"])

from rai import app

class GenerateEmbeddingsForm(BaseModel):
    model: str
    prompt: str
    options: Optional[dict] = None
    keep_alive: Optional[Union[int, str]] = None

class GenerateEmbedForm(BaseModel):
    model: str
    input: str
    truncate: Optional[bool]
    options: Optional[dict] = None
    keep_alive: Optional[Union[int, str]] = None

class UrlUpdateForm(BaseModel):
    urls: list[str]

class ModelNameForm(BaseModel):
    name: str
class PushModelForm(BaseModel):
    name: str
    insecure: Optional[bool] = None
    stream: Optional[bool] = None

class CreateModelForm(BaseModel):
    name: str
    modelfile: Optional[str] = None
    stream: Optional[bool] = None
    path: Optional[str] = None
class CopyModelForm(BaseModel):
    source: str
    destination: str

class UrlForm(BaseModel):
    url: str

class UploadBlobForm(BaseModel):
    filename: str

class OllamaConfigForm(BaseModel):
    enable_ollama_api: Optional[bool] = None

class GenerateCompletionForm(BaseModel):
    model: str
    prompt: str
    images: Optional[list[str]] = None
    format: Optional[str] = None
    options: Optional[dict] = None
    system: Optional[str] = None
    template: Optional[str] = None
    context: Optional[str] = None
    stream: Optional[bool] = True
    raw: Optional[bool] = None
    keep_alive: Optional[Union[int, str]] = None

class ChatMessage(BaseModel):
    role: str
    content: str
    images: Optional[list[str]] = None

class GenerateChatCompletionForm(BaseModel):
    model: str
    messages: list[ChatMessage]
    format: Optional[str] = None
    options: Optional[dict] = None
    template: Optional[str] = None
    stream: Optional[bool] = None
    keep_alive: Optional[Union[int, str]] = None

# TODO: we should update this part once Ollama supports other types
class OpenAIChatMessageContent(BaseModel):
    type: str
    model_config = ConfigDict(extra="allow")

class OpenAIChatMessage(BaseModel):
    role: str
    content: Union[str, OpenAIChatMessageContent]

    model_config = ConfigDict(extra="allow")

class OpenAIChatCompletionForm(BaseModel):
    model: str
    messages: list[OpenAIChatMessage]

    model_config = ConfigDict(extra="allow")

# TODO: Implement a more intelligent load balancing mechanism for distributing requests among multiple backend instances.
# Current implementation uses a simple round-robin approach (random.choice). Consider incorporating algorithms like weighted round-robin,
# least connections, or least response time for better resource utilization and performance optimization.

async def check_url(request: Request, call_next):
    if len(app.state.MODELS) == 0:
        await get_all_models()
    else:
        pass

    response = await call_next(request)
    return response

async def get_status():
    return {"status": True}
async def get_config():
    return {"ENABLE_OLLAMA_API": app.state.config.ENABLE_OLLAMA_API}
async def update_config(form_data: OllamaConfigForm, ):
    app.state.config.ENABLE_OLLAMA_API = form_data.enable_ollama_api
    return {"ENABLE_OLLAMA_API": app.state.config.ENABLE_OLLAMA_API}
async def get_ollama_api_urls():
    return {"OLLAMA_BASE_URLS": app.state.config.OLLAMA_BASE_URLS}
async def update_ollama_api_url(form_data: UrlUpdateForm, ):
    app.state.config.OLLAMA_BASE_URLS = form_data.urls

    log.info(f"app.state.config.OLLAMA_BASE_URLS: {app.state.config.OLLAMA_BASE_URLS}")
    return {"OLLAMA_BASE_URLS": app.state.config.OLLAMA_BASE_URLS}
async def fetch_url(url):
    timeout = aiohttp.ClientTimeout(total=5)
    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.get(url) as response:
                return await response.json()
    except Exception as e:
        # Handle connection error here
        log.error(f"Connection error: {e}")
        return None
async def cleanup_response(response: Optional[aiohttp.ClientResponse], session: Optional[aiohttp.ClientSession],):
    if response:
        response.close()
    if session:
        await session.close()
# async def post_streaming_url(url: str, payload: Union[str, bytes], stream: bool = True, content_type=None):
#     r = None
#     try:
#         session = aiohttp.ClientSession(
#             trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
#         )
#         r = await session.post(
#             url,
#             data=payload,
#             headers={"Content-Type": "application/json"},
#         )
#         r.raise_for_status()
#
#         if stream:
#             headers = dict(r.headers)
#             if content_type:
#                 headers["Content-Type"] = content_type
#             return StreamingResponse(
#                 r.content,
#                 status_code=r.status,
#                 headers=headers,
#                 background=BackgroundTask(
#                     cleanup_response, response=r, session=session
#                 ),
#             )
#         else:
#             res = await r.json()
#             await cleanup_response(r, session)
#             return res
#
#     except Exception as e:
#         error_detail = "Open WebUI: Server Connection Error"
#         if r is not None:
#             try:
#                 res = await r.json()
#                 if "error" in res:
#                     error_detail = f"Ollama: {res['error']}"
#             except Exception:
#                 error_detail = f"Ollama: {e}"
#
#         raise HTTPException(
#             status_code=r.status if r else 500,
#             detail=error_detail,
#         )
def merge_models_lists(model_lists):
    merged_models = {}

    for idx, model_list in enumerate(model_lists):
        if model_list is not None:
            for model in model_list:
                digest = model["digest"]
                if digest not in merged_models:
                    model["urls"] = [idx]
                    merged_models[digest] = model
                else:
                    merged_models[digest]["urls"].append(idx)

    return list(merged_models.values())
async def get_all_models():
    log.info("get_all_models()")

    if app.state.config.ENABLE_OLLAMA_API:
        tasks = [
            fetch_url(f"{url}/api/tags") for url in app.state.config.OLLAMA_BASE_URLS
        ]
        responses = await asyncio.gather(*tasks)

        models = {
            "models": merge_models_lists(
                map(
                    lambda response: response["models"] if response else None, responses
                )
            )
        }

    else:
        models = {"models": []}

    app.state.MODELS = {model["model"]: model for model in models["models"]}

    return models

async def get_ollama_versions(url_idx: Optional[int] = None):
    if app.state.config.ENABLE_OLLAMA_API:
        if url_idx is None:
            # returns lowest version
            tasks = [
                fetch_url(f"{url}/api/version")
                for url in app.state.config.OLLAMA_BASE_URLS
            ]
            responses = await asyncio.gather(*tasks)
            responses = list(filter(lambda x: x is not None, responses))

            if len(responses) > 0:
                lowest_version = min(
                    responses,
                    key=lambda x: tuple(
                        map(int, re.sub(r"^v|-.*", "", x["version"]).split("."))
                    ),
                )

                return {"version": lowest_version["version"]}
            else:
                raise HTTPException(
                    status_code=500,
                    detail=ERROR_MESSAGES.OLLAMA_NOT_FOUND,
                )
        else:
            url = app.state.config.OLLAMA_BASE_URLS[url_idx]

            r = None
            try:
                r = requests.request(method="GET", url=f"{url}/api/version")
                r.raise_for_status()

                return r.json()
            except Exception as e:
                log.exception(e)
                error_detail = "Open WebUI: Server Connection Error"
                if r is not None:
                    try:
                        res = r.json()
                        if "error" in res:
                            error_detail = f"Ollama: {res['error']}"
                    except Exception:
                        error_detail = f"Ollama: {e}"

                raise HTTPException(
                    status_code=r.status_code if r else 500,
                    detail=error_detail,
                )
    else:
        return {"version": False}
# async def pull_model(form_data: ModelNameForm, url_idx: int = 0,):
#     url = app.state.config.OLLAMA_BASE_URLS[url_idx]
#     log.info(f"url: {url}")
#
#     # Admin should be able to pull models from any source
#     payload = {**form_data.model_dump(exclude_none=True), "insecure": True}
#
#     return await post_streaming_url(f"{url}/api/pull", json.dumps(payload))
# async def push_model(form_data: PushModelForm, url_idx: Optional[int] = None):
#     if url_idx is None:
#         if form_data.name in app.state.MODELS:
#             url_idx = app.state.MODELS[form_data.name]["urls"][0]
#         else:
#             raise HTTPException(
#                 status_code=400,
#                 detail=ERROR_MESSAGES.MODEL_NOT_FOUND(form_data.name),
#             )
#
#     url = app.state.config.OLLAMA_BASE_URLS[url_idx]
#     log.debug(f"url: {url}")
#
#     return await post_streaming_url(
#         f"{url}/api/push", form_data.model_dump_json(exclude_none=True).encode()
#     )
# async def create_model(form_data: CreateModelForm, url_idx: int = 0,):
#     log.debug(f"form_data: {form_data}")
#     url = app.state.config.OLLAMA_BASE_URLS[url_idx]
#     log.info(f"url: {url}")
#
#     return await post_streaming_url(
#         f"{url}/api/create", form_data.model_dump_json(exclude_none=True).encode()
#     )

async def copy_model(form_data: CopyModelForm, url_idx: Optional[int] = None):
    if url_idx is None:
        if form_data.source in app.state.MODELS:
            url_idx = app.state.MODELS[form_data.source]["urls"][0]
        else:
            raise HTTPException(
                status_code=400,
                detail=ERROR_MESSAGES.MODEL_NOT_FOUND(form_data.source),
            )

    url = app.state.config.OLLAMA_BASE_URLS[url_idx]
    log.info(f"url: {url}")
    r = requests.request(
        method="POST",
        url=f"{url}/api/copy",
        headers={"Content-Type": "application/json"},
        data=form_data.model_dump_json(exclude_none=True).encode(),
    )

    try:
        r.raise_for_status()

        log.debug(f"r.text: {r.text}")

        return True
    except Exception as e:
        log.exception(e)
        error_detail = "Open WebUI: Server Connection Error"
        if r is not None:
            try:
                res = r.json()
                if "error" in res:
                    error_detail = f"Ollama: {res['error']}"
            except Exception:
                error_detail = f"Ollama: {e}"

        raise HTTPException(
            status_code=r.status_code if r else 500,
            detail=error_detail,
        )
async def delete_model(form_data: ModelNameForm, url_idx: Optional[int] = None):
    if url_idx is None:
        if form_data.name in app.state.MODELS:
            url_idx = app.state.MODELS[form_data.name]["urls"][0]
        else:
            raise HTTPException(
                status_code=400,
                detail=ERROR_MESSAGES.MODEL_NOT_FOUND(form_data.name),
            )

    url = app.state.config.OLLAMA_BASE_URLS[url_idx]
    log.info(f"url: {url}")

    r = requests.request(
        method="DELETE",
        url=f"{url}/api/delete",
        headers={"Content-Type": "application/json"},
        data=form_data.model_dump_json(exclude_none=True).encode(),
    )
    try:
        r.raise_for_status()

        log.debug(f"r.text: {r.text}")

        return True
    except Exception as e:
        log.exception(e)
        error_detail = "Open WebUI: Server Connection Error"
        if r is not None:
            try:
                res = r.json()
                if "error" in res:
                    error_detail = f"Ollama: {res['error']}"
            except Exception:
                error_detail = f"Ollama: {e}"

        raise HTTPException(
            status_code=r.status_code if r else 500,
            detail=error_detail,
        )
async def show_model_info(form_data: ModelNameForm):
    if form_data.name not in app.state.MODELS:
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.MODEL_NOT_FOUND(form_data.name),
        )

    url_idx = random.choice(app.state.MODELS[form_data.name]["urls"])
    url = app.state.config.OLLAMA_BASE_URLS[url_idx]
    log.info(f"url: {url}")

    r = requests.request(
        method="POST",
        url=f"{url}/api/show",
        headers={"Content-Type": "application/json"},
        data=form_data.model_dump_json(exclude_none=True).encode(),
    )
    try:
        r.raise_for_status()

        return r.json()
    except Exception as e:
        log.exception(e)
        error_detail = "Open WebUI: Server Connection Error"
        if r is not None:
            try:
                res = r.json()
                if "error" in res:
                    error_detail = f"Ollama: {res['error']}"
            except Exception:
                error_detail = f"Ollama: {e}"

        raise HTTPException(
            status_code=r.status_code if r else 500,
            detail=error_detail,
        )
async def generate_embeddings(form_data: GenerateEmbedForm, url_idx: Optional[int] = None):
    if url_idx is None:
        model = form_data.model

        if ":" not in model:
            model = f"{model}:latest"

        if model in app.state.MODELS:
            url_idx = random.choice(app.state.MODELS[model]["urls"])
        else:
            raise HTTPException(
                status_code=400,
                detail=ERROR_MESSAGES.MODEL_NOT_FOUND(form_data.model),
            )

    url = app.state.config.OLLAMA_BASE_URLS[url_idx]
    log.info(f"url: {url}")

    r = requests.request(
        method="POST",
        url=f"{url}/api/embed",
        headers={"Content-Type": "application/json"},
        data=form_data.model_dump_json(exclude_none=True).encode(),
    )
    try:
        r.raise_for_status()

        return r.json()
    except Exception as e:
        log.exception(e)
        error_detail = "Open WebUI: Server Connection Error"
        if r is not None:
            try:
                res = r.json()
                if "error" in res:
                    error_detail = f"Ollama: {res['error']}"
            except Exception:
                error_detail = f"Ollama: {e}"

        raise HTTPException(
            status_code=r.status_code if r else 500,
            detail=error_detail,
        )

async def generate_embeddings(form_data: GenerateEmbeddingsForm, url_idx: Optional[int] = None):
    if url_idx is None:
        model = form_data.model

        if ":" not in model:
            model = f"{model}:latest"

        if model in app.state.MODELS:
            url_idx = random.choice(app.state.MODELS[model]["urls"])
        else:
            raise HTTPException(
                status_code=400,
                detail=ERROR_MESSAGES.MODEL_NOT_FOUND(form_data.model),
            )

    url = app.state.config.OLLAMA_BASE_URLS[url_idx]
    log.info(f"url: {url}")

    r = requests.request(
        method="POST",
        url=f"{url}/api/embeddings",
        headers={"Content-Type": "application/json"},
        data=form_data.model_dump_json(exclude_none=True).encode(),
    )
    try:
        r.raise_for_status()

        return r.json()
    except Exception as e:
        log.exception(e)
        error_detail = "Open WebUI: Server Connection Error"
        if r is not None:
            try:
                res = r.json()
                if "error" in res:
                    error_detail = f"Ollama: {res['error']}"
            except Exception:
                error_detail = f"Ollama: {e}"

        raise HTTPException(
            status_code=r.status_code if r else 500,
            detail=error_detail,
        )
def generate_ollama_embeddings(form_data: GenerateEmbeddingsForm, url_idx: Optional[int] = None):
    log.info(f"generate_ollama_embeddings {form_data}")

    if url_idx is None:
        model = form_data.model

        if ":" not in model:
            model = f"{model}:latest"

        if model in app.state.MODELS:
            url_idx = random.choice(app.state.MODELS[model]["urls"])
        else:
            raise HTTPException(
                status_code=400,
                detail=ERROR_MESSAGES.MODEL_NOT_FOUND(form_data.model),
            )

    url = app.state.config.OLLAMA_BASE_URLS[url_idx]
    log.info(f"url: {url}")

    r = requests.request(
        method="POST",
        url=f"{url}/api/embeddings",
        headers={"Content-Type": "application/json"},
        data=form_data.model_dump_json(exclude_none=True).encode(),
    )
    try:
        r.raise_for_status()

        data = r.json()

        log.info(f"generate_ollama_embeddings {data}")

        if "embedding" in data:
            return data["embedding"]
        else:
            raise Exception("Something went wrong :/")
    except Exception as e:
        log.exception(e)
        error_detail = "Open WebUI: Server Connection Error"
        if r is not None:
            try:
                res = r.json()
                if "error" in res:
                    error_detail = f"Ollama: {res['error']}"
            except Exception:
                error_detail = f"Ollama: {e}"

        raise Exception(error_detail)
# async def generate_completion(form_data: GenerateCompletionForm, url_idx: Optional[int] = None):
#     if url_idx is None:
#         model = form_data.model
#
#         if ":" not in model:
#             model = f"{model}:latest"
#
#         if model in app.state.MODELS:
#             url_idx = random.choice(app.state.MODELS[model]["urls"])
#         else:
#             raise HTTPException(
#                 status_code=400,
#                 detail=ERROR_MESSAGES.MODEL_NOT_FOUND(form_data.model),
#             )
#
#     url = app.state.config.OLLAMA_BASE_URLS[url_idx]
#     log.info(f"url: {url}")
#
#     return await post_streaming_url(
#         f"{url}/api/generate", form_data.model_dump_json(exclude_none=True).encode()
#     )

def get_ollama_url(url_idx: Optional[int], model: str):
    if url_idx is None:
        if model not in app.state.MODELS:
            raise HTTPException(
                status_code=400,
                detail=ERROR_MESSAGES.MODEL_NOT_FOUND(model),
            )
        url_idx = random.choice(app.state.MODELS[model]["urls"])
    url = app.state.config.OLLAMA_BASE_URLS[url_idx]
    return url
# async def generate_chat_completion(form_data: GenerateChatCompletionForm, url_idx: Optional[int] = None):
#     payload = {**form_data.model_dump(exclude_none=True)}
#     log.debug(f"{payload = }")
#     if "metadata" in payload:
#         del payload["metadata"]
#
#     model_id = form_data.model
#
#     model_info = Models.get_model_by_id(model_id)
#
#     if model_info:
#         if model_info.base_model_id:
#             payload["model"] = model_info.base_model_id
#
#         params = model_info.params.model_dump()
#
#         if params:
#             if payload.get("options") is None:
#                 payload["options"] = {}
#
#             payload["options"] = apply_model_params_to_body_ollama(
#                 params, payload["options"]
#             )
#             payload = apply_model_system_prompt_to_body(params, payload)
#
#     if ":" not in payload["model"]:
#         payload["model"] = f"{payload['model']}:latest"
#
#     url = get_ollama_url(url_idx, payload["model"])
#     log.info(f"url: {url}")
#     log.debug(payload)
#
#     return await post_streaming_url(
#         f"{url}/api/chat",
#         json.dumps(payload),
#         stream=form_data.stream,
#         content_type="application/x-ndjson",
#     )
# async def generate_openai_chat_completion(form_data: dict,url_idx: Optional[int] = None):
#     completion_form = OpenAIChatCompletionForm(**form_data)
#     payload = {**completion_form.model_dump(exclude_none=True, exclude=["metadata"])}
#     if "metadata" in payload:
#         del payload["metadata"]
#
#     model_id = completion_form.model
#
#     model_info = Models.get_model_by_id(model_id)
#
#     if model_info:
#         if model_info.base_model_id:
#             payload["model"] = model_info.base_model_id
#
#         params = model_info.params.model_dump()
#
#         if params:
#             payload = apply_model_params_to_body_openai(params, payload)
#             payload = apply_model_system_prompt_to_body(params, payload)
#
#     if ":" not in payload["model"]:
#         payload["model"] = f"{payload['model']}:latest"
#
#     url = get_ollama_url(url_idx, payload["model"])
#     log.info(f"url: {url}")
#
#     return await post_streaming_url(
#         f"{url}/v1/chat/completions",
#         json.dumps(payload),
#         stream=payload.get("stream", False),
#     )
async def get_openai_models(url_idx: Optional[int] = None):
    if url_idx is None:
        models = await get_all_models()
        return {
            "data": [
                {
                    "id": model["model"],
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "openai",
                }
                for model in models["models"]
            ],
            "object": "list",
        }

    else:
        url = app.state.config.OLLAMA_BASE_URLS[url_idx]
        try:
            r = requests.request(method="GET", url=f"{url}/api/tags")
            r.raise_for_status()

            models = r.json()

            return {
                "data": [
                    {
                        "id": model["model"],
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "openai",
                    }
                    for model in models["models"]
                ],
                "object": "list",
            }

        except Exception as e:
            log.exception(e)
            error_detail = "Open WebUI: Server Connection Error"
            if r is not None:
                try:
                    res = r.json()
                    if "error" in res:
                        error_detail = f"Ollama: {res['error']}"
                except Exception:
                    error_detail = f"Ollama: {e}"

            raise HTTPException(
                status_code=r.status_code if r else 500,
                detail=error_detail,
            )
def parse_huggingface_url(hf_url):
    try:
        # Parse the URL
        parsed_url = urlparse(hf_url)

        # Get the path and split it into components
        path_components = parsed_url.path.split("/")

        # Extract the desired output
        model_file = path_components[-1]

        return model_file
    except ValueError:
        return None
async def download_file_stream(ollama_url, file_url, file_path, file_name, chunk_size=1024 * 1024):
    done = False

    if os.path.exists(file_path):
        current_size = os.path.getsize(file_path)
    else:
        current_size = 0

    headers = {"Range": f"bytes={current_size}-"} if current_size > 0 else {}

    timeout = aiohttp.ClientTimeout(total=600)  # Set the timeout

    async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
        async with session.get(file_url, headers=headers) as response:
            total_size = int(response.headers.get("content-length", 0)) + current_size

            with open(file_path, "ab+") as file:
                async for data in response.content.iter_chunked(chunk_size):
                    current_size += len(data)
                    file.write(data)

                    done = current_size == total_size
                    progress = round((current_size / total_size) * 100, 2)

                    yield f'data: {{"progress": {progress}, "completed": {current_size}, "total": {total_size}}}\n\n'

                if done:
                    file.seek(0)
                    hashed = calculate_sha256(file)
                    file.seek(0)

                    url = f"{ollama_url}/api/blobs/sha256:{hashed}"
                    response = requests.post(url, data=file)

                    if response.ok:
                        res = {
                            "done": done,
                            "blob": f"sha256:{hashed}",
                            "name": file_name,
                        }
                        os.remove(file_path)

                        yield f"data: {json.dumps(res)}\n\n"
                    else:
                        raise "Ollama: Could not create blob, Please try again."
# url = "https://huggingface.co/TheBloke/stablelm-zephyr-3b-GGUF/resolve/main/stablelm-zephyr-3b.Q2_K.gguf"
# async def download_model(form_data: UrlForm,url_idx: Optional[int] = None):
#     allowed_hosts = ["https://huggingface.co/", "https://github.com/"]
#
#     if not any(form_data.url.startswith(host) for host in allowed_hosts):
#         raise HTTPException(
#             status_code=400,
#             detail="Invalid file_url. Only URLs from allowed hosts are permitted.",
#         )
#
#     if url_idx is None:
#         url_idx = 0
#     url = app.state.config.OLLAMA_BASE_URLS[url_idx]
#
#     file_name = parse_huggingface_url(form_data.url)
#
#     if file_name:
#         file_path = f"{UPLOAD_DIR}/{file_name}"
#
#         return StreamingResponse(
#             download_file_stream(url, form_data.url, file_path, file_name),
#         )
#     else:
#         return None
# def upload_model(file: UploadFile = File(...),url_idx: Optional[int] = None):
#     if url_idx is None:
#         url_idx = 0
#     ollama_url = app.state.config.OLLAMA_BASE_URLS[url_idx]
#
#     file_path = f"{UPLOAD_DIR}/{file.filename}"
#
#     # Save file in chunks
#     with open(file_path, "wb+") as f:
#         for chunk in file.file:
#             f.write(chunk)
#
#     def file_process_stream():
#         nonlocal ollama_url
#         total_size = os.path.getsize(file_path)
#         chunk_size = 1024 * 1024
#         try:
#             with open(file_path, "rb") as f:
#                 total = 0
#                 done = False
#
#                 while not done:
#                     chunk = f.read(chunk_size)
#                     if not chunk:
#                         done = True
#                         continue
#
#                     total += len(chunk)
#                     progress = round((total / total_size) * 100, 2)
#
#                     res = {
#                         "progress": progress,
#                         "total": total_size,
#                         "completed": total,
#                     }
#                     yield f"data: {json.dumps(res)}\n\n"
#
#                 if done:
#                     f.seek(0)
#                     hashed = calculate_sha256(f)
#                     f.seek(0)
#
#                     url = f"{ollama_url}/api/blobs/sha256:{hashed}"
#                     response = requests.post(url, data=f)
#
#                     if response.ok:
#                         res = {
#                             "done": done,
#                             "blob": f"sha256:{hashed}",
#                             "name": file.filename,
#                         }
#                         os.remove(file_path)
#                         yield f"data: {json.dumps(res)}\n\n"
#                     else:
#                         raise Exception(
#                             "Ollama: Could not create blob, Please try again."
#                         )
#
#         except Exception as e:
#             res = {"error": str(e)}
#             yield f"data: {json.dumps(res)}\n\n"
#
#     return StreamingResponse(file_process_stream(), media_type="text/event-stream")
