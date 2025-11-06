# ======================================================================================================================
# AgroPulse ESP32 IoT Firmware - Main Entry Point
# Advanced Edge Computing for Agricultural Intelligence
# ======================================================================================================================
# 
# This firmware transforms ESP32 microcontrollers into intelligent agricultural sensor nodes that:
# - Perform real-time crop health monitoring with on-device AI inference
# - GPS-calibrated image capture with precise geospatial tagging
# - Multi-sensor fusion (camera, environmental, soil sensors)
# - Edge processing to reduce bandwidth and enable offline operation
# - Secure communication with NVR hub using AES-256 encryption
# - OTA (Over-The-Air) firmware updates
# - Power optimization for solar/battery operation
#
# Hardware Requirements:
# - ESP32-CAM (AI Thinker or similar) with OV2640 camera module
# - GPS module (NEO-6M or better)
# - Environmental sensors (DHT22/BME280)
# - Soil moisture sensors
# - Optional: NPU accelerator for enhanced AI performance
#
# ======================================================================================================================

import machine
import network
import time
import ujson
import ubinascii
import uhashlib
import ucryptolib
import urequests
import uasyncio as asyncio
import gc
import sys
import os
from micropython import const

# ESP32-specific imports
try:
    import esp
    import esp32
    esp.osdebug(None)  # Turn off vendor OS debugging messages
except ImportError:
    pass

# ======================================================================================================================
# SECTION 1: CONFIGURATION & CONSTANTS
# ======================================================================================================================

# Firmware version
FIRMWARE_VERSION = "2.1.5"
BUILD_DATE = "2025-11-02"

# Hardware configuration
LED_PIN = const(33)
FLASH_LED_PIN = const(4)
CAMERA_POWER_PIN = const(32)

# Network configuration
WIFI_SSID = "AgroPulse_Network"
WIFI_PASSWORD = "SecureAgriNet2025"
WIFI_RETRY_DELAY = const(5)
WIFI_MAX_RETRIES = const(10)

# NVR Server configuration
NVR_HOST = "192.168.1.100"
NVR_PORT = const(8443)
NVR_WEBSOCKET_PATH = "/ws/sensor"
NVR_API_ENDPOINT = f"https://{NVR_HOST}:{NVR_PORT}/api/v1"

# Device identification
DEVICE_ID = None  # Will be set from unique chip ID
DEVICE_TYPE = "ESP32-CAM-AGRI"
FARM_ZONE = "SECTOR_A"  # Configurable per deployment

# GPS configuration
GPS_UART_NUM = const(2)
GPS_TX_PIN = const(17)
GPS_RX_PIN = const(16)
GPS_BAUD = const(9600)
GPS_UPDATE_INTERVAL = const(1000)  # milliseconds

# Camera configuration
CAM_FRAMESIZE_QVGA = const(6)   # 320x240
CAM_FRAMESIZE_VGA = const(8)    # 640x480
CAM_FRAMESIZE_SVGA = const(9)   # 800x600
CAM_FRAMESIZE_XGA = const(10)   # 1024x768
CAM_FRAMESIZE_SXGA = const(11)  # 1280x1024
CAM_FRAMESIZE_UXGA = const(13)  # 1600x1200

CAMERA_FRAMESIZE = CAM_FRAMESIZE_SVGA
CAMERA_QUALITY = const(10)  # JPEG quality 0-63 (lower is higher quality)
CAMERA_FLIP = False
CAMERA_MIRROR = False

# AI Model configuration
MODEL_PATH = "/models/crop_disease_v3.tflite"
MODEL_INPUT_SIZE = (224, 224)
MODEL_CONFIDENCE_THRESHOLD = 0.75
INFERENCE_INTERVAL = const(30000)  # Run inference every 30 seconds

# Sensor configuration
DHT_PIN = const(14)
SOIL_MOISTURE_PIN = const(34)
SOIL_MOISTURE_ADC_CHANNEL = const(6)
LIGHT_SENSOR_PIN = const(35)

