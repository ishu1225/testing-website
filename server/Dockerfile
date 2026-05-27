FROM python:3.11

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

# Prometheus multiprocess mode: required when Gunicorn runs multiple workers.
# Each worker writes its metrics into this shared directory; the /metrics
# endpoint then aggregates them all so Prometheus sees a single consistent view.
ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc

RUN mkdir -p /tmp/prometheus_multiproc

EXPOSE 5000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "2"]