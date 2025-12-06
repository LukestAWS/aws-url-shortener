FROM python:3.12-slim AS builder
WORKDIR /app

# Install build dependencies needed for psycopg binary wheels
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final image
FROM python:3.12-slim
WORKDIR /app

ARG UID=1001
ARG GID=1001
RUN addgroup --gid $GID appgroup && \
    adduser --disabled-password --gecos '' --uid $UID --gid $GID appuser

# Install runtime libraries required by psycopg2 (libpq)
RUN apt-get update && \
    apt-get install -y libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy app sources
COPY . /app

USER appuser
EXPOSE 8000

HEALTHCHECK CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://localhost:8000/'); print('OK')" || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