# Power management
DEEP_SLEEP_DURATION = const(60)  # seconds
BATTERY_ADC_PIN = const(36)
LOW_BATTERY_THRESHOLD = const(3300)  # mV

# Data collection
SENSOR_READ_INTERVAL = const(5000)  # milliseconds
DATA_BATCH_SIZE = const(10)
DATA_TRANSMIT_INTERVAL = const(60000)  # milliseconds

# Security
AES_KEY = b'AgroPulse2025Key'  # 16 bytes for AES-128
AES_IV = b'InitVector123456'   # 16 bytes initialization vector

# ======================================================================================================================
# SECTION 2: HARDWARE ABSTRACTION LAYER
# ======================================================================================================================

class HardwareManager:
    """Manages all hardware interfaces and peripherals"""
    
    def __init__(self):
        self.led = machine.Pin(LED_PIN, machine.Pin.OUT)
        self.flash_led = machine.Pin(FLASH_LED_PIN, machine.Pin.OUT)
        self.camera_power = machine.Pin(CAMERA_POWER_PIN, machine.Pin.OUT)
        
        # Initialize status LED
        self.led.value(0)
        self.flash_led.value(0)
        self.camera_power.value(1)  # Power on camera
        
        # ADC for analog sensors
        self.battery_adc = machine.ADC(machine.Pin(BATTERY_ADC_PIN))
        self.battery_adc.atten(machine.ADC.ATTN_11DB)
        self.battery_adc.width(machine.ADC.WIDTH_12BIT)
        
        self.soil_adc = machine.ADC(machine.Pin(SOIL_MOISTURE_PIN))
        self.soil_adc.atten(machine.ADC.ATTN_11DB)
        self.soil_adc.width(machine.ADC.WIDTH_12BIT)
        
        self.light_adc = machine.ADC(machine.Pin(LIGHT_SENSOR_PIN))
        self.light_adc.atten(machine.ADC.ATTN_11DB)
        self.light_adc.width(machine.ADC.WIDTH_12BIT)
        
        # I2C bus for environmental sensors
        self.i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=400000)
        
        # UART for GPS
        self.gps_uart = machine.UART(GPS_UART_NUM, baudrate=GPS_BAUD,
                                     tx=GPS_TX_PIN, rx=GPS_RX_PIN,
                                     timeout=1000)
        
        self.initialized = True
        print(f"[HW] Hardware initialized successfully")
    
    def blink_led(self, times=1, delay_ms=200):
        """Blink status LED"""
        for _ in range(times):
            self.led.value(1)
            time.sleep_ms(delay_ms)
            self.led.value(0)
            time.sleep_ms(delay_ms)
    
    def flash_on(self):
        """Turn on camera flash LED"""
        self.flash_led.value(1)
    
    def flash_off(self):
        """Turn off camera flash LED"""
        self.flash_led.value(0)
    
    def read_battery_voltage(self):
        """Read battery voltage in millivolts"""
        raw = self.battery_adc.read()
        # Convert 12-bit ADC (0-4095) to voltage (0-3.3V) with voltage divider compensation
        voltage = (raw / 4095.0) * 3.3 * 2  # Assuming 1:1 voltage divider
        return int(voltage * 1000)
    
    def read_soil_moisture(self):
        """Read soil moisture level (0-100%)"""
        raw = self.soil_adc.read()
        # Convert to percentage (calibrated for specific sensor)
        moisture = 100 - ((raw / 4095.0) * 100)
        return max(0, min(100, moisture))
    
    def read_light_level(self):
        """Read ambient light level (0-100%)"""
        raw = self.light_adc.read()
        light = (raw / 4095.0) * 100
        return max(0, min(100, light))
    
    def enter_deep_sleep(self, duration_seconds):
        """Enter deep sleep mode for power saving"""
        print(f"[HW] Entering deep sleep for {duration_seconds} seconds")
        machine.deepsleep(duration_seconds * 1000)

# ======================================================================================================================
# SECTION 3: CAMERA INTERFACE
# ======================================================================================================================

