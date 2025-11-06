# c:\Users\Codeternal\Desktop\AgroPulse\app\iot\fleet_management\communication.py

"""
Fleet Communication Service
===========================

This module simulates the communication layer for the fleet management system,
handling incoming data from vehicles, which would typically be transmitted over
a protocol like MQTT. It provides a bridge between the raw data from IoT devices
and the structured `FleetRegistry`.

Key Components:
-------------
1.  **`FleetCommunicationService`**:
    -   **Purpose**: Manages the connection to a (simulated) MQTT broker and
      processes incoming messages.
    -   **Singleton Pattern**: Ensures a single instance manages all communication,
      preventing duplicate connections or message handlers.
    -   **`connect()`**: Simulates connecting to an MQTT broker. In a real
      implementation with a library like `paho-mqtt`, this is where the client
      would be configured and the connection established.
    -   **`subscribe_to_topics()`**: Subscribes the client to relevant MQTT topics,
      such as `fleet/+/telemetry`, where `+` is a wildcard for the vehicle ID.
      This allows a single subscription to capture telemetry from all vehicles.
    -   **`on_message_received()`**: The callback function that is triggered when a
      message arrives. It parses the topic to get the `vehicle_id`, decodes the
      JSON payload, validates it using the `TelemetryData` model, and then uses
      the `FleetRegistry` to update the vehicle's state.
    -   **`publish_command()`**: Allows the backend to send commands back to a
      vehicle (e.g., 'start_mission', 'return_to_base'). This demonstrates
      bidirectional communication.

2.  **Simulation (`start_simulation` function)**:
    -   **Purpose**: To demonstrate the communication service in action without
      needing a live fleet of vehicles or a real MQTT broker.
    -   **Process**:
        -   It selects a random vehicle from the registry.
        -   It generates a realistic, slightly modified telemetry payload by
          simulating movement and changes in fuel/battery level.
        -   It serializes this payload to a JSON string.
        -   It calls the `on_message_received` method directly to simulate an
          MQTT message arriving for that vehicle.
        -   It runs this process in a loop in a separate thread to mimic a
          continuous stream of incoming data.

This module is crucial for decoupling the core fleet management logic from the
specifics of the communication protocol. It provides a clear point of entry for
all data originating from the fleet's IoT devices.
"""

import json
import time
import random
import threading
import logging
from typing import Dict, Optional

from .registry import get_fleet_registry
from .vehicle import TelemetryData, Location, Vehicle

