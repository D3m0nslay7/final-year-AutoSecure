"""
Mosquitto MQTT Broker Test Device

Simulates a Mosquitto MQTT broker by:
1. Opening a TCP socket on port 1883 (standard MQTT port)
2. Responding to MQTT CONNECT packets with proper CONNACK responses
3. This allows the discovery engine to detect it as an MQTT broker

This is NOT a full MQTT broker - it only responds to connection attempts
to allow testing of the MQTT discovery functionality.
"""

import socket
import threading
import time


class MosquittoMQTTBroker:
    """Simulated Mosquitto MQTT Broker for testing"""

    def __init__(self, host='0.0.0.0', port=1883):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None
        self.client_count = 0

    def _build_connack_packet(self, return_code=0):
        """
        Build MQTT CONNACK packet

        Args:
            return_code: 0 = Connection Accepted

        Returns:
            bytes: CONNACK packet
        """
        # CONNACK packet format:
        # Byte 1: 0x20 (CONNACK packet type)
        # Byte 2: 0x02 (Remaining length)
        # Byte 3: 0x00 (Connect Acknowledge Flags)
        # Byte 4: return_code (0 = accepted)
        return bytes([0x20, 0x02, 0x00, return_code])

    def _handle_client(self, client_socket, address):
        """Handle individual client connection"""
        try:
            # Wait for CONNECT packet
            data = client_socket.recv(1024)

            if data and len(data) > 0:
                # Check if it's an MQTT CONNECT packet (starts with 0x10)
                if data[0] == 0x10:
                    # Send CONNACK response (connection accepted)
                    connack = self._build_connack_packet(return_code=0)
                    client_socket.sendall(connack)

                    self.client_count += 1
                    print(f"  ✓ Client connected from {address[0]}:{address[1]} (Total: {self.client_count})")

                    # Keep connection open briefly
                    time.sleep(0.5)

        except Exception as e:
            print(f"  Error handling client {address}: {e}")

        finally:
            try:
                client_socket.close()
            except Exception:
                pass

    def _accept_connections(self):
        """Accept incoming connections in a loop"""
        self.server_socket.listen(5)
        print(f"  Listening for MQTT connections...")

        while self.running:
            try:
                # Set timeout to allow checking self.running periodically
                self.server_socket.settimeout(1.0)

                try:
                    client_socket, address = self.server_socket.accept()

                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()

                except socket.timeout:
                    # Timeout is normal, just continue loop
                    continue

            except Exception as e:
                if self.running:
                    print(f"  Error accepting connection: {e}")

    def start(self):
        """Start the simulated MQTT broker"""
        try:
            # Create TCP socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind to port
            self.server_socket.bind((self.host, self.port))

            print("=" * 70)
            print("Mosquitto MQTT Broker (Simulated)")
            print("=" * 70)
            print(f"Vendor:       Mosquitto")
            print(f"MQTT Version: 3.1.1")
            print(f"Host:         {self.host}")
            print(f"Port:         {self.port} (Standard MQTT)")
            print("=" * 70)
            print("\nPress Ctrl+C to stop broker...\n")

            # Start accepting connections
            self.running = True

            # Run in main thread
            self._accept_connections()

        except PermissionError:
            print(f"\nError: Permission denied. Port {self.port} may require administrator privileges.")
            print("Try running as Administrator (Windows) or with sudo (Linux/Mac)")

        except OSError as e:
            if "address already in use" in str(e).lower():
                print(f"\nError: Port {self.port} is already in use.")
                print("Another MQTT broker may already be running on this port.")
            else:
                print(f"\nError starting broker: {e}")

        except Exception as e:
            print(f"\nUnexpected error: {e}")

    def stop(self):
        """Stop the simulated MQTT broker"""
        print("\n\nStopping Mosquitto broker...")
        self.running = False

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass

        print(f"Broker stopped. Total connections handled: {self.client_count}")


def main():
    """Main function to run the simulated broker"""
    # Use port 1883 - Standard MQTT port (unencrypted)
    broker = MosquittoMQTTBroker(host='0.0.0.0', port=1883)

    try:
        broker.start()
    except KeyboardInterrupt:
        broker.stop()


if __name__ == "__main__":
    main()