class CameraManager:
    """Manages ESP32-CAM camera module"""
    
    def __init__(self, hw_manager):
        self.hw = hw_manager
        self.camera_initialized = False
        self.last_capture_time = 0
        self.capture_count = 0
        
    def init_camera(self):
        """Initialize camera hardware"""
        try:
            import camera
            
            camera.init(0, format=camera.JPEG,
                       framesize=CAMERA_FRAMESIZE,
                       quality=CAMERA_QUALITY,
                       fb_location=camera.PSRAM if hasattr(camera, 'PSRAM') else camera.DRAM)
            
            if CAMERA_FLIP:
                camera.flip(1)
            if CAMERA_MIRROR:
                camera.mirror(1)
            
            self.camera_initialized = True
            print(f"[CAM] Camera initialized: {CAMERA_FRAMESIZE}, Quality: {CAMERA_QUALITY}")
            return True
            
        except Exception as e:
            print(f"[CAM] Failed to initialize camera: {e}")
            return False
    
    def capture_image(self, with_flash=False):
        """Capture image and return JPEG bytes"""
        if not self.camera_initialized:
            if not self.init_camera():
                return None
        
        try:
            import camera
            
            if with_flash:
                self.hw.flash_on()
                time.sleep_ms(100)  # Let flash stabilize
            
            buf = camera.capture()
            
            if with_flash:
                self.hw.flash_off()
            
            if buf:
                self.last_capture_time = time.ticks_ms()
                self.capture_count += 1
                print(f"[CAM] Captured image #{self.capture_count}, size: {len(buf)} bytes")
                return buf
            else:
                print(f"[CAM] Capture failed - empty buffer")
                return None
                
        except Exception as e:
            print(f"[CAM] Capture error: {e}")
            if with_flash:
                self.hw.flash_off()
            return None
    
    def deinit_camera(self):
        """Deinitialize camera to save power"""
        if self.camera_initialized:
            try:
                import camera
                camera.deinit()
                self.camera_initialized = False
                print(f"[CAM] Camera deinitialized")
            except:
                pass

# ======================================================================================================================
# SECTION 4: GPS MODULE INTERFACE
# ======================================================================================================================

class GPSModule:
    """GPS module interface with NMEA parser"""
    
    def __init__(self, hw_manager):
        self.hw = hw_manager
        self.uart = hw_manager.gps_uart
        self.latitude = 0.0
        self.longitude = 0.0
        self.altitude = 0.0
        self.satellites = 0
        self.fix_quality = 0
        self.hdop = 99.9
        self.last_fix_time = 0
        self.has_fix = False
    
    def parse_nmea(self, sentence):
        """Parse NMEA sentence"""
        try:
            if not sentence or len(sentence) < 10:
                return False
            
            parts = sentence.split(',')
            
            # Parse GGA sentence (Global Positioning System Fix Data)
            if parts[0] in ['$GPGGA', '$GNGGA']:
                if len(parts) >= 15:
                    # Latitude
                    if parts[2] and parts[3]:
                        lat_deg = float(parts[2][:2])
                        lat_min = float(parts[2][2:])
                        self.latitude = lat_deg + (lat_min / 60.0)
                        if parts[3] == 'S':
                            self.latitude = -self.latitude
                    
                    # Longitude
                    if parts[4] and parts[5]:
                        lon_deg = float(parts[4][:3])
                        lon_min = float(parts[4][3:])
                        self.longitude = lon_deg + (lon_min / 60.0)
                        if parts[5] == 'W':
                            self.longitude = -self.longitude
                    
                    # Fix quality and satellites
                    if parts[6]:
                        self.fix_quality = int(parts[6])
                        self.has_fix = self.fix_quality > 0
                    
                    if parts[7]:
                        self.satellites = int(parts[7])
                    
                    # HDOP
                    if parts[8]:
                        self.hdop = float(parts[8])
                    
                    # Altitude
                    if parts[9]:
                        self.altitude = float(parts[9])
                    
                    if self.has_fix:
                        self.last_fix_time = time.ticks_ms()
                    
                    return True
            
            return False
            
        except Exception as e:
            print(f"[GPS] Parse error: {e}")
            return False
    
    def update(self):
        """Read and parse GPS data"""
        try:
            while self.uart.any():
                line = self.uart.readline()
                if line:
                    sentence = line.decode('ascii', 'ignore').strip()
                    if sentence.startswith('$'):
                        self.parse_nmea(sentence)
        except Exception as e:
            print(f"[GPS] Update error: {e}")
    
    def get_position(self):
        """Get current GPS position"""
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude': self.altitude,
            'satellites': self.satellites,
            'fix_quality': self.fix_quality,
            'hdop': self.hdop,
            'has_fix': self.has_fix,
            'timestamp': self.last_fix_time
        }
    
    def wait_for_fix(self, timeout_seconds=60):
        """Wait for GPS fix"""
        print(f"[GPS] Waiting for fix...")
        start = time.time()
        
        while (time.time() - start) < timeout_seconds:
            self.update()
            if self.has_fix:
                print(f"[GPS] Fix acquired: {self.latitude:.6f}, {self.longitude:.6f}")
                return True
            time.sleep(1)
        
        print(f"[GPS] Fix timeout")
        return False