# In a real application, you would use a library like paho-mqtt
# from paho.mqtt import client as mqtt_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FleetCommunicationService:
    """
    Manages communication with the vehicle fleet, typically via MQTT.
    This is a simulated version.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, broker: str = 'localhost', port: int = 1883):
        if not hasattr(self, '_initialized'):
            self.broker = broker
            self.port = port
            self.client_id = f'fleet-service-{random.randint(0, 1000)}'
            # self.client = mqtt_client.Client(self.client_id) # Real implementation
            self._connected = False
            self._registry = get_fleet_registry()
            self._simulation_thread = None
            self._stop_simulation_event = threading.Event()
            self._initialized = True
            logging.info("FleetCommunicationService initialized.")

    def connect(self):
        """Simulates connecting to the MQTT broker."""
        # In a real implementation:
        # self.client.on_connect = self._on_connect
        # self.client.on_message = self.on_message_received
        # self.client.connect(self.broker, self.port)
        # self.client.loop_start()
        self._connected = True
        logging.info(f"Simulated connection to MQTT broker at {self.broker}:{self.port}")

    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when the client connects to the broker."""
        if rc == 0:
            self._connected = True
            logging.info("Connected to MQTT Broker!")
            self.subscribe_to_topics()
        else:
            logging.error(f"Failed to connect, return code {rc}\n")

    def subscribe_to_topics(self):
        """Subscribes to all relevant fleet topics."""
        # The '+' is a single-level wildcard for the vehicle ID
        telemetry_topic = "fleet/+/telemetry"
        status_topic = "fleet/+/status"
        # self.client.subscribe([(telemetry_topic, 0), (status_topic, 0)])
        logging.info(f"Simulated subscription to topics: '{telemetry_topic}', '{status_topic}'")

    def on_message_received(self, topic: str, payload: str):
        """
        Callback for processing messages from subscribed topics.
        This method would be called by the MQTT client library.
        """
        logging.debug(f"Received message on topic '{topic}': {payload}")
        parts = topic.split('/')
        if len(parts) != 3:
            logging.warning(f"Ignoring malformed topic: {topic}")
            return

        vehicle_id = parts[1]
        message_type = parts[2]

        vehicle = self._registry.get_vehicle(vehicle_id)
        if not vehicle:
            logging.warning(f"Received message for unknown vehicle ID: {vehicle_id}")
            return

        try:
            data = json.loads(payload)
            if message_type == "telemetry":
                telemetry = TelemetryData(**data)
                self._registry.update_telemetry(vehicle_id, telemetry)
            elif message_type == "status":
                # Example of handling a different type of message
                # Here we could update the vehicle status directly
                pass
            else:
                logging.warning(f"Unknown message type '{message_type}' on topic '{topic}'")

        except (json.JSONDecodeError, TypeError) as e:
            logging.error(f"Error processing message payload for topic '{topic}': {e}")

    def publish_command(self, vehicle_id: str, command: Dict):
        """
        Publishes a command to a specific vehicle.
        """
        topic = f"fleet/{vehicle_id}/commands"
        payload = json.dumps(command)
        # self.client.publish(topic, payload)
        logging.info(f"Simulated publish to topic '{topic}': {payload}")

    def start_simulation(self, interval_seconds: int = 10):
        """Starts a background thread to simulate incoming telemetry data."""
        if self._simulation_thread is not None and self._simulation_thread.is_alive():
            logging.warning("Simulation is already running.")
            return

        self._stop_simulation_event.clear()
        self._simulation_thread = threading.Thread(
            target=self._simulation_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self._simulation_thread.start()
        logging.info(f"Telemetry simulation started, updating every {interval_seconds} seconds.")

    def stop_simulation(self):
        """Stops the telemetry simulation thread."""
        if self._simulation_thread and self._simulation_thread.is_alive():
            self._stop_simulation_event.set()
            self._simulation_thread.join()
            logging.info("Telemetry simulation stopped.")

    def _simulation_loop(self, interval_seconds: int):
        """The actual loop that generates and 'receives' telemetry data."""
        while not self._stop_simulation_event.is_set():
            vehicles = self._registry.get_all_vehicles()
            if not vehicles:
                time.sleep(interval_seconds)
                continue

            # Select a random vehicle to send an update
            vehicle_to_update = random.choice(vehicles)
            
            # Generate new telemetry data based on the old data
            new_telemetry = self._generate_simulated_telemetry(vehicle_to_update)
            
            # Simulate receiving this data
            topic = f"fleet/{vehicle_to_update.vehicle_id}/telemetry"
            payload = new_telemetry.json()
            
            self.on_message_received(topic, payload)
            
            time.sleep(interval_seconds)

    def _generate_simulated_telemetry(self, vehicle: Vehicle) -> TelemetryData:
        """Generates a new TelemetryData point based on the vehicle's last known state."""
        if vehicle.current_telemetry and vehicle.current_telemetry.location:
            last_loc = vehicle.current_telemetry.location
            new_lat = last_loc.latitude + random.uniform(-0.001, 0.001)
            new_lon = last_loc.longitude + random.uniform(-0.001, 0.001)
            
            last_fuel = vehicle.current_telemetry.fuel_level_percent
            new_fuel = max(0, last_fuel - random.uniform(0.1, 0.5)) if last_fuel else None

            last_battery = vehicle.current_telemetry.battery_level_percent
            new_battery = max(0, last_battery - random.uniform(0.2, 1.0)) if last_battery else None
        else:
            # Default starting point if no telemetry exists
            new_lat, new_lon = 34.05, -118.24
            new_fuel, new_battery = 100.0, 100.0

        return TelemetryData(
            location=Location(latitude=new_lat, longitude=new_lon),
            speed_kph=random.uniform(5, 20),
            fuel_level_percent=new_fuel if vehicle.vehicle_type != VehicleType.DRONE else None,
            battery_level_percent=new_battery if vehicle.vehicle_type == VehicleType.DRONE else None,
            engine_temp_celsius=random.uniform(85, 95) if vehicle.vehicle_type == VehicleType.TRACTOR else None,
            engine_rpm=random.randint(1500, 2200) if vehicle.vehicle_type == VehicleType.TRACTOR else None
        )

def get_communication_service() -> FleetCommunicationService:
    """Global accessor for the FleetCommunicationService singleton."""
    return FleetCommunicationService()

# Example Usage
if __name__ == "__main__":
    # 1. Get services
    registry = get_fleet_registry()
    comm_service = get_communication_service()

    # 2. Add a vehicle to the registry if it's empty
    if not registry.get_all_vehicles():
        tractor = Vehicle(vin="SIMTRACTOR00000001", make="SimBrand", model="SimModel", year=2023, vehicle_type="tractor")
        drone = Vehicle(vin="SIMDRONE0000000001", make="SimDJI", model="SimAgras", year=2023, vehicle_type="drone")
        registry.add_vehicle(tractor)
        registry.add_vehicle(drone)

    # 3. Connect and subscribe
    comm_service.connect()
    comm_service.subscribe_to_topics()

    # 4. Start the simulation
    comm_service.start_simulation(interval_seconds=5)

    # 5. Run for a while and observe the logs
    try:
        logging.info("Running simulation for 30 seconds. Check logs for telemetry updates.")
        for i in range(30):
            vehicle_id = "SIMTRACTOR00000001"
            vehicle = registry.get_vehicle(vehicle_id)
            if vehicle and vehicle.current_telemetry:
                print(f"Time {i}s: Tractor at ({vehicle.current_telemetry.location.latitude:.4f}, {vehicle.current_telemetry.location.longitude:.4f}) with fuel {vehicle.current_telemetry.fuel_level_percent:.1f}%")
            time.sleep(1)
        
        # 6. Publish a command
        comm_service.publish_command(vehicle_id, {"command": "set_speed", "value": 10})

    except KeyboardInterrupt:
        logging.info("Interrupted by user.")
    finally:
        # 7. Stop the simulation
        comm_service.stop_simulation()
        logging.info("Application finished.")
```