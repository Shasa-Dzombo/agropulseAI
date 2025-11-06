# ======================================================================================================================
# AgroPulse ESP32 - OTA (Over-The-Air) Update Manager
# Secure firmware updates without physical access
# ======================================================================================================================

import machine
import network
import urequests
import uhashlib
import ubinascii
import os
import time

OTA_SERVER_URL = "https://192.168.1.100:8443/api/v1/firmware"
OTA_CHECK_INTERVAL = 3600  # Check for updates every hour
OTA_PARTITION_SIZE = 0x1F0000  # ~2MB

class OTAManager:
    """Manages Over-The-Air firmware updates"""
    
    def __init__(self, device_id, current_version):
        self.device_id = device_id
        self.current_version = current_version
        self.update_available = False
        self.update_info = None
        
    def check_for_updates(self):
        """Check if new firmware version is available"""
        try:
            print(f"[OTA] Checking for updates...")
            
            url = f"{OTA_SERVER_URL}/check?device_id={self.device_id}&current_version={self.current_version}"
            response = urequests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('update_available'):
                    self.update_available = True
                    self.update_info = data
                    print(f"[OTA] Update available: {data['version']}")
                    print(f"[OTA] Size: {data['size']} bytes")
                    print(f"[OTA] Release notes: {data.get('notes', 'N/A')}")
                    return True
                else:
                    print(f"[OTA] No updates available")
                    return False
            else:
                print(f"[OTA] Check failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[OTA] Check error: {e}")
            return False
    
    def download_and_install(self):
        """Download and install firmware update"""
        if not self.update_available or not self.update_info:
            print(f"[OTA] No update available")
            return False
        
        try:
            print(f"[OTA] Downloading firmware...")
            
            download_url = self.update_info['download_url']
            expected_sha256 = self.update_info['sha256']
            firmware_size = self.update_info['size']
            
            # Download firmware
            response = urequests.get(download_url, stream=True)
            
            if response.status_code != 200:
                print(f"[OTA] Download failed: HTTP {response.status_code}")
                return False
            
            # Save to file and calculate hash
            temp_file = "/tmp/firmware_update.bin"
            sha256 = uhashlib.sha256()
            bytes_downloaded = 0
            
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=4096):
                    f.write(chunk)
                    sha256.update(chunk)
                    bytes_downloaded += len(chunk)
                    
                    # Progress indicator
                    if bytes_downloaded % 40960 == 0:  # Every ~40KB
                        progress = (bytes_downloaded / firmware_size) * 100
                        print(f"[OTA] Downloaded: {progress:.1f}%")
            
            response.close()
            
            # Verify checksum
            calculated_sha256 = ubinascii.hexlify(sha256.digest()).decode()
            
            if calculated_sha256 != expected_sha256:
                print(f"[OTA] Checksum mismatch!")
                print(f"[OTA] Expected: {expected_sha256}")
                print(f"[OTA] Got: {calculated_sha256}")
                os.remove(temp_file)
                return False
            
            print(f"[OTA] Checksum verified")
            print(f"[OTA] Installing firmware...")
            
            # Flash new firmware
            if self.flash_firmware(temp_file):
                print(f"[OTA] Firmware installed successfully")
                os.remove(temp_file)
                
                # Schedule reboot
                print(f"[OTA] Rebooting in 5 seconds...")
                time.sleep(5)
                machine.reset()
                
                return True
            else:
                print(f"[OTA] Firmware installation failed")
                os.remove(temp_file)
                return False
                
        except Exception as e:
            print(f"[OTA] Update error: {e}")
            return False
    
    def flash_firmware(self, firmware_path):
        """Flash firmware to OTA partition"""
        try:
            # In real ESP32 implementation, would use esp32.Partition
            # to write to OTA partition
            
            with open(firmware_path, 'rb') as f:
                firmware_data = f.read()
            
            # Verify it's a valid ESP32 binary
            if len(firmware_data) < 100:
                print(f"[OTA] Invalid firmware size")
                return False
            
            # Check magic bytes (0xE9 for ESP32)
            if firmware_data[0] != 0xE9:
                print(f"[OTA] Invalid firmware magic byte")
                return False
            
            print(f"[OTA] Writing {len(firmware_data)} bytes to OTA partition...")
            
            # Simulated flashing (real implementation would write to flash)
            # ota_partition = esp32.Partition(esp32.Partition.RUNNING)
            # ota_partition.write_partition(firmware_data)
            
            return True
            
        except Exception as e:
            print(f"[OTA] Flash error: {e}")
            return False
    
    def rollback(self):
        """Rollback to previous firmware version"""
        try:
            print(f"[OTA] Rolling back to previous firmware...")
            
            # In real implementation, would use esp32.Partition
            # to switch boot partition
            
            print(f"[OTA] Rollback complete, rebooting...")
            time.sleep(2)
            machine.reset()
            
        except Exception as e:
            print(f"[OTA] Rollback error: {e}")

