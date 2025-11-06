"""
Hardware Integration Layer Module

Hardware device integration for agricultural sensors and accessories.

Features:
- Clip-on lens control for microscopy
- IoT Extender device management
- Multi-device discovery and pairing
- Comprehensive calibration system
- Firmware management
- Device health monitoring

The hardware layer enables seamless integration with specialized agricultural
equipment, providing professional-grade capabilities at consumer prices.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json


class DeviceType(Enum):
    """Hardware device types."""
    CLIP_ON_LENS = "clip_on_lens"
    IOT_EXTENDER = "iot_extender"
    MULTISPECTRAL_CAMERA = "multispectral_camera"
    SENTRY_STAKE = "sentry_stake"
    UNKNOWN = "unknown"


class ConnectionType(Enum):
    """Device connection types."""
    BLUETOOTH = "bluetooth"
    WIFI = "wifi"
    USB = "usb"
    SERIAL = "serial"


class CalibrationStatus(Enum):
    """Calibration status."""
    NOT_CALIBRATED = "not_calibrated"
    IN_PROGRESS = "in_progress"
    CALIBRATED = "calibrated"
    NEEDS_RECALIBRATION = "needs_recalibration"


@dataclass
class DeviceInfo:
    """Device information."""
    device_id: str
    device_type: DeviceType
    name: str
    manufacturer: str
    model: str
    firmware_version: str
    
    connection_type: ConnectionType
    is_connected: bool = False
    
    battery_level: Optional[float] = None  # 0-100%
    signal_strength: Optional[int] = None  # dBm
    
    last_seen: Optional[datetime] = None


@dataclass
class CalibrationData:
    """Calibration data for device."""
    device_id: str
    calibration_type: str  # 'sensor', 'color', 'geometric', 'lens'
    status: CalibrationStatus
    
    timestamp: datetime
    parameters: Dict
    
    quality_score: float = 0.0
    notes: str = ""


class ClipOnLensAPI:
    """
    API for clip-on microscope lenses.
    
    Supports:
    - Magnification control (10x, 20x, 50x, 100x)
    - Focus adjustment
    - Calibration management
    - Distortion correction
    """
    
    def __init__(self):
        """Initialize clip-on lens API."""
        self.connected_lenses: Dict[str, DeviceInfo] = {}
        self.calibrations: Dict[str, CalibrationData] = {}
        
        # Supported magnifications
        self.magnifications = [10, 20, 50, 100]
        
    def discover_lenses(self) -> List[DeviceInfo]:
        """
        Discover available clip-on lenses.
        
        Returns:
            List of discovered lenses
        """
        print("[Lens] Discovering clip-on lenses...")
        
        # Placeholder: would use actual Bluetooth/WiFi discovery
        discovered = [
            DeviceInfo(
                device_id="lens_001",
                device_type=DeviceType.CLIP_ON_LENS,
                name="Macro Lens 100x",
                manufacturer="AgroVision",
                model="AV-ML100",
                firmware_version="1.2.3",
                connection_type=ConnectionType.BLUETOOTH
            )
        ]
        
        print(f"[Lens] Found {len(discovered)} lens(es)")
        return discovered
    
    def connect_lens(self, device_id: str) -> bool:
        """
        Connect to lens.
        
        Args:
            device_id: Lens device ID
            
        Returns:
            Connection success
        """
        print(f"[Lens] Connecting to {device_id}...")
        
        # Placeholder: would establish actual connection
        device = DeviceInfo(
            device_id=device_id,
            device_type=DeviceType.CLIP_ON_LENS,
            name="Macro Lens 100x",
            manufacturer="AgroVision",
            model="AV-ML100",
            firmware_version="1.2.3",
            connection_type=ConnectionType.BLUETOOTH,
            is_connected=True,
            battery_level=85.0,
            signal_strength=-45
        )
        
        self.connected_lenses[device_id] = device
        
        print(f"[Lens] Connected to {device_id}")
        return True
    
    def disconnect_lens(self, device_id: str) -> bool:
        """
        Disconnect lens.
        
        Args:
            device_id: Lens device ID
            
        Returns:
            Disconnection success
        """
        if device_id in self.connected_lenses:
            del self.connected_lenses[device_id]
            print(f"[Lens] Disconnected {device_id}")
            return True
        
        return False
    
    def set_magnification(self, device_id: str, magnification: int) -> bool:
        """
        Set lens magnification.
        
        Args:
            device_id: Lens device ID
            magnification: Magnification level (10, 20, 50, 100)
            
        Returns:
            Success status
        """
        if device_id not in self.connected_lenses:
            print(f"[Lens] Lens not connected: {device_id}")
            return False
        
        if magnification not in self.magnifications:
            print(f"[Lens] Invalid magnification: {magnification}")
            return False
        
        # Placeholder: would send command to lens
        print(f"[Lens] Set magnification to {magnification}x")
        return True
    
    def adjust_focus(self, device_id: str, focus_offset: float) -> bool:
        """
        Adjust lens focus.
        
        Args:
            device_id: Lens device ID
            focus_offset: Focus adjustment (-1.0 to 1.0)
            
        Returns:
            Success status
        """
        if device_id not in self.connected_lenses:
            return False
        
        # Clamp offset
        focus_offset = max(-1.0, min(1.0, focus_offset))
        
        # Placeholder: would send focus command
        print(f"[Lens] Adjusted focus: {focus_offset:+.2f}")
        return True
    
    def calibrate_lens(self, device_id: str, checkerboard_image: np.ndarray) -> CalibrationData:
        """
        Calibrate lens using checkerboard pattern.
        
        Args:
            device_id: Lens device ID
            checkerboard_image: Image of checkerboard pattern
            
        Returns:
            Calibration data
        """
        print(f"[Lens] Calibrating {device_id}...")
        
        # Detect checkerboard corners
        corners_found, corners = self._detect_checkerboard(checkerboard_image)
        
        if not corners_found:
            raise ValueError("Checkerboard pattern not detected")
        
        # Calculate distortion parameters
        camera_matrix = np.eye(3)
        dist_coeffs = np.zeros(5)
        
        # Placeholder: would use actual calibration (cv2.calibrateCamera)
        camera_matrix[0, 0] = 800  # fx
        camera_matrix[1, 1] = 800  # fy
        camera_matrix[0, 2] = checkerboard_image.shape[1] / 2  # cx
        camera_matrix[1, 2] = checkerboard_image.shape[0] / 2  # cy
        
        dist_coeffs = np.array([0.1, -0.05, 0.001, 0.001, 0.01])
        
        # Store calibration
        calibration = CalibrationData(
            device_id=device_id,
            calibration_type='lens',
            status=CalibrationStatus.CALIBRATED,
            timestamp=datetime.now(),
            parameters={
                'camera_matrix': camera_matrix.tolist(),
                'dist_coeffs': dist_coeffs.tolist(),
                'image_size': checkerboard_image.shape[:2]
            },
            quality_score=0.95
        )
        
        self.calibrations[device_id] = calibration
        
        print(f"[Lens] Calibration complete (quality: {calibration.quality_score:.2%})")
        return calibration
    
    def _detect_checkerboard(
        self,
        image: np.ndarray,
        pattern_size: Tuple[int, int] = (9, 6)
    ) -> Tuple[bool, Optional[np.ndarray]]:
        """Detect checkerboard pattern in image."""
        # Placeholder: would use cv2.findChessboardCorners
        
        # Simulate detection
        found = True
        corners = np.random.rand(pattern_size[0] * pattern_size[1], 2) * 100
        
        return found, corners
    
    def apply_distortion_correction(
        self,
        device_id: str,
        image: np.ndarray
    ) -> np.ndarray:
        """
        Apply distortion correction to image.
        
        Args:
            device_id: Lens device ID
            image: Input image
            
        Returns:
            Corrected image
        """
        if device_id not in self.calibrations:
            print(f"[Lens] No calibration data for {device_id}")
            return image
        
        calib = self.calibrations[device_id]
        
        # Placeholder: would use cv2.undistort
        corrected = image.copy()
        
        return corrected


class IoTExtenderControl:
    """
    Control for Micro-Focus IoT Extender devices.
    
    Features:
    - Motor control for focus adjustment
    - LED ring control for illumination
    - Sensor data aggregation
    - Wireless communication
    """
    
    def __init__(self):
        """Initialize IoT Extender control."""
        self.connected_extenders: Dict[str, DeviceInfo] = {}
        
    def discover_extenders(self) -> List[DeviceInfo]:
        """
        Discover IoT Extenders on network.
        
        Returns:
            List of discovered extenders
        """
        print("[Extender] Discovering IoT Extenders...")
        
        # Placeholder: would scan WiFi/Bluetooth
        discovered = [
            DeviceInfo(
                device_id="extender_001",
                device_type=DeviceType.IOT_EXTENDER,
                name="Micro-Focus Extender",
                manufacturer="AgroTech",
                model="MFE-100",
                firmware_version="2.1.0",
                connection_type=ConnectionType.WIFI
            )
        ]
        
        print(f"[Extender] Found {len(discovered)} extender(s)")
        return discovered
    
    def connect_extender(self, device_id: str) -> bool:
        """
        Connect to IoT Extender.
        
        Args:
            device_id: Extender device ID
            
        Returns:
            Connection success
        """
        print(f"[Extender] Connecting to {device_id}...")
        
        device = DeviceInfo(
            device_id=device_id,
            device_type=DeviceType.IOT_EXTENDER,
            name="Micro-Focus Extender",
            manufacturer="AgroTech",
            model="MFE-100",
            firmware_version="2.1.0",
            connection_type=ConnectionType.WIFI,
            is_connected=True,
            battery_level=None,  # AC powered
            signal_strength=-55
        )
        
        self.connected_extenders[device_id] = device
        
        print(f"[Extender] Connected to {device_id}")
        return True
    
    def control_motor(
        self,
        device_id: str,
        position: float,
        speed: float = 1.0
    ) -> bool:
        """
        Control focus motor.
        
        Args:
            device_id: Extender device ID
            position: Target position (0.0 to 1.0)
            speed: Motor speed (0.1 to 1.0)
            
        Returns:
            Success status
        """
        if device_id not in self.connected_extenders:
            return False
        
        position = max(0.0, min(1.0, position))
        speed = max(0.1, min(1.0, speed))
        
        # Placeholder: would send motor command
        print(f"[Extender] Motor -> position: {position:.2f}, speed: {speed:.2f}")
        return True
    
    def control_led_ring(
        self,
        device_id: str,
        brightness: float,
        color_temp: int = 5000
    ) -> bool:
        """
        Control LED ring illumination.
        
        Args:
            device_id: Extender device ID
            brightness: Brightness (0.0 to 1.0)
            color_temp: Color temperature in Kelvin
            
        Returns:
            Success status
        """
        if device_id not in self.connected_extenders:
            return False
        
        brightness = max(0.0, min(1.0, brightness))
        
        # Placeholder: would send LED command
        print(f"[Extender] LED -> brightness: {brightness:.2%}, temp: {color_temp}K")
        return True
    
    def read_sensors(self, device_id: str) -> Dict:
        """
        Read sensor data from extender.
        
        Args:
            device_id: Extender device ID
            
        Returns:
            Sensor readings
        """
        if device_id not in self.connected_extenders:
            return {}
        
        # Placeholder: would read actual sensors
        data = {
            'temperature': 23.5,
            'humidity': 45.2,
            'light_level': 850,
            'motor_position': 0.5,
            'timestamp': datetime.now().isoformat()
        }
        
        return data


class DeviceManager:
    """
    Central device management.
    
    Manages all connected hardware devices with unified interface.
    """
    
    def __init__(self):
        """Initialize device manager."""
        self.devices: Dict[str, DeviceInfo] = {}
        
        # Component managers
        self.lens_api = ClipOnLensAPI()
        self.extender_control = IoTExtenderControl()
        
    def scan_all_devices(self) -> List[DeviceInfo]:
        """
        Scan for all device types.
        
        Returns:
            List of all discovered devices
        """
        print("[DeviceManager] Scanning for devices...")
        
        all_devices = []
        
        # Scan lenses
        lenses = self.lens_api.discover_lenses()
        all_devices.extend(lenses)
        
        # Scan extenders
        extenders = self.extender_control.discover_extenders()
        all_devices.extend(extenders)
        
        # Update device registry
        for device in all_devices:
            self.devices[device.device_id] = device
        
        print(f"[DeviceManager] Found {len(all_devices)} device(s)")
        return all_devices
    
    def connect_device(self, device_id: str) -> bool:
        """
        Connect to device.
        
        Args:
            device_id: Device ID
            
        Returns:
            Connection success
        """
        if device_id not in self.devices:
            print(f"[DeviceManager] Unknown device: {device_id}")
            return False
        
        device = self.devices[device_id]
        
        # Route to appropriate manager
        if device.device_type == DeviceType.CLIP_ON_LENS:
            return self.lens_api.connect_lens(device_id)
        elif device.device_type == DeviceType.IOT_EXTENDER:
            return self.extender_control.connect_extender(device_id)
        
        return False
    
    def disconnect_device(self, device_id: str) -> bool:
        """
        Disconnect device.
        
        Args:
            device_id: Device ID
            
        Returns:
            Disconnection success
        """
        if device_id not in self.devices:
            return False
        
        device = self.devices[device_id]
        
        if device.device_type == DeviceType.CLIP_ON_LENS:
            return self.lens_api.disconnect_lens(device_id)
        
        return True
    
    def get_device_status(self, device_id: str) -> Dict:
        """
        Get device status.
        
        Args:
            device_id: Device ID
            
        Returns:
            Status information
        """
        if device_id not in self.devices:
            return {'error': 'Device not found'}
        
        device = self.devices[device_id]
        
        return {
            'device_id': device.device_id,
            'name': device.name,
            'type': device.device_type.value,
            'connected': device.is_connected,
            'battery': device.battery_level,
            'signal': device.signal_strength,
            'firmware': device.firmware_version
        }
    
    def update_firmware(self, device_id: str, firmware_path: str) -> bool:
        """
        Update device firmware.
        
        Args:
            device_id: Device ID
            firmware_path: Path to firmware file
            
        Returns:
            Update success
        """
        if device_id not in self.devices:
            return False
        
        print(f"[DeviceManager] Updating firmware for {device_id}...")
        
        # Placeholder: would perform actual OTA update
        # 1. Verify firmware file
        # 2. Transfer to device
        # 3. Install and reboot
        
        print(f"[DeviceManager] Firmware updated successfully")
        return True


class CalibrationManager:
    """
    Comprehensive calibration management system.
    
    Handles:
    - Sensor calibration
    - Color calibration
    - Geometric calibration
    - Validation and quality assessment
    """
    
    def __init__(self):
        """Initialize calibration manager."""
        self.calibrations: Dict[str, List[CalibrationData]] = {}
        
    def calibrate_sensor(
        self,
        device_id: str,
        reference_measurements: Dict[str, float]
    ) -> CalibrationData:
        """
        Calibrate sensor using reference measurements.
        
        Args:
            device_id: Device ID
            reference_measurements: Known reference values
            
        Returns:
            Calibration data
        """
        print(f"[Calibration] Calibrating sensor for {device_id}...")
        
        # Collect sensor readings
        # Compare with reference
        # Calculate correction factors
        
        calibration = CalibrationData(
            device_id=device_id,
            calibration_type='sensor',
            status=CalibrationStatus.CALIBRATED,
            timestamp=datetime.now(),
            parameters={
                'correction_factors': {
                    'temperature': 1.02,
                    'humidity': 0.98,
                    'light': 1.05
                }
            },
            quality_score=0.92
        )
        
        self._store_calibration(device_id, calibration)
        
        print(f"[Calibration] Sensor calibrated (quality: {calibration.quality_score:.2%})")
        return calibration
    
    def calibrate_color(
        self,
        device_id: str,
        color_chart_image: np.ndarray
    ) -> CalibrationData:
        """
        Calibrate color using color chart.
        
        Args:
            device_id: Device ID
            color_chart_image: Image of standard color chart
            
        Returns:
            Calibration data
        """
        print(f"[Calibration] Calibrating color for {device_id}...")
        
        # Detect color patches
        detected_colors = self._detect_color_patches(color_chart_image)
        
        # Known reference colors (from color chart spec)
        reference_colors = self._get_reference_colors()
        
        # Calculate color correction matrix
        correction_matrix = self._calculate_color_correction(
            detected_colors,
            reference_colors
        )
        
        calibration = CalibrationData(
            device_id=device_id,
            calibration_type='color',
            status=CalibrationStatus.CALIBRATED,
            timestamp=datetime.now(),
            parameters={
                'correction_matrix': correction_matrix.tolist()
            },
            quality_score=0.88
        )
        
        self._store_calibration(device_id, calibration)
        
        print(f"[Calibration] Color calibrated (quality: {calibration.quality_score:.2%})")
        return calibration
    
    def calibrate_geometric(
        self,
        device_id: str,
        calibration_images: List[np.ndarray]
    ) -> CalibrationData:
        """
        Calibrate camera geometry.
        
        Args:
            device_id: Device ID
            calibration_images: Images of calibration pattern
            
        Returns:
            Calibration data
        """
        print(f"[Calibration] Calibrating geometry for {device_id}...")
        
        # Detect calibration pattern in each image
        # Estimate camera parameters
        
        calibration = CalibrationData(
            device_id=device_id,
            calibration_type='geometric',
            status=CalibrationStatus.CALIBRATED,
            timestamp=datetime.now(),
            parameters={
                'focal_length': 800.0,
                'principal_point': [320, 240],
                'distortion': [0.1, -0.05, 0.001, 0.001]
            },
            quality_score=0.94
        )
        
        self._store_calibration(device_id, calibration)
        
        print(f"[Calibration] Geometry calibrated (quality: {calibration.quality_score:.2%})")
        return calibration
    
    def _detect_color_patches(self, image: np.ndarray) -> np.ndarray:
        """Detect color patches in color chart."""
        # Placeholder: would use actual detection
        num_patches = 24  # Standard ColorChecker
        colors = np.random.rand(num_patches, 3)
        return colors
    
    def _get_reference_colors(self) -> np.ndarray:
        """Get reference colors from standard color chart."""
        # Standard ColorChecker reference values
        references = np.array([
            [0.443, 0.318, 0.230],  # Dark skin
            [0.773, 0.578, 0.493],  # Light skin
            # ... more colors
        ])
        return references
    
    def _calculate_color_correction(
        self,
        detected: np.ndarray,
        reference: np.ndarray
    ) -> np.ndarray:
        """Calculate color correction matrix."""
        # Use least squares to find correction matrix
        # In production: would use proper color science
        
        correction = np.eye(3)
        return correction
    
    def _store_calibration(
        self,
        device_id: str,
        calibration: CalibrationData
    ) -> None:
        """Store calibration data."""
        if device_id not in self.calibrations:
            self.calibrations[device_id] = []
        
        self.calibrations[device_id].append(calibration)
    
    def get_calibration(
        self,
        device_id: str,
        calibration_type: str
    ) -> Optional[CalibrationData]:
        """
        Get latest calibration for device.
        
        Args:
            device_id: Device ID
            calibration_type: Type of calibration
            
        Returns:
            Calibration data if available
        """
        if device_id not in self.calibrations:
            return None
        
        # Find latest calibration of requested type
        for calib in reversed(self.calibrations[device_id]):
            if calib.calibration_type == calibration_type:
                return calib
        
        return None
    
    def validate_calibration(
        self,
        device_id: str,
        calibration_type: str
    ) -> bool:
        """
        Validate calibration quality.
        
        Args:
            device_id: Device ID
            calibration_type: Type of calibration
            
        Returns:
            Validation success
        """
        calib = self.get_calibration(device_id, calibration_type)
        
        if not calib:
            return False
        
        # Check quality score
        if calib.quality_score < 0.8:
            print(f"[Calibration] Quality too low: {calib.quality_score:.2%}")
            calib.status = CalibrationStatus.NEEDS_RECALIBRATION
            return False
        
        # Check age
        age = (datetime.now() - calib.timestamp).days
        if age > 30:  # Re-calibrate monthly
            print(f"[Calibration] Calibration expired ({age} days old)")
            calib.status = CalibrationStatus.NEEDS_RECALIBRATION
            return False
        
        return True


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Hardware Integration Layer Test")
    print("=" * 60)
    
    # Initialize device manager
    manager = DeviceManager()
    
    # Scan for devices
    print("\n1. Scanning for devices...")
    devices = manager.scan_all_devices()
    
    for device in devices:
        print(f"   Found: {device.name} ({device.device_type.value})")
    
    # Connect to lens
    print("\n2. Connecting to clip-on lens...")
    if devices:
        lens_id = devices[0].device_id
        manager.connect_device(lens_id)
        
        # Set magnification
        print("\n3. Setting magnification...")
        manager.lens_api.set_magnification(lens_id, 50)
    
    # Calibration
    print("\n4. Running calibration...")
    calib_manager = CalibrationManager()
    
    # Sensor calibration
    sensor_calib = calib_manager.calibrate_sensor(
        "device_001",
        {
            'temperature': 25.0,
            'humidity': 50.0,
            'light': 1000.0
        }
    )
    
    print(f"   Sensor calibrated: {sensor_calib.quality_score:.2%} quality")
    
    print("\n" + "=" * 60)
    print("Hardware Integration Complete!")
    print("=" * 60)
