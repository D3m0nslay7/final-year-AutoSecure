FROM python:3.11-slim

WORKDIR /app

# Install ssdpy
RUN pip install --no-cache-dir ssdpy

# Copy SSDP device scripts
COPY *.py ./

# Default command
CMD ["python", "-u", "generic_ssdp_device.py"]
