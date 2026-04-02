FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends tcpdump && rm -rf /var/lib/apt/lists/*

# Install zeroconf
RUN pip install --no-cache-dir zeroconf

# Copy mDNS device scripts
COPY *.py ./

# Default command (can be overridden)
CMD ["python", "-u", "generic_iot_device.py"]
