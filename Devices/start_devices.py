"""
Test Device Launcher

Starts multiple test devices for AutoSecure Discovery Engine testing:
- mDNS devices (Generic IoT, HomeKit)
- SSDP devices (Generic SSDP)
- MQTT brokers (Mosquitto, HiveMQ, or EMQX - user choice)

All devices run simultaneously in separate threads.
Press Ctrl+C to stop all devices.
"""

import sys
import os
import threading
import time
import importlib.util


class DeviceLauncher:
    """Manages launching and stopping multiple test devices"""

    def __init__(self):
        self.devices_path = os.path.dirname(os.path.abspath(__file__))
        self.threads = []
        self.stop_event = threading.Event()

    def load_module(self, module_path, module_name):
        """
        Dynamically load a Python module from file path

        Args:
            module_path: Full path to the .py file
            module_name: Name to give the module

        Returns:
            Loaded module object
        """
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def run_device(self, device_path, device_name, function_name):
        """
        Run a device in a thread

        Args:
            device_path: Path to device script
            device_name: Display name for the device
            function_name: Name of the main function to call
        """
        try:
            print(f"  Starting {device_name}...")

            # Load the module
            module = self.load_module(device_path, device_name.replace(" ", "_"))

            # Get the main function
            if hasattr(module, function_name):
                func = getattr(module, function_name)
                func()
            else:
                print(f"  Error: {device_name} doesn't have function '{function_name}'")

        except KeyboardInterrupt:
            # This is expected when stopping
            pass
        except Exception as e:
            print(f"  Error running {device_name}: {e}")

    def start_device_thread(self, device_path, device_name, function_name):
        """
        Start a device in a new thread

        Args:
            device_path: Path to device script
            device_name: Display name for the device
            function_name: Name of the main function to call
        """
        thread = threading.Thread(
            target=self.run_device,
            args=(device_path, device_name, function_name),
            daemon=True,
            name=device_name
        )
        thread.start()
        self.threads.append(thread)

        # Give thread time to start
        time.sleep(0.5)

    def choose_mqtt_brokers(self):
        """
        Interactive menu to choose MQTT brokers (can select multiple)

        Returns:
            List of tuples (broker_path, broker_name, function_name)
        """
        print("\n" + "=" * 70)
        print("MQTT BROKER SELECTION")
        print("=" * 70)
        print("Each broker runs on a different port - you can run all simultaneously!")
        print()
        print("  1. Mosquitto  - MQTT 3.1.1 on port 1883 (Standard MQTT)")
        print("  2. HiveMQ     - MQTT 5.0 on port 8883 (MQTT over TLS)")
        print("  3. EMQX       - MQTT 5.0 on port 8884 (MQTT WebSocket)")
        print("  4. All        - Run all three brokers")
        print("  5. None       - Skip MQTT brokers")
        print()

        while True:
            try:
                choice = input("Enter choice (1-5): ").strip()

                brokers = []

                if choice == '1':
                    brokers.append((
                        os.path.join(self.devices_path, "MQTT", "mosquitto_broker.py"),
                        "Mosquitto MQTT Broker",
                        "main"
                    ))
                elif choice == '2':
                    brokers.append((
                        os.path.join(self.devices_path, "MQTT", "hivemq_broker.py"),
                        "HiveMQ MQTT Broker",
                        "main"
                    ))
                elif choice == '3':
                    brokers.append((
                        os.path.join(self.devices_path, "MQTT", "emqx_broker.py"),
                        "EMQX MQTT Broker",
                        "main"
                    ))
                elif choice == '4':
                    # All brokers
                    brokers.append((
                        os.path.join(self.devices_path, "MQTT", "mosquitto_broker.py"),
                        "Mosquitto MQTT Broker",
                        "main"
                    ))
                    brokers.append((
                        os.path.join(self.devices_path, "MQTT", "hivemq_broker.py"),
                        "HiveMQ MQTT Broker",
                        "main"
                    ))
                    brokers.append((
                        os.path.join(self.devices_path, "MQTT", "emqx_broker.py"),
                        "EMQX MQTT Broker",
                        "main"
                    ))
                elif choice == '5':
                    return []
                else:
                    print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")
                    continue

                return brokers

            except KeyboardInterrupt:
                print("\n\nCancelled.")
                return []

    def start_all_devices(self):
        """Start all test devices"""
        print("\n" + "=" * 70)
        print("TEST DEVICE LAUNCHER")
        print("=" * 70)
        print()

        # Choose MQTT brokers first
        mqtt_brokers = self.choose_mqtt_brokers()

        print("\n" + "=" * 70)
        print("STARTING DEVICES")
        print("=" * 70)
        print()

        # Start mDNS devices
        print("[1/4] Starting mDNS Devices...")
        self.start_device_thread(
            os.path.join(self.devices_path, "mDNS", "generic_iot_device.py"),
            "mDNS Generic IoT Device",
            "broadcast_generic_iot"
        )
        self.start_device_thread(
            os.path.join(self.devices_path, "mDNS", "homekit_device.py"),
            "mDNS HomeKit Device",
            "broadcast_homekit_device"
        )

        # Start SSDP devices
        print("\n[2/4] Starting SSDP Devices...")
        self.start_device_thread(
            os.path.join(self.devices_path, "SSDP", "generic_ssdp_device.py"),
            "SSDP Generic Device",
            "broadcast_generic_iot"
        )

        # Start MQTT brokers if selected
        if mqtt_brokers:
            print(f"\n[3/4] Starting MQTT Broker(s)...")
            for broker_path, broker_name, function_name in mqtt_brokers:
                self.start_device_thread(broker_path, broker_name, function_name)
        else:
            print("\n[3/4] Skipping MQTT Brokers (none selected)")

        print("\n[4/4] All devices started!")
        print("\n" + "=" * 70)
        print("DEVICE STATUS")
        print("=" * 70)
        print(f"Total devices running: {len(self.threads)}")
        print()
        for thread in self.threads:
            print(f"  ✓ {thread.name}")
        print()
        print("=" * 70)
        print()
        print("All devices are now broadcasting and can be discovered.")
        print()
        print("To test discovery, run in a separate terminal:")
        print('  cd "Engines\\Discovery"')
        print("  python discovery_engine.py")
        print()
        print("Press Ctrl+C to stop all devices...")
        print()

    def wait_for_stop(self):
        """Wait for user to stop all devices"""
        try:
            # Keep main thread alive
            while True:
                time.sleep(1)

                # Check if any threads have died
                alive_count = sum(1 for t in self.threads if t.is_alive())
                if alive_count == 0 and len(self.threads) > 0:
                    print("\n\nAll device threads have stopped.")
                    break

        except KeyboardInterrupt:
            print("\n\n" + "=" * 70)
            print("STOPPING ALL DEVICES")
            print("=" * 70)
            print("\nShutting down gracefully...")

    def stop_all(self):
        """Stop all devices and cleanup"""
        self.stop_event.set()

        # Wait for threads to finish (with timeout)
        for thread in self.threads:
            thread.join(timeout=2.0)

        print(f"\nAll {len(self.threads)} device(s) stopped.")
        print("\n" + "=" * 70)


