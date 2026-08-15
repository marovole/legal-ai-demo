# 律师一案一档 Web — Railway / 本地容器
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    REPO_ROOT=/app

COPY web/requirements.txt /app/web/requirements.txt
RUN pip install --no-cache-dir -r /app/web/requirements.txt

COPY . /app

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/healthz' % __import__('os').environ.get('PORT','8080'))"

CMD ["sh", "-c", "uvicorn web.app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
