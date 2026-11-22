FROM python:3.12-slim-bookworm

# PySpark needs a JVM (17+)
RUN apt-get update \
 && apt-get install -y --no-install-recommends openjdk-17-jre-headless \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# data and results live in mounted volumes, not inside the image
ENV AGRI_DATA_DIR=/data \
    AGRI_OUTPUT_DIR=/outputs \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "scripts/run_pipeline.py"]
CMD ["--mode", "demo", "--steps", "all"]
