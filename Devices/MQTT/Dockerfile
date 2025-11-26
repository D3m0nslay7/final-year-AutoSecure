FROM python:3.11-slim

WORKDIR /app

# Copy MQTT broker scripts (no external dependencies needed)
COPY *.py ./

# Default command (can be overridden)
CMD ["python", "-u", "mosquitto_broker.py"]
