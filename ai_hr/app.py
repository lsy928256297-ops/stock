"""AI HR 面试助手 - Flask Web 服务入口。

启动：
    python -m ai_hr.app
或：
    cd ai_hr && python app.py

默认监听 0.0.0.0:8765。
"""
from __future__ import annotations

import os
import sys
import traceback

from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ai_hr import ai_client, config, prompts, resume_parser, storage  # type: ignore
else:
    from . import ai_client, config, prompts, resume_parser, storage


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(config.BASE_DIR, "templates"),
        static_folder=os.path.join(config.BASE_DIR, "static"),
    )
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH

    # ---------------- 页面 ----------------
    @app.route("/")
    def index():
        return render_template(
            "index.html",
            model=config.MODEL,
            api_base=config.API_BASE,
            api_key_set=bool(config.API_KEY),
        )

    # ---------------- 行（候选人）CRUD ----------------
    @app.get("/api/rows")
    def api_list_rows():
        return jsonify({"rows": storage.list_rows()})

    @app.post("/api/rows")
    def api_create_row():
        data = request.get_json(silent=True) or {}
        row = storage.create_row(
            job_desc=data.get("job_desc", ""),
            focus_points=data.get("focus_points", ""),
        )
        return jsonify(row)

    @app.put("/api/rows/<row_id>")
    def api_update_row(row_id: str):
        data = request.get_json(silent=True) or {}
        allowed = {
            "job_desc",
            "focus_points",
            "interview_notes",
            "questions_md",
            "resume_text",
            "resume_filename",
        }
        fields = {k: v for k, v in data.items() if k in allowed}
        row = storage.update_row(row_id, **fields)
        if not row:
            return jsonify({"error": "row not found"}), 404
        return jsonify(row)

    @app.delete("/api/rows/<row_id>")
    def api_delete_row(row_id: str):
        ok = storage.delete_row(row_id)
        if not ok:
            return jsonify({"error": "row not found"}), 404
        return jsonify({"ok": True})

    # ---------------- 简历上传 ----------------
    @app.post("/api/rows/<row_id>/resume")
    def api_upload_resume(row_id: str):
        row = storage.get_row(row_id)
        if not row:
            return jsonify({"error": "row not found"}), 404
        if "file" not in request.files:
            return jsonify({"error": "请选择简历文件"}), 400
        file = request.files["file"]
        if not file or not file.filename:
            return jsonify({"error": "请选择简历文件"}), 400
        filename = secure_filename(file.filename) or file.filename
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if ext not in config.ALLOWED_EXTENSIONS:
            return jsonify({
                "error": f"不支持的文件类型 .{ext}；仅支持: {', '.join(sorted(config.ALLOWED_EXTENSIONS))}"
            }), 400
        raw = file.read()
        try:
            text = resume_parser.extract_resume_text(filename, raw)
        except (ValueError, RuntimeError) as exc:
            return jsonify({"error": str(exc)}), 400
        # 存盘（便于追溯）
        save_name = f"{row_id}_{filename}"
        save_path = os.path.join(config.UPLOAD_DIR, save_name)
        try:
            with open(save_path, "wb") as f:
                f.write(raw)
        except OSError:
            pass
        updated = storage.update_row(
            row_id, resume_filename=filename, resume_text=text
        )
        return jsonify(updated)

    @app.post("/api/rows/bulk_resume")
    def api_bulk_upload_resumes():
        """一次上传多份简历：每份自动创建一行。可附带默认 job_desc / focus_points。"""
        job_desc = request.form.get("job_desc", "")
        focus_points = request.form.get("focus_points", "")
        files = request.files.getlist("files")
        if not files:
            return jsonify({"error": "未选择任何文件"}), 400
        created, errors = [], []
        for file in files:
            if not file or not file.filename:
                continue
            filename = secure_filename(file.filename) or file.filename
            ext = os.path.splitext(filename)[1].lower().lstrip(".")
            if ext not in config.ALLOWED_EXTENSIONS:
                errors.append({"file": filename, "error": f"不支持 .{ext}"})
                continue
            raw = file.read()
            try:
                text = resume_parser.extract_resume_text(filename, raw)
            except (ValueError, RuntimeError) as exc:
                errors.append({"file": filename, "error": str(exc)})
                continue
            row = storage.create_row(
                job_desc=job_desc,
                focus_points=focus_points,
                resume_filename=filename,
                resume_text=text,
            )
            try:
                with open(
                    os.path.join(config.UPLOAD_DIR, f"{row['id']}_{filename}"), "wb"
                ) as f:
                    f.write(raw)
            except OSError:
                pass
            created.append(row)
        return jsonify({"created": created, "errors": errors})

    # ---------------- AI 生成：面试问题 ----------------
    @app.post("/api/rows/<row_id>/generate_questions")
    def api_generate_questions(row_id: str):
        row = storage.get_row(row_id)
        if not row:
            return jsonify({"error": "row not found"}), 404
        messages = prompts.build_questions_messages(
            row.get("job_desc", ""),
            row.get("resume_text", ""),
            row.get("focus_points", ""),
        )
        try:
            text = ai_client.chat_completion(messages, temperature=0.5, max_tokens=3000)
        except ai_client.AIClientError as exc:
            return jsonify({"error": str(exc)}), 502
        updated = storage.update_row(row_id, questions_md=text)
        return jsonify(updated)

    # ---------------- AI 分析：面试记录 ----------------
    @app.post("/api/rows/<row_id>/analyze")
    def api_analyze(row_id: str):
        row = storage.get_row(row_id)
        if not row:
            return jsonify({"error": "row not found"}), 404
        notes = (row.get("interview_notes") or "").strip()
        if not notes:
            # 允许前端在调用前先提交；若仍为空则直接报错
            return jsonify({"error": "请先填写面试记录后再分析"}), 400
        messages = prompts.build_analysis_messages(
            row.get("job_desc", ""),
            row.get("resume_text", ""),
            row.get("focus_points", ""),
            row.get("questions_md", ""),
            notes,
        )
        try:
            text = ai_client.chat_completion(
                messages,
                temperature=0.2,
                max_tokens=3000,
                response_format_json=True,
            )
        except ai_client.AIClientError as exc:
            return jsonify({"error": str(exc)}), 502
        parsed = ai_client.extract_json(text)
        if not parsed:
            return jsonify({
                "error": "模型输出不是有效的 JSON，原文已附在 raw 字段",
                "raw": text,
            }), 502
        parsed["_raw"] = text
        updated = storage.update_row(row_id, analysis=parsed)
        return jsonify(updated)

    # ---------------- 元信息 ----------------
    @app.get("/api/meta")
    def api_meta():
        return jsonify({
            "model": config.MODEL,
            "api_base": config.API_BASE,
            "api_key_set": bool(config.API_KEY),
            "allowed_ext": sorted(config.ALLOWED_EXTENSIONS),
            "max_mb": config.MAX_CONTENT_MB,
        })

    @app.get("/api/diagnose")
    def api_diagnose():
        """一键自检：LLM 接口是否可用。"""
        result = ai_client.ping()
        result["model"] = config.MODEL
        result["api_base"] = config.API_BASE
        result["api_key_set"] = bool(config.API_KEY)
        return jsonify(result)

    # ---------------- 错误处理 ----------------
    @app.errorhandler(413)
    def too_large(_):
        return jsonify({"error": f"文件大小超过 {config.MAX_CONTENT_MB}MB 限制"}), 413

    @app.errorhandler(Exception)
    def on_error(exc):
        traceback.print_exc()
        return jsonify({"error": f"服务器错误: {exc}"}), 500

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    host = os.environ.get("HOST", "0.0.0.0")
    app.run(host=host, port=port, debug=False)
