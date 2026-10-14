# Reproducible environment for the Python evidence layer (Power BI Desktop is out of scope).
FROM python:3.13.7-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

COPY . .
RUN useradd --create-home app && chown -R app /app
USER app

CMD ["sh", "-c", "for a in lint validate-data validate-artifact batch-smoke validate-evidence; do python -B -m tools.project_checks $a || exit 1; done"]
