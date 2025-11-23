"""
HiveMQ MQTT Broker Test Device

Simulates a HiveMQ MQTT broker by:
1. Opening a TCP socket on port 1883 (standard MQTT port)
2. Responding to MQTT CONNECT packets with proper CONNACK responses
3. Running a simple HTTP server on port 8000 (HiveMQ Control Center)
4. This allows the discovery engine to detect it as a HiveMQ broker

This is NOT a full MQTT broker - it only responds to connection attempts
and serves a simple web page to allow testing of vendor identification.
"""

import socket
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler


class HiveMQWebHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler that serves HiveMQ-like pages"""

    def do_GET(self):
        """Handle GET requests"""
        # Send response headers
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        # Send HTML content with HiveMQ branding
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>HiveMQ Control Center</title>
        </head>
        <body>
            <h1>HiveMQ Control Center</h1>
            <p>Welcome to the HiveMQ MQTT Broker Control Center</p>
            <p>Version: 4.9.0 (Simulated)</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress HTTP server log messages"""
        pass


class HiveMQMQTTBroker:
    """Simulated HiveMQ MQTT Broker for testing"""

    def __init__(self, mqtt_host='0.0.0.0', mqtt_port=1883, web_port=8000):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.web_port = web_port
        self.running = False
        self.mqtt_socket = None
        self.web_server = None
        self.client_count = 0

    def _build_connack_packet(self, return_code=0):
        """Build MQTT CONNACK packet (MQTT 5.0 format)"""
        # MQTT 5.0 CONNACK packet format:
        # Byte 1: 0x20 (CONNACK packet type)
        # Byte 2: 0x03 (Remaining length for MQTT 5.0)
        # Byte 3: 0x00 (Connect Acknowledge Flags)
        # Byte 4: return_code (0 = accepted)
        # Byte 5: 0x00 (Properties length = 0)
        return bytes([0x20, 0x03, 0x00, return_code, 0x00])

    def _handle_mqtt_client(self, client_socket, address):
        """Handle individual MQTT client connection"""
        try:
            # Wait for CONNECT packet
            data = client_socket.recv(1024)

            if data and len(data) > 0:
                # Check if it's an MQTT CONNECT packet (starts with 0x10)
                if data[0] == 0x10:
                    # Send CONNACK response
                    connack = self._build_connack_packet(return_code=0)
                    client_socket.sendall(connack)

                    self.client_count += 1
                    print(f"  [MQTT] Client connected from {address[0]}:{address[1]} (Total: {self.client_count})")

                    # Keep connection open briefly
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

                    # Handle client in separate thread
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
        """Run the web control center"""
        try:
            self.web_server = HTTPServer((self.mqtt_host, self.web_port), HiveMQWebHandler)
            print(f"  [WEB]  Listening on port {self.web_port}...")

            while self.running:
                self.web_server.handle_request()

        except Exception as e:
            print(f"  [WEB]  Failed to start: {e}")

    def start(self):
        """Start the simulated HiveMQ broker"""
        print("=" * 70)
        print("HiveMQ MQTT Broker (Simulated)")
        print("=" * 70)
        print(f"Vendor:             HiveMQ")
        print(f"MQTT Version:       5.0")
        print(f"MQTT Port:          {self.mqtt_port} (MQTT over TLS/SSL)")
        print(f"Control Center:     http://{self.mqtt_host if self.mqtt_host != '0.0.0.0' else 'localhost'}:{self.web_port}")
        print(f"Features:           WebSocket, TLS")
        print("=" * 70)
        print("\nStarting services...\n")

        self.running = True

        # Start MQTT server in separate thread
        mqtt_thread = threading.Thread(target=self._run_mqtt_server, daemon=True)
        mqtt_thread.start()

        # Give MQTT server time to start
        time.sleep(0.5)

        # Start web server in separate thread
        web_thread = threading.Thread(target=self._run_web_server, daemon=True)
        web_thread.start()

        # Give web server time to start
        time.sleep(0.5)

        print("\nHiveMQ broker is running!")
        print("Press Ctrl+C to stop...\n")

        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop the simulated broker"""
        print("\n\nStopping HiveMQ broker...")
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
    # Use port 8883 - MQTT over TLS/SSL (allows running alongside Mosquitto on 1883)
    broker = HiveMQMQTTBroker(mqtt_host='0.0.0.0', mqtt_port=8883, web_port=8000)

    try:
        broker.start()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
