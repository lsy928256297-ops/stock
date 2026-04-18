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
    if resp.status_code != 200:
        raise AIClientError(
            f"LLM 接口返回 {resp.status_code}: {resp.text[:500]}"
        )
    try:
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except (KeyError, ValueError, TypeError) as exc:
        raise AIClientError(f"解析 LLM 响应失败: {exc}; 原文: {resp.text[:300]}") from exc


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