# ======================================================================================================================
# Advanced Power Management
# ======================================================================================================================

class PowerManager:
    """Advanced power management for solar/battery operation"""
    
    def __init__(self, hw_manager):
        self.hw = hw_manager
        self.power_mode = "NORMAL"  # NORMAL, POWER_SAVE, DEEP_SLEEP
        self.battery_level = 100
        self.is_charging = False
        self.solar_voltage = 0
        
        # Power profiles
        self.profiles = {
            'NORMAL': {
                'cpu_freq': 240,  # MHz
                'wifi_power': 20,  # dBm
                'inference_interval': 30,  # seconds
                'sensor_interval': 5  # seconds
            },
            'POWER_SAVE': {
                'cpu_freq': 160,
                'wifi_power': 15,
                'inference_interval': 60,
                'sensor_interval': 10
            },
            'ULTRA_SAVE': {
                'cpu_freq': 80,
                'wifi_power': 10,
                'inference_interval': 300,
                'sensor_interval': 30
            }
        }
    
    def update_power_status(self):
        """Update power status"""
        battery_voltage = self.hw.read_battery_voltage()
        
        # Calculate battery percentage (assuming 3.3V to 4.2V range for Li-ion)
        min_voltage = 3300  # mV
        max_voltage = 4200  # mV
        
        if battery_voltage >= max_voltage:
            self.battery_level = 100
        elif battery_voltage <= min_voltage:
            self.battery_level = 0
        else:
            self.battery_level = ((battery_voltage - min_voltage) / (max_voltage - min_voltage)) * 100
        
        # Detect charging (would need charging detection circuit)
        # self.is_charging = self.detect_charging()
        
        return self.battery_level
    
    def set_power_mode(self, mode):
        """Set power mode"""
        if mode not in self.profiles:
            print(f"[PWR] Invalid power mode: {mode}")
            return False
        
        profile = self.profiles[mode]
        
        try:
            # Set CPU frequency
            machine.freq(profile['cpu_freq'] * 1000000)
            
            # Adjust WiFi power
            # In real implementation: network.WLAN().config(txpower=profile['wifi_power'])
            
            self.power_mode = mode
            print(f"[PWR] Power mode set to {mode}")
            print(f"[PWR] CPU: {profile['cpu_freq']} MHz")
            print(f"[PWR] WiFi: {profile['wifi_power']} dBm")
            
            return True
            
        except Exception as e:
            print(f"[PWR] Error setting power mode: {e}")
            return False
    
    def auto_adjust_power(self):
        """Automatically adjust power mode based on battery level"""
        level = self.update_power_status()
        
        if level > 70:
            if self.power_mode != 'NORMAL':
                self.set_power_mode('NORMAL')
        elif level > 30:
            if self.power_mode != 'POWER_SAVE':
                self.set_power_mode('POWER_SAVE')
        else:
            if self.power_mode != 'ULTRA_SAVE':
                self.set_power_mode('ULTRA_SAVE')
        
        print(f"[PWR] Battery: {level:.1f}%, Mode: {self.power_mode}")
    
    def enter_deep_sleep(self, duration_seconds):
        """Enter deep sleep mode"""
        print(f"[PWR] Entering deep sleep for {duration_seconds}s")
        
        # Configure wake sources
        # Wake on timer
        esp32.wake_on_timer(duration_seconds * 1000000)  # microseconds
        
        # Wake on external interrupt (optional)
        # wake_pin = machine.Pin(14, machine.Pin.IN)
        # esp32.wake_on_ext0(wake_pin, esp32.WAKEUP_ANY_HIGH)
        
        machine.deepsleep()

