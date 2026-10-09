FROM python:3.11-alpine

# Non-root user
RUN adduser -D -u 1001 appuser

WORKDIR /app

# Minimal agent dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser agent.py .

USER 1001

# ARM placement engine will route traffic to this port
EXPOSE 8080

CMD ["python", "agent.py"]
