FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/matplotlib \
    XDG_CACHE_HOME=/tmp \
    DATA_DIR=/app/data \
    OUTPUT_DIR=/app/output

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libfreetype6 \
        libpng16-16 \
        libjpeg62-turbo \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --create-home --home-dir /home/app app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY tests ./tests
COPY pytest.ini .
COPY main.py .

RUN mkdir -p /app/data/raw /app/output \
    && chown -R app:app /app

USER app

CMD ["python", "main.py"]