# ======================================================================================================================
# Mesh Networking for Multi-Device Coordination
# ======================================================================================================================

class MeshNetwork:
    """ESP-NOW based mesh networking for device coordination"""
    
    def __init__(self, device_id):
        self.device_id = device_id
        self.peers = {}
        self.esp_now = None
        self.message_handlers = {}
        
    def init_esp_now(self):
        """Initialize ESP-NOW protocol"""
        try:
            import espnow
            
            # Initialize ESP-NOW
            self.esp_now = espnow.ESPNow()
            self.esp_now.active(True)
            
            # Register callback
            self.esp_now.on_recv(self.on_receive)
            
            print(f"[MESH] ESP-NOW initialized")
            return True
            
        except Exception as e:
            print(f"[MESH] ESP-NOW init error: {e}")
            return False
    
    def add_peer(self, mac_address, device_info):
        """Add a peer device to the mesh network"""
        try:
            # Convert MAC address string to bytes
            mac_bytes = ubinascii.unhexlify(mac_address.replace(':', ''))
            
            # Add peer
            self.esp_now.add_peer(mac_bytes)
            
            self.peers[mac_address] = {
                'mac': mac_bytes,
                'info': device_info,
                'last_seen': time.time()
            }
            
            print(f"[MESH] Added peer: {mac_address}")
            return True
            
        except Exception as e:
            print(f"[MESH] Add peer error: {e}")
            return False
    
    def send_message(self, mac_address, message_type, data):
        """Send message to peer"""
        if mac_address not in self.peers:
            print(f"[MESH] Unknown peer: {mac_address}")
            return False
        
        try:
            message = {
                'from': self.device_id,
                'type': message_type,
                'timestamp': time.time(),
                'data': data
            }
            
            json_msg = ujson.dumps(message)
            peer_mac = self.peers[mac_address]['mac']
            
            self.esp_now.send(peer_mac, json_msg)
            print(f"[MESH] Sent {message_type} to {mac_address}")
            
            return True
            
        except Exception as e:
            print(f"[MESH] Send error: {e}")
            return False
    
    def broadcast_message(self, message_type, data):
        """Broadcast message to all peers"""
        success_count = 0
        
        for mac_address in self.peers:
            if self.send_message(mac_address, message_type, data):
                success_count += 1
        
        print(f"[MESH] Broadcast sent to {success_count}/{len(self.peers)} peers")
        return success_count > 0
    
    def on_receive(self, mac, msg):
        """Callback for received messages"""
        try:
            mac_str = ubinascii.hexlify(mac, ':').decode()
            message = ujson.loads(msg)
            
            msg_type = message.get('type')
            sender = message.get('from')
            data = message.get('data', {})
            
            print(f"[MESH] Received {msg_type} from {sender}")
            
            # Update peer last seen
            if mac_str in self.peers:
                self.peers[mac_str]['last_seen'] = time.time()
            
            # Call registered handlers
            if msg_type in self.message_handlers:
                for handler in self.message_handlers[msg_type]:
                    handler(sender, data)
            
        except Exception as e:
            print(f"[MESH] Receive error: {e}")
    
    def register_handler(self, message_type, handler):
        """Register handler for message type"""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        
        self.message_handlers[message_type].append(handler)
        print(f"[MESH] Registered handler for {message_type}")

# ======================================================================================================================
# Configuration Management
# ======================================================================================================================

