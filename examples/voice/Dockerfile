FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py index.html index.js recording_server.py README.md ./
COPY wavtools ./wavtools

ENV PORT=9511

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9511"]
