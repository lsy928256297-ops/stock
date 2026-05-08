"""WSGI 入口：供 gunicorn / uwsgi 等生产服务器使用。

示例：
    gunicorn -w 2 -k gthread --threads 4 -b 0.0.0.0:8765 \
        --timeout 900 ai_hr.wsgi:app
"""
from __future__ import annotations

import os

if __name__ == "__main__" or __package__ in (None, ""):
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ai_hr.app import create_app  # type: ignore
else:
    from .app import create_app

app = create_app()