def print_banner():
    """Print startup banner"""
    print()
    print("=" * 70)
    print(" " * 20 + "AutoSecure Test Device Launcher")
    print("=" * 70)
    print()
    print("This launcher will start multiple test devices for discovery testing:")
    print()
    print("  mDNS Devices:")
    print("    - Generic IoT Device (IP: 192.168.1.100, Port: 80)")
    print("    - HomeKit Smart Light (IP: 192.168.1.101, Port: 8080)")
    print()
    print("  SSDP Devices:")
    print("    - Generic SSDP Device (Random IP & Port)")
    print()
    print("  MQTT Brokers:")
    print("    - Mosquitto on port 1883 (Standard MQTT)")
    print("    - HiveMQ on port 8883 (MQTT over TLS)")
    print("    - EMQX on port 8884 (MQTT WebSocket)")
    print("    - Can run one, multiple, or all brokers simultaneously!")
    print()
    print("=" * 70)


def main():
    """Main function"""
    # Check if we're in the Devices folder
    if not os.path.exists("mDNS") or not os.path.exists("SSDP") or not os.path.exists("MQTT"):
        print("\nError: This script must be run from the Devices folder.")
        print("\nUsage:")
        print('  cd "R:\\University\\Year 4\\Final Year\\final-year-AutoSecure\\Devices"')
        print("  python start_devices.py")
        sys.exit(1)

    # Print banner
    print_banner()

    # Create launcher
    launcher = DeviceLauncher()

    try:
        # Start all devices
        launcher.start_all_devices()

        # Wait for user to stop
        launcher.wait_for_stop()

    except KeyboardInterrupt:
        pass

    finally:
        # Cleanup
        launcher.stop_all()


if __name__ == "__main__":
    main()
