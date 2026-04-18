FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 系统依赖：pdfminer.six / pypdf 需要 libjpeg 等运行时
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libjpeg-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY ai_hr/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /root/.cache

COPY ai_hr /app/ai_hr

# 容器内数据目录。挂载宿主目录可持久化：-v ai_hr_data:/app/ai_hr/data 等。
ENV AI_HR_UPLOAD_DIR=/app/ai_hr/uploads \
    AI_HR_DATA_FILE=/app/ai_hr/data/candidates.json \
    AI_HR_DB_FILE=/app/ai_hr/data/users.db

RUN mkdir -p /app/ai_hr/uploads /app/ai_hr/data

EXPOSE 8765

HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/login', timeout=3)" || exit 1

CMD ["gunicorn", "-w", "2", "-k", "gthread", "--threads", "4", \
     "-b", "0.0.0.0:8765", "--timeout", "900", \
     "--access-logfile", "-", "--error-logfile", "-", \
     "ai_hr.wsgi:app"]
