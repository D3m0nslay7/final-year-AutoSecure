from zeroconf import ServiceInfo, Zeroconf
import socket
import time
import os
import random
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler


def get_container_ip():
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return ip
    except:
        return f"192.168.1.{random.randint(100, 254)}"


def generate_mac():
    return ":".join([f"{random.randint(0, 255):02X}" for _ in range(6)])


class HAPHandler(BaseHTTPRequestHandler):
    """Minimal HTTP server simulating a HomeKit Accessory Protocol device."""

    def do_GET(self):
        if self.path == "/accessories":
            body = json.dumps({
                "accessories": [{
                    "aid": 1,
                    "services": [
                        {"iid": 1, "type": "3E", "characteristics": []},
                        {"iid": 2, "type": "43", "characteristics": [
                            {"iid": 8,  "type": "25", "value": True,  "description": "On"},
                            {"iid": 9,  "type": "08", "value": 100,   "description": "Brightness"},
                        ]}
                    ]
                }]
            })
            self._respond(200, "application/hap+json", body)
        elif self.path.startswith("/characteristics"):
            body = json.dumps({"characteristics": [{"aid": 1, "iid": 8, "value": True}]})
            self._respond(200, "application/hap+json", body)
        else:
            self._respond(404, "text/plain", "Not Found")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        if self.path == "/pair-setup":
            # Return a minimal TLV8 error: kTLVError_Authentication (0x02)
            self._respond(200, "application/pairing+tlv8", bytes([0x06, 0x01, 0x02]))
        elif self.path == "/pair-verify":
            self._respond(200, "application/pairing+tlv8", bytes([0x06, 0x01, 0x02]))
        else:
            self._respond(404, "text/plain", "Not Found")

    def do_PUT(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        self._respond(204, "application/hap+json", "")

    def _respond(self, status, ctype, body):
        encoded = body if isinstance(body, bytes) else body.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt, *args):
        print(f"  [HAP] {self.address_string()} - {fmt % args}")


def broadcast_homekit_device():
    zeroconf = Zeroconf()

    container_ip = os.getenv('DEVICE_IP', get_container_ip())
    device_id    = os.getenv('DEVICE_ID', str(random.randint(1000, 9999)))
    port         = int(os.getenv('DEVICE_PORT', '8080'))
    mac_address  = os.getenv('DEVICE_MAC', generate_mac())

    # Start HAP HTTP server in background thread
    server = HTTPServer(('0.0.0.0', port), HAPHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"HAP HTTP server listening on 0.0.0.0:{port}")

    device = ServiceInfo(
        "_hap._tcp.local.",
        f"SmartLight-{device_id}._hap._tcp.local.",
        addresses=[socket.inet_aton(container_ip)],
        port=port,
        properties={
            'md': f'SmartBulb-{device_id}',
            'pv': '1.0',
            'id': mac_address,
            'c#': '1',
            'sf': '1',
            'ff': '0',
            's#': '1',
            'ci': '5'
        }
    )

    zeroconf.register_service(device)
    print(f"Broadcasting HomeKit Device: {device.name}")
    print(f"IP: {container_ip}  Port: {port}  MAC: {mac_address}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        server.shutdown()
        zeroconf.unregister_service(device)
        zeroconf.close()


if __name__ == "__main__":
    broadcast_homekit_device()
