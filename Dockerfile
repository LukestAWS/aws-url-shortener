# ───── Builder ─────
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ───── Final ─────
FROM python:3.12-slim
WORKDIR /app

# Non-root user
ARG UID=1001
ARG GID=1001
RUN addgroup --gid $GID appgroup && \
    adduser --disabled-password --gecos '' --uid $UID --gid $GID appuser

# Copy only what we need
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

USER appuser
EXPOSE 8000

HEALTHCHECK CMD curl -f http://localhost:8000/ || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
