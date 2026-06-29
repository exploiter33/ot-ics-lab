FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl netcat-openbsd iproute2 tcpdump \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5020 4840 47808/udp 9099

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:9099/health || exit 1

CMD ["python", "-u", "sim_manager.py"]
