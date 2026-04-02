FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends tcpdump && rm -rf /var/lib/apt/lists/*

# Copy MQTT broker scripts (no external dependencies needed)
COPY *.py ./

# Default command (can be overridden)
CMD ["python", "-u", "mosquitto_broker.py"]
