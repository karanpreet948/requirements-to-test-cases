# Minimal image to run the Requirements-to-Test-Cases CLI.
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir .

COPY examples ./examples

# Default: show CLI help. Override the command to run "generate", e.g.:
#   docker run --rm -v "$(pwd)/out:/app/out" rtc \
#       generate --input examples/sample_requirements.yaml --output out/test_cases.xlsx
ENTRYPOINT ["python", "-m", "rtc"]
CMD ["--help"]
