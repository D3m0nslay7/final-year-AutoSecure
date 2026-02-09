FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for scapy (network scanning) and iptables (segmentation)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tcpdump \
    libpcap-dev \
    iptables \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY Discovery/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all engine modules
COPY . .

# Run with unbuffered output so logs appear in real-time
CMD ["python", "-u", "main.py"]
