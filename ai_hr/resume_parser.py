"""简历解析：支持 PDF / DOCX / TXT / MD。"""
from __future__ import annotations

import io
import os
from typing import Union


def _extract_pdf_pdfminer(raw: bytes) -> str:
    from pdfminer.high_level import extract_text  # type: ignore
    return extract_text(io.BytesIO(raw)) or ""


def _extract_pdf_pypdf(raw: bytes) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        from PyPDF2 import PdfReader  # type: ignore
    reader = PdfReader(io.BytesIO(raw))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(parts)


def _inspect_pdf(raw: bytes) -> dict:
    """初步探测 PDF：文件魔数、是否加密、页数、是否含 Text 对象。"""
    info = {
        "is_pdf": raw[:5] == b"%PDF-",
        "size_kb": round(len(raw) / 1024, 1),
        "encrypted": False,
        "pages": None,
        "has_text_stream": False,
        "has_image": False,
        "reader_err": None,
    }
    if not info["is_pdf"]:
        return info
    try:
        try:
            from pypdf import PdfReader  # type: ignore
        except ImportError:
            from PyPDF2 import PdfReader  # type: ignore
        reader = PdfReader(io.BytesIO(raw))
        info["encrypted"] = bool(getattr(reader, "is_encrypted", False))
        info["pages"] = len(reader.pages)
    except Exception as exc:
        info["reader_err"] = f"{type(exc).__name__}: {exc}"
    # 粗略检查原文里是否能找到 BT/ET 之间的文本段或 Image XObject
    try:
        head = raw[: min(len(raw), 4 * 1024 * 1024)]
        info["has_text_stream"] = b"/Tj" in head or b"/TJ" in head or b"BT\n" in head
        info["has_image"] = b"/Image" in head or b"/XObject" in head
    except Exception:
        pass
    return info


def _extract_pdf(raw: bytes) -> str:
    """PDF 解析：优先 pdfminer.six，失败则回退到 pypdf。两者都失败时抛详细错误。"""
    info = _inspect_pdf(raw)

    if not info["is_pdf"]:
        raise RuntimeError(
            "这个文件不是有效的 PDF（文件头不是 %PDF-）。"
            "请确认扩展名没有改错，或重新导出一份 PDF 后再上传。"
            f"\n[诊断] 大小 {info['size_kb']}KB"
        )

    if info["encrypted"]:
        raise RuntimeError(
            "这份 PDF 带有密码/权限加密，无法提取文字。请先用 WPS/Adobe 解除加密后再上传（文件 → 属性 → 权限 → 移除）。"
            f"\n[诊断] 大小 {info['size_kb']}KB, 页数 {info['pages']}"
        )

    errors = []
    for name, fn in (("pdfminer", _extract_pdf_pdfminer), ("pypdf", _extract_pdf_pypdf)):
        try:
            text = fn(raw)
            if text and text.strip():
                return text
            errors.append(f"{name}: 解析结果为空")
        except ImportError as exc:
            errors.append(f"{name}: 未安装（{exc}）")
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")

    hint = ""
    if info["has_image"] and not info["has_text_stream"]:
        hint = (
            "\n[推测] 这份 PDF 很可能是**扫描件 / 图片 PDF**（内部只有图像，没有可选中的文字流）。"
            "解决方案：\n"
            "  1) 用微信/WPS/Adobe 的「OCR 文字识别」功能把图像转成文字后另存为 PDF；\n"
            "  2) 或直接让候选人发 Word/DOCX 版本；\n"
            "  3) 或把简历文字复制到一个 .txt 文件上传。"
        )
    elif not info["has_text_stream"]:
        hint = (
            "\n[推测] PDF 内部没有检测到标准文字流，可能是自定义编码/子集字体 / 异常 PDF。"
            "建议用 Adobe / WPS 重新「另存为 PDF」或导出为 DOCX 后再上传。"
        )

    diag = f"\n[诊断] 大小 {info['size_kb']}KB, 页数 {info['pages']}, " \
           f"加密={info['encrypted']}, 含文字流={info['has_text_stream']}, 含图像={info['has_image']}"

    raise RuntimeError(
        "PDF 解析失败。尝试记录：" + "; ".join(errors) + hint + diag
    )


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
        raise ValueError(
            "简历内容为空或无法解析。若是扫描件 PDF（全是图片），需要先做 OCR；"
            "也可改用 WPS/Adobe 将 PDF 另存为 DOCX 或 TXT 后再上传。"
        )
    return text