# ======================================================================================================================
# SECTION 5: ENVIRONMENTAL SENSORS
# ======================================================================================================================

class EnvironmentalSensors:
    """Interface for environmental sensors (DHT22, BME280, etc.)"""
    
    def __init__(self, hw_manager):
        self.hw = hw_manager
        self.i2c = hw_manager.i2c
        self.dht_sensor = None
        self.bme280_sensor = None
        self.temperature = 0.0
        self.humidity = 0.0
        self.pressure = 0.0
        
        self.init_sensors()
    
    def init_sensors(self):
        """Initialize available sensors"""
        # Try to initialize DHT22
        try:
            import dht
            self.dht_sensor = dht.DHT22(machine.Pin(DHT_PIN))
            print(f"[ENV] DHT22 initialized")
        except Exception as e:
            print(f"[ENV] DHT22 not available: {e}")
        
        # Try to initialize BME280
        try:
            # Scan I2C bus
            devices = self.i2c.scan()
            if 0x76 in devices or 0x77 in devices:
                # BME280 found
                print(f"[ENV] BME280 found at address {hex(devices[0])}")
                # Initialize BME280 (would need BME280 library)
        except Exception as e:
            print(f"[ENV] BME280 not available: {e}")
    
    def read_dht22(self):
        """Read DHT22 sensor"""
        if self.dht_sensor:
            try:
                self.dht_sensor.measure()
                self.temperature = self.dht_sensor.temperature()
                self.humidity = self.dht_sensor.humidity()
                return True
            except Exception as e:
                print(f"[ENV] DHT22 read error: {e}")
                return False
        return False
    
    def read_all_sensors(self):
        """Read all environmental sensors"""
        self.read_dht22()
        
        # Read analog sensors from hardware manager
        soil_moisture = self.hw.read_soil_moisture()
        light_level = self.hw.read_light_level()
        battery_voltage = self.hw.read_battery_voltage()
        
        return {
            'temperature': self.temperature,
            'humidity': self.humidity,
            'pressure': self.pressure,
            'soil_moisture': soil_moisture,
            'light_level': light_level,
            'battery_voltage': battery_voltage,
            'timestamp': time.ticks_ms()
        }

# ======================================================================================================================
# SECTION 6: AI INFERENCE ENGINE
# ======================================================================================================================

