"""
EMQX MQTT Broker Test Device

Simulates an EMQX MQTT broker by:
1. Opening a TCP socket on port 1883 (standard MQTT port)
2. Responding to MQTT CONNECT packets with proper CONNACK responses
3. Running a simple HTTP server on port 18083 (EMQX Dashboard)
4. This allows the discovery engine to detect it as an EMQX broker

This is NOT a full MQTT broker - it only responds to connection attempts
and serves a simple web page to allow testing of vendor identification.
"""

import socket
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler


class EMQXWebHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler that serves EMQX-like pages"""

    def do_GET(self):
        """Handle GET requests"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>EMQX Dashboard</title>
        </head>
        <body>
            <h1>EMQX Dashboard</h1>
            <p>Welcome to EMQX MQTT Broker Dashboard</p>
            <p>Version: 5.0.0 (Simulated)</p>
            <p>The most scalable MQTT broker for IoT</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress HTTP server log messages"""
        pass


class EMQXMQTTBroker:
    """Simulated EMQX MQTT Broker for testing"""

    def __init__(self, mqtt_host='0.0.0.0', mqtt_port=1883, dashboard_port=18083):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.dashboard_port = dashboard_port
        self.running = False
        self.mqtt_socket = None
        self.web_server = None
        self.client_count = 0

    def _build_connack_packet(self, return_code=0):
        """Build MQTT CONNACK packet (MQTT 5.0 format)"""
        return bytes([0x20, 0x03, 0x00, return_code, 0x00])

    def _handle_mqtt_client(self, client_socket, address):
        """Handle individual MQTT client connection"""
        try:
            data = client_socket.recv(1024)

            if data and len(data) > 0:
                if data[0] == 0x10:  # MQTT CONNECT
                    connack = self._build_connack_packet(return_code=0)
                    client_socket.sendall(connack)

                    self.client_count += 1
                    print(f"  [MQTT] Client connected from {address[0]}:{address[1]} (Total: {self.client_count})")

                    time.sleep(0.5)

        except Exception as e:
            print(f"  [MQTT] Error handling client {address}: {e}")
        finally:
            try:
                client_socket.close()
            except Exception:
                pass

    def _run_mqtt_server(self):
        """Run the MQTT server"""
        try:
            self.mqtt_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.mqtt_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.mqtt_socket.bind((self.mqtt_host, self.mqtt_port))
            self.mqtt_socket.listen(5)
            self.mqtt_socket.settimeout(1.0)

            print(f"  [MQTT] Listening on port {self.mqtt_port}...")

            while self.running:
                try:
                    client_socket, address = self.mqtt_socket.accept()

                    client_thread = threading.Thread(
                        target=self._handle_mqtt_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()

                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"  [MQTT] Error: {e}")

        except Exception as e:
            print(f"  [MQTT] Failed to start: {e}")

    def _run_web_server(self):
        """Run the EMQX dashboard"""
        try:
            self.web_server = HTTPServer((self.mqtt_host, self.dashboard_port), EMQXWebHandler)
            print(f"  [WEB]  Dashboard on port {self.dashboard_port}...")

            while self.running:
                self.web_server.handle_request()

        except Exception as e:
            print(f"  [WEB]  Failed to start: {e}")

    def start(self):
        """Start the simulated EMQX broker"""
        print("=" * 70)
        print("EMQX MQTT Broker (Simulated)")
        print("=" * 70)
        print(f"Vendor:             EMQX")
        print(f"MQTT Version:       5.0")
        print(f"MQTT Port:          {self.mqtt_port} (MQTT WebSocket)")
        print(f"Dashboard:          http://{self.mqtt_host if self.mqtt_host != '0.0.0.0' else 'localhost'}:{self.dashboard_port}")
        print(f"Features:           Clustering, WebSocket, MQTT-SN")
        print("=" * 70)
        print("\nStarting services...\n")

        self.running = True

        # Start MQTT server
        mqtt_thread = threading.Thread(target=self._run_mqtt_server, daemon=True)
        mqtt_thread.start()
        time.sleep(0.5)

        # Start dashboard
        web_thread = threading.Thread(target=self._run_web_server, daemon=True)
        web_thread.start()
        time.sleep(0.5)

        print("\nEMQX broker is running!")
        print("Press Ctrl+C to stop...\n")

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop the simulated broker"""
        print("\n\nStopping EMQX broker...")
        self.running = False

        if self.mqtt_socket:
            try:
                self.mqtt_socket.close()
            except Exception:
                pass

        if self.web_server:
            try:
                self.web_server.server_close()
            except Exception:
                pass

        print(f"Broker stopped. Total connections handled: {self.client_count}")


def main():
    """Main function to run the simulated broker"""
    # Use port 8884 - MQTT WebSocket (allows running alongside Mosquitto and HiveMQ)
    broker = EMQXMQTTBroker(mqtt_host='0.0.0.0', mqtt_port=8884, dashboard_port=18083)

    try:
        broker.start()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
