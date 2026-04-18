"""调用 OpenAI 兼容接口的轻量客户端。"""
from __future__ import annotations

import json
import re
from typing import Dict, List, Optional

import requests

from . import config


class AIClientError(RuntimeError):
    pass


def _require_api_key():
    if not config.API_KEY:
        raise AIClientError(
            "未设置 AI_HR_API_KEY 环境变量，请先配置 LLM API Key 后再试。"
        )


def chat_completion(
    messages: List[Dict[str, str]],
    *,
    temperature: float = 0.4,
    max_tokens: int = 2048,
    response_format_json: bool = False,
    timeout: int = 120,
) -> str:
    """调用 LLM，返回模型输出的字符串内容。"""
    _require_api_key()
    url = f"{config.API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.API_KEY}",
        "Content-Type": "application/json",
    }
    payload: Dict = {
        "model": config.MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format_json:
        payload["response_format"] = {"type": "json_object"}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        raise AIClientError(f"调用 LLM 网络错误: {exc}") from exc

    # 某些代理/模型（例如部分 Claude 走 openai 兼容层）不支持 response_format，
    # 收到 400/422 时自动去掉该字段再重试一次。
    if response_format_json and resp.status_code in (400, 415, 422):
        err_text = (resp.text or "")[:500].lower()
        if "response_format" in err_text or "unsupported" in err_text or "invalid" in err_text:
            payload.pop("response_format", None)
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            except requests.RequestException as exc:
                raise AIClientError(f"调用 LLM 网络错误: {exc}") from exc
    ctype = (resp.headers.get("Content-Type") or "").lower()
    body_preview = (resp.text or "")[:300].strip()

    def _hint_html() -> str:
        return (
            f"LLM 返回的不是 JSON（Content-Type={ctype or 'unknown'}），疑似 AI_HR_API_BASE 配置错误。"
            f"当前 API_BASE={config.API_BASE!r}，请确认：\n"
            "  · OpenAI 官方       → https://api.openai.com/v1\n"
            "  · DeepSeek          → https://api.deepseek.com/v1\n"
            "  · 通义千问兼容      → https://dashscope.aliyuncs.com/compatible-mode/v1\n"
            "  · Kimi              → https://api.moonshot.cn/v1\n"
            "  · 火山方舟（豆包）  → https://ark.cn-beijing.volces.com/api/v3\n"
            "  · 本地 Ollama       → http://localhost:11434/v1\n"
            f"原始响应前 300 字：{body_preview!r}"
        )

    looks_like_html = (
        "text/html" in ctype
        or body_preview.lower().startswith("<!doctype")
        or body_preview.lower().startswith("<html")
    )

    if resp.status_code != 200:
        if looks_like_html:
            raise AIClientError(f"HTTP {resp.status_code}。{_hint_html()}")
        raise AIClientError(
            f"LLM 接口返回 HTTP {resp.status_code}，原文：{body_preview!r}"
        )

    if looks_like_html:
        raise AIClientError(_hint_html())

    try:
        data = resp.json()
    except ValueError as exc:
        raise AIClientError(
            f"LLM 响应不是有效 JSON（Content-Type={ctype or 'unknown'}），"
            f"原文：{body_preview!r}"
        ) from exc

    if not isinstance(data, dict) or "choices" not in data:
        err = data.get("error") if isinstance(data, dict) else None
        if err:
            raise AIClientError(f"LLM 接口返回错误：{err}")
        raise AIClientError(
            f"LLM 响应结构异常（缺少 choices 字段），原文：{json.dumps(data, ensure_ascii=False)[:300]!r}"
        )

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIClientError(
            f"解析 LLM 响应失败: {exc}; 原文：{json.dumps(data, ensure_ascii=False)[:300]!r}"
        ) from exc


def ping() -> Dict:
    """用最小请求探测 LLM 接口连通性，返回 {ok, detail}。"""
    try:
        _require_api_key()
    except AIClientError as exc:
        return {"ok": False, "stage": "config", "detail": str(exc)}
    try:
        text = chat_completion(
            [{"role": "user", "content": "ping"}],
            temperature=0.0,
            max_tokens=16,
            timeout=30,
        )
        return {"ok": True, "detail": (text or "")[:120]}
    except AIClientError as exc:
        return {"ok": False, "stage": "chat", "detail": str(exc)}


def extract_json(text: str) -> Optional[Dict]:
    """从模型输出中提取第一个 JSON 对象。"""
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None
