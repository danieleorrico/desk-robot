# Il cervello di Francesca senza microfono/altoparlante locali: l'audio arriva dal robot o dalla "testa" (telefono).
# Il codice NON è dentro l'immagine: si monta da ../server, così un "git pull" basta per aggiornarlo.
FROM python:3.12-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends espeak-ng \
    && rm -rf /var/lib/apt/lists/*
COPY requirements-docker.txt /tmp/requirements-docker.txt
RUN pip install --no-cache-dir -r /tmp/requirements-docker.txt
WORKDIR /app/server
ENV PYTHONUNBUFFERED=1
CMD ["python", "launcher.py"]