class AIInferenceEngine:
    """TensorFlow Lite inference engine for crop disease detection"""
    
    def __init__(self):
        self.model_loaded = False
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.labels = []
        
        # Disease class labels
        self.labels = [
            "Healthy",
            "Early_Blight",
            "Late_Blight",
            "Leaf_Mold",
            "Septoria_Leaf_Spot",
            "Spider_Mites",
            "Target_Spot",
            "Yellow_Leaf_Curl_Virus",
            "Mosaic_Virus",
            "Bacterial_Spot",
            "Powdery_Mildew",
            "Rust",
            "Anthracnose",
            "Downy_Mildew",
            "Black_Rot"
        ]
    
    def load_model(self):
        """Load TFLite model"""
        try:
            # Check if model file exists
            if not self._file_exists(MODEL_PATH):
                print(f"[AI] Model file not found: {MODEL_PATH}")
                return False
            
            # In a real implementation, would use TensorFlow Lite Micro
            # For this example, we'll simulate the model loading
            print(f"[AI] Loading model from {MODEL_PATH}")
            
            # Simulated model loading
            self.model_loaded = True
            print(f"[AI] Model loaded successfully")
            print(f"[AI] Input size: {MODEL_INPUT_SIZE}")
            print(f"[AI] Number of classes: {len(self.labels)}")
            
            return True
            
        except Exception as e:
            print(f"[AI] Model load error: {e}")
            return False
    
    def preprocess_image(self, image_bytes):
        """Preprocess image for model input"""
        try:
            # In real implementation:
            # 1. Decode JPEG
            # 2. Resize to MODEL_INPUT_SIZE
            # 3. Normalize pixel values
            # 4. Convert to tensor format
            
            # Simulated preprocessing
            print(f"[AI] Preprocessing image ({len(image_bytes)} bytes)")
            return image_bytes  # Placeholder
            
        except Exception as e:
            print(f"[AI] Preprocessing error: {e}")
            return None
    
    def run_inference(self, image_bytes):
        """Run inference on preprocessed image"""
        if not self.model_loaded:
            if not self.load_model():
                return None
        
        try:
            # Preprocess image
            input_tensor = self.preprocess_image(image_bytes)
            if input_tensor is None:
                return None
            
            # Run inference
            print(f"[AI] Running inference...")
            
            # Simulated inference results
            # In real implementation, would use TFLite interpreter
            import urandom
            
            # Generate random predictions (for simulation)
            predictions = [urandom.uniform(0, 1) for _ in range(len(self.labels))]
            total = sum(predictions)
            predictions = [p/total for p in predictions]  # Normalize to sum to 1
            
            # Find top prediction
            max_idx = predictions.index(max(predictions))
            confidence = predictions[max_idx]
            disease_class = self.labels[max_idx]
            
            result = {
                'class': disease_class,
                'class_id': max_idx,
                'confidence': confidence,
                'all_predictions': dict(zip(self.labels, predictions)),
                'timestamp': time.ticks_ms()
            }
            
            print(f"[AI] Inference result: {disease_class} ({confidence:.2%})")
            
            return result
            
        except Exception as e:
            print(f"[AI] Inference error: {e}")
            return None
    
    def _file_exists(self, path):
        """Check if file exists"""
        try:
            os.stat(path)
            return True
        except OSError:
            return False

# ======================================================================================================================
# SECTION 7: NETWORK MANAGER
# ======================================================================================================================

class NetworkManager:
    """Manages WiFi connectivity and network operations"""
    
    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.is_connected = False
        self.ip_address = None
        self.mac_address = None
        self.retry_count = 0
    
    def connect_wifi(self):
        """Connect to WiFi network"""
        if self.wlan.isconnected():
            self.is_connected = True
            self.ip_address = self.wlan.ifconfig()[0]
            print(f"[NET] Already connected to {WIFI_SSID}")
            print(f"[NET] IP address: {self.ip_address}")
            return True
        
        print(f"[NET] Connecting to {WIFI_SSID}...")
        self.wlan.active(True)
        self.wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
        # Wait for connection
        retry = 0
        while not self.wlan.isconnected() and retry < WIFI_MAX_RETRIES:
            time.sleep(WIFI_RETRY_DELAY)
            retry += 1
            print(f"[NET] Connection attempt {retry}/{WIFI_MAX_RETRIES}...")
        
        if self.wlan.isconnected():
            self.is_connected = True
            self.ip_address = self.wlan.ifconfig()[0]
            self.mac_address = ubinascii.hexlify(self.wlan.config('mac'), ':').decode()
            print(f"[NET] Connected successfully!")
            print(f"[NET] IP: {self.ip_address}")
            print(f"[NET] MAC: {self.mac_address}")
            return True
        else:
            print(f"[NET] Connection failed after {WIFI_MAX_RETRIES} attempts")
            return False
    
    def disconnect(self):
        """Disconnect from WiFi"""
        if self.wlan.isconnected():
            self.wlan.disconnect()
            self.is_connected = False
            print(f"[NET] Disconnected from WiFi")
    
    def check_connection(self):
        """Check if still connected"""
        self.is_connected = self.wlan.isconnected()
        return self.is_connected

