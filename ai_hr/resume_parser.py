"""简历解析：支持 PDF / DOCX / TXT / MD。"""
from __future__ import annotations

import io
import os
from typing import Union


def _extract_pdf(raw: bytes) -> str:
    try:
        from pdfminer.high_level import extract_text  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "未安装 pdfminer.six，无法解析 PDF；请先 pip install pdfminer.six"
        ) from exc
    return extract_text(io.BytesIO(raw)) or ""


def _extract_docx(raw: bytes) -> str:
    try:
        import docx  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "未安装 python-docx，无法解析 DOCX；请先 pip install python-docx"
        ) from exc
    document = docx.Document(io.BytesIO(raw))
    parts = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(p for p in parts if p)


def _extract_text(raw: bytes) -> str:
    for encoding in ("utf-8", "gbk", "gb18030", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def extract_resume_text(filename: str, raw: Union[bytes, bytearray]) -> str:
    """根据扩展名解析简历，返回纯文本。解析失败时抛 ValueError。"""
    raw = bytes(raw)
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    if ext == "pdf":
        text = _extract_pdf(raw)
    elif ext in {"docx"}:
        text = _extract_docx(raw)
    elif ext in {"txt", "md"}:
        text = _extract_text(raw)
    elif ext == "doc":
        raise ValueError("暂不支持旧版 .doc 格式，请另存为 .docx 或 PDF 后再上传")
    else:
        raise ValueError(f"不支持的文件类型: .{ext}")
    text = (text or "").strip()
    if not text:
        raise ValueError("简历内容为空或无法解析")
    return text
