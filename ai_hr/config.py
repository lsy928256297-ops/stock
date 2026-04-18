"""AI HR 应用配置。

支持通过环境变量覆盖默认值。默认接入 OpenAI 兼容 API（例如 OpenAI、DeepSeek、
通义千问、Kimi、本地 Ollama 等只要兼容 /v1/chat/completions 的服务）。

环境变量：
- AI_HR_API_KEY     : 调用 LLM 使用的 API Key
- AI_HR_API_BASE    : LLM 接口的 Base URL，默认 https://api.openai.com/v1
- AI_HR_MODEL       : 使用的模型名，默认 gpt-4o-mini
- AI_HR_UPLOAD_DIR  : 简历上传目录，默认 ai_hr/uploads
- AI_HR_DATA_FILE   : 持久化数据文件，默认 ai_hr/data/candidates.json
- AI_HR_MAX_MB      : 单个简历最大大小（MB），默认 16
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

API_KEY = os.environ.get("AI_HR_API_KEY", "")
API_BASE = os.environ.get("AI_HR_API_BASE", "https://api.openai.com/v1").rstrip("/")
MODEL = os.environ.get("AI_HR_MODEL", "gpt-4o-mini")

UPLOAD_DIR = os.environ.get(
    "AI_HR_UPLOAD_DIR", os.path.join(BASE_DIR, "uploads")
)
DATA_FILE = os.environ.get(
    "AI_HR_DATA_FILE", os.path.join(BASE_DIR, "data", "candidates.json")
)
MAX_CONTENT_MB = int(os.environ.get("AI_HR_MAX_MB", "16"))
MAX_CONTENT_LENGTH = MAX_CONTENT_MB * 1024 * 1024

ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt", "md"}

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
