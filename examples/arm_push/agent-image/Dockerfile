FROM registry.redhat.io/ubi9/python-311-minimal:latest

# Non-root user required by IBM security policy
RUN useradd -m -u 1001 appuser

WORKDIR /app

# Minimal agent dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser agent.py .

USER 1001

# ARM placement engine will route traffic to this port
EXPOSE 8080

CMD ["python", "agent.py"]