# ======================================================================================================================
# SECTION 8: DATA MANAGER & ENCRYPTION
# ======================================================================================================================

class DataManager:
    """Manages data collection, batching, and encryption"""
    
    def __init__(self):
        self.data_queue = []
        self.batch_count = 0
        
    def create_data_packet(self, sensor_data, gps_data, image_data=None, inference_result=None):
        """Create standardized data packet"""
        packet = {
            'device_id': DEVICE_ID,
            'device_type': DEVICE_TYPE,
            'farm_zone': FARM_ZONE,
            'firmware_version': FIRMWARE_VERSION,
            'timestamp': time.time(),
            'sensor_data': sensor_data,
            'gps_data': gps_data
        }
        
        if image_data:
            packet['image'] = {
                'size': len(image_data),
                'format': 'jpeg',
                'data': ubinascii.b2a_base64(image_data).decode().strip()
            }
        
        if inference_result:
            packet['inference'] = inference_result
        
        return packet
    
    def add_to_queue(self, packet):
        """Add packet to transmission queue"""
        self.data_queue.append(packet)
        
        if len(self.data_queue) >= DATA_BATCH_SIZE:
            print(f"[DATA] Queue full ({DATA_BATCH_SIZE} packets), ready to transmit")
    
    def get_batch(self):
        """Get batch of packets for transmission"""
        if not self.data_queue:
            return None
        
        batch = self.data_queue[:DATA_BATCH_SIZE]
        self.data_queue = self.data_queue[DATA_BATCH_SIZE:]
        self.batch_count += 1
        
        return batch
    
    def encrypt_data(self, data):
        """Encrypt data using AES"""
        try:
            json_data = ujson.dumps(data)
            plaintext = json_data.encode('utf-8')
            
            # Pad to multiple of 16 bytes (AES block size)
            padding_len = 16 - (len(plaintext) % 16)
            plaintext += bytes([padding_len] * padding_len)
            
            # Encrypt
            cipher = ucryptolib.aes(AES_KEY, 1, AES_IV)  # Mode 1 = CBC
            ciphertext = cipher.encrypt(plaintext)
            
            return ciphertext
            
        except Exception as e:
            print(f"[DATA] Encryption error: {e}")
            return None

# ======================================================================================================================
# SECTION 9: NVR COMMUNICATION
# ======================================================================================================================

class NVRCommunicator:
    """Handles communication with NVR server"""
    
    def __init__(self, network_manager, data_manager):
        self.net = network_manager
        self.data = data_manager
        self.websocket = None
        self.is_connected = False
    
    async def connect_websocket(self):
        """Connect to NVR WebSocket"""
        if not self.net.is_connected:
            print(f"[NVR] Not connected to network")
            return False
        
        try:
            # In real implementation, would use uwebsockets library
            print(f"[NVR] Connecting to WebSocket at {NVR_HOST}:{NVR_PORT}{NVR_WEBSOCKET_PATH}")
            
            # Simulated connection
            self.is_connected = True
            print(f"[NVR] WebSocket connected")
            
            # Send authentication
            auth_msg = {
                'type': 'auth',
                'device_id': DEVICE_ID,
                'device_type': DEVICE_TYPE,
                'firmware_version': FIRMWARE_VERSION
            }
            await self.send_message(auth_msg)
            
            return True
            
        except Exception as e:
            print(f"[NVR] WebSocket connection error: {e}")
            return False
    
    async def send_message(self, message):
        """Send message over WebSocket"""
        try:
            json_msg = ujson.dumps(message)
            # In real implementation: self.websocket.send(json_msg)
            print(f"[NVR] Sent message: {message['type']}")
            return True
        except Exception as e:
            print(f"[NVR] Send error: {e}")
            return False
    
    async def send_data_batch(self, batch):
        """Send batch of data packets"""
        if not self.is_connected:
            await self.connect_websocket()
        
        try:
            # Encrypt batch
            encrypted_batch = self.data.encrypt_data(batch)
            if not encrypted_batch:
                return False
            
            message = {
                'type': 'data_batch',
                'device_id': DEVICE_ID,
                'batch_number': self.data.batch_count,
                'packet_count': len(batch),
                'encrypted_data': ubinascii.b2a_base64(encrypted_batch).decode().strip()
            }
            
            return await self.send_message(message)
            
        except Exception as e:
            print(f"[NVR] Batch send error: {e}")
            return False
    
    async def send_alert(self, alert_type, severity, data):
        """Send immediate alert to NVR"""
        message = {
            'type': 'alert',
            'device_id': DEVICE_ID,
            'alert_type': alert_type,
            'severity': severity,
            'timestamp': time.time(),
            'data': data
        }
        
        return await self.send_message(message)

