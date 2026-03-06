FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    LIBLIB_OUTPUT_DIR=/data/output \
    LIBLIB_HOST=0.0.0.0 \
    LIBLIB_PORT=8000 \
    LIBLIB_MCP_PATH=/mcp

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY README.md ./README.md

RUN mkdir -p /data/output

EXPOSE 8000
VOLUME ["/data/output"]

CMD ["python", "-m", "liblib_mcp.server"]
