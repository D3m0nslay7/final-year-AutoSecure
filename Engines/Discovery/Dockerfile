FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for scapy (network scanning)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tcpdump \
    libpcap-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire Discovery module
COPY . .

# Run with unbuffered output (-u) so logs appear in real-time
# Use the Docker wrapper script for better configuration
CMD ["python", "-u", "run_discovery_docker.py"]