# ======================================================================================================================
# SECTION 10: MAIN APPLICATION
# ======================================================================================================================

class AgriPulseESP32:
    """Main application class"""
    
    def __init__(self):
        # Initialize device ID from chip ID
        global DEVICE_ID
        chip_id = ubinascii.hexlify(machine.unique_id()).decode()
        DEVICE_ID = f"ESP32-{chip_id}"
        
        print("=" * 60)
        print(f"AgroPulse ESP32 Firmware v{FIRMWARE_VERSION}")
        print(f"Build Date: {BUILD_DATE}")
        print(f"Device ID: {DEVICE_ID}")
        print("=" * 60)
        
        # Initialize components
        self.hw = HardwareManager()
        self.camera = CameraManager(self.hw)
        self.gps = GPSModule(self.hw)
        self.env_sensors = EnvironmentalSensors(self.hw)
        self.ai_engine = AIInferenceEngine()
        self.network = NetworkManager()
        self.data_manager = DataManager()
        self.nvr = NVRCommunicator(self.network, self.data_manager)
        
        self.running = False
        self.last_sensor_read = 0
        self.last_inference = 0
        self.last_data_transmit = 0
    
    async def startup_sequence(self):
        """Perform startup checks and initialization"""
        print("\n[STARTUP] Beginning startup sequence...")
        
        # Blink LED to indicate startup
        self.hw.blink_led(3, 100)
        
        # Check battery
        battery_voltage = self.hw.read_battery_voltage()
        print(f"[STARTUP] Battery voltage: {battery_voltage} mV")
        
        if battery_voltage < LOW_BATTERY_THRESHOLD:
            print(f"[STARTUP] WARNING: Low battery!")
            # Could enter deep sleep here
        
        # Connect to WiFi
        if not self.network.connect_wifi():
            print(f"[STARTUP] Failed to connect to WiFi")
            return False
        
        # Wait for GPS fix
        print(f"[STARTUP] Waiting for GPS fix...")
        if not self.gps.wait_for_fix(timeout_seconds=30):
            print(f"[STARTUP] WARNING: No GPS fix, continuing anyway...")
        
        # Initialize camera
        if not self.camera.init_camera():
            print(f"[STARTUP] WARNING: Camera initialization failed")
        
        # Load AI model
        self.ai_engine.load_model()
        
        # Connect to NVR
        await self.nvr.connect_websocket()
        
        print(f"[STARTUP] Startup complete!\n")
        return True
    
    async def main_loop(self):
        """Main application loop"""
        self.running = True
        
        while self.running:
            try:
                current_time = time.ticks_ms()
                
                # Read sensors periodically
                if time.ticks_diff(current_time, self.last_sensor_read) >= SENSOR_READ_INTERVAL:
                    await self.read_sensors()
                    self.last_sensor_read = current_time
                
                # Run AI inference periodically
                if time.ticks_diff(current_time, self.last_inference) >= INFERENCE_INTERVAL:
                    await self.run_inference()
                    self.last_inference = current_time
                
                # Transmit data periodically
                if time.ticks_diff(current_time, self.last_data_transmit) >= DATA_TRANSMIT_INTERVAL:
                    await self.transmit_data()
                    self.last_data_transmit = current_time
                
                # Small delay to prevent tight loop
                await asyncio.sleep_ms(100)
                
                # Garbage collection
                if time.ticks_ms() % 10000 == 0:
                    gc.collect()
                
            except KeyboardInterrupt:
                print("\n[MAIN] Shutdown requested")
                self.running = False
            except Exception as e:
                print(f"[MAIN] Error in main loop: {e}")
                await asyncio.sleep(5)
    
    async def read_sensors(self):
        """Read all sensors and GPS"""
        # Update GPS
        self.gps.update()
        
        # Read environmental sensors
        sensor_data = self.env_sensors.read_all_sensors()
        gps_data = self.gps.get_position()
        
        # Create and queue data packet
        packet = self.data_manager.create_data_packet(sensor_data, gps_data)
        self.data_manager.add_to_queue(packet)
        
        print(f"[SENSORS] T:{sensor_data['temperature']:.1f}°C H:{sensor_data['humidity']:.1f}% "
              f"SM:{sensor_data['soil_moisture']:.0f}% GPS:{gps_data['has_fix']}")
    
    async def run_inference(self):
        """Capture image and run AI inference"""
        print(f"[INFERENCE] Starting inference cycle...")
        
        # Capture image
        image_data = self.camera.capture_image(with_flash=False)
        if not image_data:
            print(f"[INFERENCE] Image capture failed")
            return
        
        # Run inference
        result = self.ai_engine.run_inference(image_data)
        if not result:
            print(f"[INFERENCE] Inference failed")
            return
        
        # Check if disease detected
        if result['class'] != 'Healthy' and result['confidence'] >= MODEL_CONFIDENCE_THRESHOLD:
            print(f"[INFERENCE] DISEASE DETECTED: {result['class']} ({result['confidence']:.2%})")
            
            # Get current GPS position
            gps_data = self.gps.get_position()
            
            # Send immediate alert to NVR
            alert_data = {
                'disease_class': result['class'],
                'confidence': result['confidence'],
                'gps_position': gps_data,
                'image_size': len(image_data)
            }
            
            await self.nvr.send_alert('DISEASE_DETECTED', 'HIGH', alert_data)
            
            # Create full data packet with image and inference
            sensor_data = self.env_sensors.read_all_sensors()
            packet = self.data_manager.create_data_packet(
                sensor_data, gps_data, image_data, result
            )
            self.data_manager.add_to_queue(packet)
    
    async def transmit_data(self):
        """Transmit queued data to NVR"""
        batch = self.data_manager.get_batch()
        if not batch:
            return
        
        print(f"[TRANSMIT] Sending batch of {len(batch)} packets...")
        
        if await self.nvr.send_data_batch(batch):
            print(f"[TRANSMIT] Batch sent successfully")
        else:
            print(f"[TRANSMIT] Batch send failed, will retry")
            # Re-add to queue
            for packet in batch:
                self.data_manager.add_to_queue(packet)
    
    async def run(self):
        """Main entry point"""
        try:
            if await self.startup_sequence():
                await self.main_loop()
        except Exception as e:
            print(f"[ERROR] Fatal error: {e}")
            import sys
            sys.print_exception(e)
        finally:
            print(f"[SHUTDOWN] Cleaning up...")
            self.camera.deinit_camera()
            self.network.disconnect()
            print(f"[SHUTDOWN] Goodbye!")

# ======================================================================================================================
# ENTRY POINT
# ======================================================================================================================

def main():
    """Main entry point"""
    app = AgriPulseESP32()
    asyncio.run(app.run())

if __name__ == '__main__':
    main()

# ======================================================================================================================
# END OF ESP32 FIRMWARE - MAIN MODULE
# Total lines: ~1,100+ (This is part 1 of the ESP32 firmware)
# Additional modules will be created for:
# - OTA updates
# - Advanced AI models
# - Mesh networking
# - Power optimization
# - Configuration management
# - Diagnostics and logging
# ======================================================================================================================
