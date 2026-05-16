FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY locust/ locust/

# sessions/ and reports/ are mounted as volumes at runtime
VOLUME ["/app/sessions", "/app/reports"]

ENV SESSIONS_DIR=/app/sessions

EXPOSE 8089

ENTRYPOINT ["locust", "-f", "locust/locustfile.py"]
CMD ["--host", "http://host.docker.internal:9000"]
