"""
Generic MQTT Client Test Device

Simulates an IoT device that connects to an MQTT broker and
publishes sensor data periodically.

This script can be used to test MQTT broker functionality
by connecting to a local or remote broker.
"""

import time
import random
import json
from datetime import datetime


def simulate_mqtt_client(broker_host='localhost', broker_port=1883):
    """
    Simulate an IoT device publishing data to MQTT broker

    Args:
        broker_host: MQTT broker hostname or IP
        broker_port: MQTT broker port (default: 1883)
    """
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        print("Error: paho-mqtt library not installed")
        print("Install with: pip install paho-mqtt")
        return

    # Device configuration
    device_id = f"iot_sensor_{random.randint(1000, 9999)}"
    topic = f"sensors/{device_id}/data"

    print("=" * 70)
    print("Generic MQTT IoT Client (Simulated)")
    print("=" * 70)
    print(f"Device ID:        {device_id}")
    print(f"Broker:           {broker_host}:{broker_port}")
    print(f"Topic:            {topic}")
    print(f"Device Type:      Temperature & Humidity Sensor")
    print("=" * 70)

    # Callback functions
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print(f"\n✓ Connected to MQTT broker at {broker_host}:{broker_port}")
            print(f"  Publishing data every 5 seconds...")
            print(f"  Press Ctrl+C to stop\n")
        else:
            print(f"\n✗ Failed to connect to broker. Return code: {rc}")
            print(f"  Make sure broker is running at {broker_host}:{broker_port}")

    def on_publish(client, userdata, mid):
        """Called when message is published"""
        pass

    def on_disconnect(client, userdata, rc):
        if rc != 0:
            print(f"\n✗ Unexpected disconnection from broker")

    # Create MQTT client
    client = mqtt.Client(client_id=device_id)

    # Set callbacks
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect

    try:
        # Connect to broker
        print(f"\nConnecting to {broker_host}:{broker_port}...")
        client.connect(broker_host, broker_port, keepalive=60)

        # Start network loop in background
        client.loop_start()

        # Publish sensor data periodically
        message_count = 0

        while True:
            # Simulate sensor readings
            temperature = round(random.uniform(20.0, 30.0), 2)
            humidity = round(random.uniform(40.0, 60.0), 2)

            # Create message payload
            payload = {
                "device_id": device_id,
                "timestamp": datetime.now().isoformat(),
                "temperature": temperature,
                "humidity": humidity,
                "unit": "celsius",
                "battery": random.randint(80, 100)
            }

            # Publish message
            message_json = json.dumps(payload)
            result = client.publish(topic, message_json, qos=1)

            if result.rc == 0:
                message_count += 1
                print(f"[{message_count}] Published: Temp={temperature}°C, Humidity={humidity}%")
            else:
                print(f"✗ Failed to publish message")

            # Wait before next reading
            time.sleep(5)

    except ConnectionRefusedError:
        print(f"\n✗ Connection refused. Is the MQTT broker running at {broker_host}:{broker_port}?")

    except KeyboardInterrupt:
        print(f"\n\nStopping MQTT client...")
        print(f"Total messages published: {message_count}")

    finally:
        client.loop_stop()
        client.disconnect()
        print("Client disconnected")


def main():
    """Main function"""
    import sys

    # Default broker settings
    broker_host = 'localhost'
    broker_port = 1883

    # Allow broker host/port as command line arguments
    if len(sys.argv) > 1:
        broker_host = sys.argv[1]

    if len(sys.argv) > 2:
        try:
            broker_port = int(sys.argv[2])
        except ValueError:
            print(f"Error: Invalid port number '{sys.argv[2]}'")
            return

    simulate_mqtt_client(broker_host, broker_port)


if __name__ == "__main__":
    main()
