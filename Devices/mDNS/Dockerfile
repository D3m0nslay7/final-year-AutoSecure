FROM python:3.11-slim

WORKDIR /app

# Install zeroconf
RUN pip install --no-cache-dir zeroconf

# Copy mDNS device scripts
COPY *.py ./

# Default command (can be overridden)
CMD ["python", "-u", "generic_iot_device.py"]
