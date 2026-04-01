from zeroconf import ServiceInfo, Zeroconf
import socket
import time
import os
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler


def get_container_ip():
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return ip
    except:
        return f"192.168.1.{random.randint(100, 254)}"


class IoTHTTPHandler(BaseHTTPRequestHandler):
    """Minimal HTTP server simulating a generic IoT device web interface."""

    ROUTES = {
        "/":                     (200, "application/json", '{"device":"GenericIoT","status":"ok"}'),
        "/admin":                (200, "text/html",        "<html><body><h1>Admin Panel</h1></body></html>"),
        "/login":                (200, "text/html",        "<html><body><form>Login</form></body></html>"),
        "/config":               (200, "application/json", '{"config":{"ssid":"home_network","auth":"none"}}'),
        "/api/v1/status":        (200, "application/json", '{"uptime":1234,"temp":22.5}'),
        "/api/v1/credentials":   (200, "application/json", '{"username":"admin","password":"admin"}'),
        "/firmware":             (200, "application/json", '{"version":"1.0.0","update_url":"http://device/fw"}'),
    }

    def do_GET(self):
        status, ctype, body = self.ROUTES.get(self.path, (404, "text/plain", "Not Found"))
        self._respond(status, ctype, body)

    def do_POST(self):
        self._respond(200, "application/json", '{"result":"ok"}')

    def _respond(self, status, ctype, body):
        encoded = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt, *args):
        print(f"  [HTTP] {self.address_string()} - {fmt % args}")


def broadcast_generic_iot():
    zeroconf = Zeroconf()

    container_ip = os.getenv('DEVICE_IP', get_container_ip())
    device_id    = os.getenv('DEVICE_ID', str(random.randint(1000, 9999)))
    port         = int(os.getenv('DEVICE_PORT', '80'))

    # Start HTTP server in background thread
    server = HTTPServer(('0.0.0.0', port), IoTHTTPHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"HTTP server listening on 0.0.0.0:{port}")

    device = ServiceInfo(
        "_http._tcp.local.",
        f"GenericIoTDevice-{device_id}._http._tcp.local.",
        addresses=[socket.inet_aton(container_ip)],
        port=port,
        properties={
            'model':        f'IoT-Generic-{device_id}',
            'manufacturer': 'Generic IoT Corp',
            'version':      '1.0.0',
            'type':         'sensor',
            'id':           device_id
        }
    )

    zeroconf.register_service(device)
    print(f"Broadcasting Generic IoT Device: {device.name}")
    print(f"IP: {container_ip}  Port: {port}")

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
    broadcast_generic_iot()