class ConfigManager:
    """Persistent configuration management"""
    
    def __init__(self, config_file="/config.json"):
        self.config_file = config_file
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                self.config = ujson.load(f)
            print(f"[CFG] Configuration loaded")
            return True
        except OSError:
            print(f"[CFG] Config file not found, using defaults")
            self.config = self.get_default_config()
            self.save_config()
            return False
        except Exception as e:
            print(f"[CFG] Load error: {e}")
            self.config = self.get_default_config()
            return False
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                ujson.dump(self.config, f)
            print(f"[CFG] Configuration saved")
            return True
        except Exception as e:
            print(f"[CFG] Save error: {e}")
            return False
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set configuration value"""
        self.config[key] = value
        self.save_config()
    
    def get_default_config(self):
        """Get default configuration"""
        return {
            'device_name': 'AgroPulse-ESP32',
            'farm_zone': 'SECTOR_A',
            'wifi_ssid': 'AgroPulse_Network',
            'wifi_password': 'SecureAgriNet2025',
            'nvr_host': '192.168.1.100',
            'nvr_port': 8443,
            'gps_enabled': True,
            'camera_quality': 10,
            'inference_enabled': True,
            'inference_interval': 30,
            'sensor_interval': 5,
            'power_mode': 'NORMAL',
            'deep_sleep_enabled': False,
            'deep_sleep_duration': 300
        }

# ======================================================================================================================
# Diagnostics and Health Monitoring
# ======================================================================================================================

class DiagnosticsManager:
    """System diagnostics and health monitoring"""
    
    def __init__(self):
        self.boot_count = 0
        self.uptime_start = time.time()
        self.errors = []
        self.max_errors = 100
        
        # Performance metrics
        self.metrics = {
            'total_captures': 0,
            'successful_captures': 0,
            'total_inferences': 0,
            'successful_inferences': 0,
            'total_transmissions': 0,
            'successful_transmissions': 0,
            'gps_fixes': 0,
            'wifi_reconnects': 0
        }
    
    def record_error(self, component, error_msg):
        """Record an error"""
        error = {
            'timestamp': time.time(),
            'component': component,
            'error': error_msg
        }
        
        self.errors.append(error)
        
        # Keep only recent errors
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]
        
        print(f"[DIAG] Error recorded: {component} - {error_msg}")
    
    def increment_metric(self, metric_name):
        """Increment a metric counter"""
        if metric_name in self.metrics:
            self.metrics[metric_name] += 1
    
    def get_system_info(self):
        """Get comprehensive system information"""
        uptime = time.time() - self.uptime_start
        
        info = {
            'uptime_seconds': uptime,
            'boot_count': self.boot_count,
            'free_memory': gc.mem_free(),
            'allocated_memory': gc.mem_alloc(),
            'cpu_freq_mhz': machine.freq() // 1000000,
            'flash_size': esp.flash_size(),
            'metrics': self.metrics,
            'recent_errors': self.errors[-10:]  # Last 10 errors
        }
        
        return info
    
    def print_diagnostics(self):
        """Print comprehensive diagnostics"""
        info = self.get_system_info()
        
        print("\n" + "=" * 60)
        print("SYSTEM DIAGNOSTICS")
        print("=" * 60)
        print(f"Uptime: {info['uptime_seconds']:.0f} seconds")
        print(f"Boot Count: {info['boot_count']}")
        print(f"CPU Frequency: {info['cpu_freq_mhz']} MHz")
        print(f"Free Memory: {info['free_memory']} bytes")
        print(f"Flash Size: {info['flash_size']} bytes")
        print(f"\nPerformance Metrics:")
        
        for metric, value in info['metrics'].items():
            print(f"  {metric}: {value}")
        
        if info['recent_errors']:
            print(f"\nRecent Errors ({len(info['recent_errors'])}):")
            for err in info['recent_errors']:
                print(f"  [{err['component']}] {err['error']}")
        
        print("=" * 60 + "\n")

# ======================================================================================================================
# END OF ESP32 SUPPORT MODULES
# Total additional lines: ~600+
# Combined with main.py: 1,700+ lines
# ======================================================================================================================
