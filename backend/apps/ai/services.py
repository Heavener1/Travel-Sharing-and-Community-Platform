"""
AI 服务层 — 统一封装 Kimi（Moonshot）和通义千问（Qwen / DashScope）调用。

支持同步补全和流式补全两种模式，通过 OpenAI 兼容的 chat/completions 接口接入。
"""

import json

import requests
from django.conf import settings


class AIServiceError(Exception):
    """AI 调用统一异常类型。"""


PROVIDER_OPTIONS = {
    "kimi": {
        "label": "Kimi",
        "default_model": settings.KIMI_MODEL,
        "models": [settings.KIMI_MODEL],
        "base_url": settings.KIMI_BASE_URL,
        "api_key": settings.KIMI_API_KEY,
    },
    "qwen": {
        "label": "千问",
        "default_model": settings.QWEN_MODEL,
        "models": ["qwen-turbo", "qwen-plus", "qwen-max", "qwq-plus", "qwen3-32b"],
        "base_url": settings.QWEN_BASE_URL,
        "api_key": settings.QWEN_API_KEY,
    },
}


def list_providers():
    """列出已配置的 AI 提供方，标记 API Key 是否已设置。"""
    return {
        key: {
            "label": value["label"],
            "default_model": value["default_model"],
            "models": value["models"],
            "configured": bool(value["api_key"]),
        }
        for key, value in PROVIDER_OPTIONS.items()
    }


def _build_payload(provider, prompt, model=None, system_prompt=None, temperature=0.7, stream=False):
    """构建 OpenAI 兼容的请求体。"""
    config = PROVIDER_OPTIONS[provider]
    return {
        "model": model or config["default_model"],
        "messages": [
            {
                "role": "system",
                "content": system_prompt or "你是旅游分享平台的智能助手，请用简洁、专业、可执行的中文回答。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "stream": stream,
    }


def _validate_provider(provider):
    """校验提供方名是否有效且 API Key 已配置，返回提供方配置。"""
    if provider not in PROVIDER_OPTIONS:
        raise AIServiceError("不支持的模型提供方。")
    config = PROVIDER_OPTIONS[provider]
    if not config["api_key"]:
        raise AIServiceError(f"{config['label']} API Key 未配置。")
    return config


def chat_completion(provider, prompt, model=None, system_prompt=None, temperature=0.7):
    """同步补全：发送请求，等待并返回完整的 AI 回复文本。"""
    config = _validate_provider(provider)
    payload = _build_payload(
        provider=provider,
        prompt=prompt,
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
        stream=False,
    )
    response = requests.post(
        config["base_url"],
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    if response.status_code >= 400:
        raise AIServiceError(f"{config['label']} 调用失败：{response.text[:200]}")

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        raise AIServiceError(f"{config['label']} 返回格式异常") from exc


def chat_completion_stream(provider, prompt, model=None, system_prompt=None, temperature=0.7):
    """流式补全生成器：逐块 yield AI 回复的增量文本片段。"""
    config = _validate_provider(provider)
    payload = _build_payload(
        provider=provider,
        prompt=prompt,
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
        stream=True,
    )
    response = requests.post(
        config["base_url"],
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
        stream=True,
    )
    if response.status_code >= 400:
        raise AIServiceError(f"{config['label']} 调用失败：{response.text[:200]}")

    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        line = raw_line.strip()
        if not line.startswith("data:"):
            continue
        data_str = line[5:].strip()
        if data_str == "[DONE]":
            break
        try:
            payload = json.loads(data_str)
        except json.JSONDecodeError:
            continue
        choices = payload.get("choices") or []
        if not choices:
            continue
        delta = choices[0].get("delta") or {}
        content = delta.get("content")
        if content:
            yield content
