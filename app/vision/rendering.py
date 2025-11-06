"""
3D Visualization Engine Module

Interactive 3D visualization for plant models with WebGL rendering.

Features:
- High-performance WebGL rendering with Three.js
- Interactive viewer with intuitive controls
- Measurement tools for quantitative analysis
- Export utilities for various formats
- Real-time rendering optimizations
- Cross-platform browser support

The visualization engine provides farmers and agronomists with interactive
3D models for detailed plant inspection and measurements.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json


class RenderMode(Enum):
    """3D rendering modes."""
    POINT_CLOUD = "point_cloud"
    MESH = "mesh"
    WIREFRAME = "wireframe"
    SHADED = "shaded"
    TEXTURED = "textured"


class ViewMode(Enum):
    """Camera view modes."""
    FREE = "free"
    ORBIT = "orbit"
    FLY = "fly"
    FIRST_PERSON = "first_person"


class MeasurementType(Enum):
    """Measurement types."""
    DISTANCE = "distance"
    ANGLE = "angle"
    AREA = "area"
    VOLUME = "volume"
    DIAMETER = "diameter"


class ExportFormat(Enum):
    """Export file formats."""
    OBJ = "obj"
    PLY = "ply"
    STL = "stl"
    GLTF = "gltf"
    GLB = "glb"
    PNG = "png"
    JPG = "jpg"
    MP4 = "mp4"
    GIF = "gif"


@dataclass
class RenderConfig:
    """3D rendering configuration."""
    render_mode: RenderMode = RenderMode.SHADED
    
    # Quality settings
    point_size: float = 2.0
    anti_aliasing: bool = True
    shadows: bool = True
    ambient_occlusion: bool = False
    
    # Performance
    max_points: int = 1_000_000
    lod_enabled: bool = True  # Level of Detail
    frustum_culling: bool = True
    
    # Lighting
    ambient_intensity: float = 0.4
    directional_intensity: float = 0.8
    directional_direction: Tuple[float, float, float] = (-1, -2, -1)
    
    # Background
    background_color: Tuple[float, float, float] = (0.95, 0.95, 0.95)
    show_grid: bool = True
    show_axes: bool = True


@dataclass
class ViewerState:
    """Interactive viewer state."""
    # Camera
    camera_position: np.ndarray = None
    camera_target: np.ndarray = None
    camera_up: np.ndarray = None
    
    camera_fov: float = 60.0
    camera_near: float = 0.1
    camera_far: float = 1000.0
    
    # View mode
    view_mode: ViewMode = ViewMode.ORBIT
    
    # Interaction
    is_rotating: bool = False
    is_panning: bool = False
    is_zooming: bool = False
    
    last_mouse_position: Optional[Tuple[int, int]] = None
    
    # Selection
    selected_points: List[int] = None
    selected_faces: List[int] = None


@dataclass
class Measurement:
    """3D measurement data."""
    measurement_id: str
    measurement_type: MeasurementType
    timestamp: datetime
    
    # Points involved
    points: List[np.ndarray]
    
    # Result
    value: float
    unit: str
    
    # Metadata
    label: str = ""
    color: Tuple[float, float, float] = (1.0, 0.0, 0.0)
    visible: bool = True


class WebGLRenderer:
    """
    WebGL-based 3D renderer using Three.js.
    
    Provides high-performance rendering with:
    - Point cloud visualization with LOD
    - Mesh rendering with lighting and shadows
    - Texture mapping
    - Real-time updates
    """
    
    def __init__(
        self,
        canvas_id: str = "webgl-canvas",
        config: Optional[RenderConfig] = None
    ):
        """
        Initialize WebGL renderer.
        
        Args:
            canvas_id: HTML canvas element ID
            config: Rendering configuration
        """
        self.canvas_id = canvas_id
        self.config = config or RenderConfig()
        
        self.scene_data = {
            'point_clouds': [],
            'meshes': [],
            'lights': [],
            'annotations': []
        }
        
        self.initialized = False
        
    def initialize(self) -> Dict:
        """
        Initialize WebGL context and scene.
        
        Returns:
            Initialization parameters for JavaScript
        """
        print("[Renderer] Initializing WebGL context...")
        
        # Generate Three.js initialization code
        init_code = self._generate_threejs_init()
        
        self.initialized = True
        
        return {
            'canvas_id': self.canvas_id,
            'initialization_code': init_code,
            'config': self._config_to_dict()
        }
    
    def _generate_threejs_init(self) -> str:
        """Generate Three.js initialization JavaScript code."""
        code = f"""
// Initialize Three.js scene
const scene = new THREE.Scene();
scene.background = new THREE.Color({self.config.background_color[0]}, 
                                   {self.config.background_color[1]}, 
                                   {self.config.background_color[2]});

// Camera
const camera = new THREE.PerspectiveCamera(
    60,  // FOV
    window.innerWidth / window.innerHeight,  // Aspect
    0.1,  // Near
    1000  // Far
);
camera.position.set(0, 0, 5);

// Renderer
const renderer = new THREE.WebGLRenderer({{
    canvas: document.getElementById('{self.canvas_id}'),
    antialias: {str(self.config.anti_aliasing).lower()}
}});
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = {str(self.config.shadows).lower()};

// Lights
const ambientLight = new THREE.AmbientLight(0xffffff, {self.config.ambient_intensity});
scene.add(ambientLight);

const directionalLight = new THREE.DirectionalLight(0xffffff, {self.config.directional_intensity});
directionalLight.position.set({self.config.directional_direction[0]}, 
                               {self.config.directional_direction[1]}, 
                               {self.config.directional_direction[2]});
directionalLight.castShadow = {str(self.config.shadows).lower()};
scene.add(directionalLight);

// Grid
{"const gridHelper = new THREE.GridHelper(10, 10); scene.add(gridHelper);" if self.config.show_grid else ""}

// Axes
{"const axesHelper = new THREE.AxesHelper(5); scene.add(axesHelper);" if self.config.show_axes else ""}

// Controls
const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;

// Animation loop
function animate() {{
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}}
animate();
"""
        return code
    
    def add_point_cloud(
        self,
        points: np.ndarray,
        colors: Optional[np.ndarray] = None,
        name: str = "point_cloud"
    ) -> str:
        """
        Add point cloud to scene.
        
        Args:
            points: Nx3 array of point coordinates
            colors: Nx3 array of RGB colors (0-1)
            name: Point cloud name
            
        Returns:
            Point cloud ID
        """
        # Apply LOD if needed
        if self.config.lod_enabled and len(points) > self.config.max_points:
            points, colors = self._apply_lod(points, colors)
        
        # Generate ID
        pc_id = f"{name}_{datetime.now().timestamp()}"
        
        # Store point cloud data
        self.scene_data['point_clouds'].append({
            'id': pc_id,
            'name': name,
            'points': points,
            'colors': colors,
            'num_points': len(points)
        })
        
        # Generate Three.js code
        js_code = self._generate_point_cloud_code(pc_id, points, colors)
        
        print(f"[Renderer] Added point cloud '{name}' with {len(points)} points")
        
        return pc_id
    
    def _apply_lod(
        self,
        points: np.ndarray,
        colors: Optional[np.ndarray]
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Apply Level of Detail downsampling."""
        # Random sampling to max_points
        if len(points) <= self.config.max_points:
            return points, colors
        
        indices = np.random.choice(
            len(points),
            self.config.max_points,
            replace=False
        )
        
        sampled_points = points[indices]
        sampled_colors = colors[indices] if colors is not None else None
        
        print(f"[Renderer] LOD: Downsampled {len(points)} to {len(sampled_points)} points")
        
        return sampled_points, sampled_colors
    
    def _generate_point_cloud_code(
        self,
        pc_id: str,
        points: np.ndarray,
        colors: Optional[np.ndarray]
    ) -> str:
        """Generate Three.js code for point cloud."""
        # Convert to JSON
        points_json = json.dumps(points.tolist())
        
        if colors is not None:
            colors_json = json.dumps(colors.tolist())
        else:
            # Default white
            colors_json = json.dumps([[1, 1, 1]] * len(points))
        
        code = f"""
// Point cloud: {pc_id}
const points_{pc_id} = {points_json};
const colors_{pc_id} = {colors_json};

const geometry_{pc_id} = new THREE.BufferGeometry();
geometry_{pc_id}.setAttribute('position', 
    new THREE.Float32BufferAttribute(points_{pc_id}.flat(), 3));
geometry_{pc_id}.setAttribute('color',
    new THREE.Float32BufferAttribute(colors_{pc_id}.flat(), 3));

const material_{pc_id} = new THREE.PointsMaterial({{
    size: {self.config.point_size},
    vertexColors: true
}});

const pointCloud_{pc_id} = new THREE.Points(geometry_{pc_id}, material_{pc_id});
scene.add(pointCloud_{pc_id});
"""
        return code
    
    def add_mesh(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        vertex_colors: Optional[np.ndarray] = None,
        texture: Optional[np.ndarray] = None,
        name: str = "mesh"
    ) -> str:
        """
        Add mesh to scene.
        
        Args:
            vertices: Nx3 array of vertex coordinates
            faces: Mx3 array of face indices
            vertex_colors: Nx3 array of RGB colors
            texture: Texture image
            name: Mesh name
            
        Returns:
            Mesh ID
        """
        mesh_id = f"{name}_{datetime.now().timestamp()}"
        
        # Store mesh data
        self.scene_data['meshes'].append({
            'id': mesh_id,
            'name': name,
            'vertices': vertices,
            'faces': faces,
            'vertex_colors': vertex_colors,
            'has_texture': texture is not None,
            'num_vertices': len(vertices),
            'num_faces': len(faces)
        })
        
        # Generate Three.js code
        js_code = self._generate_mesh_code(
            mesh_id, vertices, faces, vertex_colors, texture
        )
        
        print(f"[Renderer] Added mesh '{name}' with {len(vertices)} vertices, {len(faces)} faces")
        
        return mesh_id
    
    def _generate_mesh_code(
        self,
        mesh_id: str,
        vertices: np.ndarray,
        faces: np.ndarray,
        vertex_colors: Optional[np.ndarray],
        texture: Optional[np.ndarray]
    ) -> str:
        """Generate Three.js code for mesh."""
        vertices_json = json.dumps(vertices.tolist())
        faces_json = json.dumps(faces.tolist())
        
        code = f"""
// Mesh: {mesh_id}
const vertices_{mesh_id} = {vertices_json};
const faces_{mesh_id} = {faces_json};

const geometry_{mesh_id} = new THREE.BufferGeometry();
geometry_{mesh_id}.setAttribute('position',
    new THREE.Float32BufferAttribute(vertices_{mesh_id}.flat(), 3));
geometry_{mesh_id}.setIndex(faces_{mesh_id}.flat());
geometry_{mesh_id}.computeVertexNormals();

const material_{mesh_id} = new THREE.MeshPhongMaterial({{
    color: 0x44aa88,
    flatShading: false,
    side: THREE.DoubleSide
}});

const mesh_{mesh_id} = new THREE.Mesh(geometry_{mesh_id}, material_{mesh_id});
mesh_{mesh_id}.castShadow = true;
mesh_{mesh_id}.receiveShadow = true;
scene.add(mesh_{mesh_id});
"""
        return code
    
    def update_render_mode(self, mode: RenderMode) -> None:
        """Update rendering mode."""
        self.config.render_mode = mode
        print(f"[Renderer] Render mode: {mode.value}")
    
    def _config_to_dict(self) -> Dict:
        """Convert config to dictionary."""
        return {
            'render_mode': self.config.render_mode.value,
            'point_size': self.config.point_size,
            'anti_aliasing': self.config.anti_aliasing,
            'shadows': self.config.shadows,
            'ambient_occlusion': self.config.ambient_occlusion,
            'background_color': self.config.background_color,
            'show_grid': self.config.show_grid,
            'show_axes': self.config.show_axes
        }


class InteractiveViewer:
    """
    Interactive 3D viewer with intuitive controls.
    
    Supports:
    - Touch gestures (pinch, pan, rotate)
    - Mouse controls (drag, scroll, click)
    - Keyboard shortcuts
    - Smooth animations
    """
    
    def __init__(
        self,
        renderer: WebGLRenderer
    ):
        """
        Initialize interactive viewer.
        
        Args:
            renderer: WebGL renderer instance
        """
        self.renderer = renderer
        self.state = ViewerState(
            camera_position=np.array([0, 0, 5]),
            camera_target=np.array([0, 0, 0]),
            camera_up=np.array([0, 1, 0])
        )
        
        # Animation
        self.animation_active = False
        self.animation_target_position = None
        
    def set_view_mode(self, mode: ViewMode) -> None:
        """
        Set camera view mode.
        
        Args:
            mode: View mode
        """
        self.state.view_mode = mode
        print(f"[Viewer] View mode: {mode.value}")
    
    def handle_mouse_down(self, x: int, y: int, button: int) -> None:
        """
        Handle mouse down event.
        
        Args:
            x: Mouse X coordinate
            y: Mouse Y coordinate
            button: Mouse button (0=left, 1=middle, 2=right)
        """
        self.state.last_mouse_position = (x, y)
        
        if button == 0:  # Left button
            self.state.is_rotating = True
        elif button == 1:  # Middle button
            self.state.is_panning = True
        elif button == 2:  # Right button
            self.state.is_zooming = True
    
    def handle_mouse_up(self, button: int) -> None:
        """
        Handle mouse up event.
        
        Args:
            button: Mouse button
        """
        if button == 0:
            self.state.is_rotating = False
        elif button == 1:
            self.state.is_panning = False
        elif button == 2:
            self.state.is_zooming = False
        
        self.state.last_mouse_position = None
    
    def handle_mouse_move(self, x: int, y: int) -> None:
        """
        Handle mouse move event.
        
        Args:
            x: Mouse X coordinate
            y: Mouse Y coordinate
        """
        if self.state.last_mouse_position is None:
            return
        
        last_x, last_y = self.state.last_mouse_position
        dx = x - last_x
        dy = y - last_y
        
        if self.state.is_rotating:
            self._rotate_camera(dx, dy)
        elif self.state.is_panning:
            self._pan_camera(dx, dy)
        elif self.state.is_zooming:
            self._zoom_camera(dy)
        
        self.state.last_mouse_position = (x, y)
    
    def handle_mouse_wheel(self, delta: float) -> None:
        """
        Handle mouse wheel event.
        
        Args:
            delta: Wheel delta (positive = zoom in)
        """
        self._zoom_camera(delta * 0.1)
    
    def _rotate_camera(self, dx: float, dy: float) -> None:
        """Rotate camera around target."""
        # Calculate rotation angles
        angle_x = dx * 0.005  # Horizontal rotation
        angle_y = dy * 0.005  # Vertical rotation
        
        # Get current camera vector
        camera_vec = self.state.camera_position - self.state.camera_target
        distance = np.linalg.norm(camera_vec)
        
        # Apply rotation (simplified)
        # In production, would use proper quaternion rotation
        self.state.camera_position[0] += np.cos(angle_x) * distance * 0.01
        self.state.camera_position[2] += np.sin(angle_x) * distance * 0.01
        
        print(f"[Viewer] Camera rotated: dx={dx}, dy={dy}")
    
    def _pan_camera(self, dx: float, dy: float) -> None:
        """Pan camera and target together."""
        # Calculate pan vector
        pan_speed = 0.01
        pan_x = dx * pan_speed
        pan_y = -dy * pan_speed
        
        # Apply pan
        self.state.camera_position[0] += pan_x
        self.state.camera_position[1] += pan_y
        self.state.camera_target[0] += pan_x
        self.state.camera_target[1] += pan_y
        
        print(f"[Viewer] Camera panned: dx={dx}, dy={dy}")
    
    def _zoom_camera(self, delta: float) -> None:
        """Zoom camera toward/away from target."""
        # Calculate zoom direction
        direction = self.state.camera_target - self.state.camera_position
        distance = np.linalg.norm(direction)
        
        if distance > 0:
            direction = direction / distance
            
            # Apply zoom
            zoom_amount = delta * 0.1
            new_position = self.state.camera_position + direction * zoom_amount
            
            # Prevent zooming too close
            new_distance = np.linalg.norm(new_position - self.state.camera_target)
            if new_distance > 0.1:
                self.state.camera_position = new_position
                print(f"[Viewer] Camera zoomed: delta={delta}")
    
    def animate_to_view(
        self,
        target_position: np.ndarray,
        duration: float = 1.0
    ) -> None:
        """
        Animate camera to new position.
        
        Args:
            target_position: Target camera position
            duration: Animation duration in seconds
        """
        self.animation_active = True
        self.animation_target_position = target_position
        
        print(f"[Viewer] Animating to position: {target_position}")
    
    def reset_view(self) -> None:
        """Reset camera to default view."""
        self.state.camera_position = np.array([0, 0, 5])
        self.state.camera_target = np.array([0, 0, 0])
        self.state.camera_up = np.array([0, 1, 0])
        
        print("[Viewer] View reset to default")
    
    def fit_to_view(self, bounds: Dict) -> None:
        """
        Fit camera to show all content.
        
        Args:
            bounds: Bounding box {'min': [x,y,z], 'max': [x,y,z]}
        """
        # Calculate center and size
        min_point = np.array(bounds['min'])
        max_point = np.array(bounds['max'])
        
        center = (min_point + max_point) / 2
        size = np.linalg.norm(max_point - min_point)
        
        # Position camera
        distance = size * 2.0
        self.state.camera_position = center + np.array([0, 0, distance])
        self.state.camera_target = center
        
        print(f"[Viewer] Fitted to bounds, distance={distance:.2f}")


class MeasurementTools:
    """
    3D measurement tools for quantitative analysis.
    
    Enables:
    - Distance measurement between points
    - Angle measurement
    - Area calculation
    - Volume estimation
    - Annotations
    """
    
    def __init__(self):
        """Initialize measurement tools."""
        self.measurements: List[Measurement] = []
        self.active_measurement: Optional[Measurement] = None
        
        # Calibration (mm per unit)
        self.scale_factor = 1.0
        
    def start_measurement(self, measurement_type: MeasurementType) -> str:
        """
        Start new measurement.
        
        Args:
            measurement_type: Type of measurement
            
        Returns:
            Measurement ID
        """
        measurement_id = f"measure_{datetime.now().timestamp()}"
        
        self.active_measurement = Measurement(
            measurement_id=measurement_id,
            measurement_type=measurement_type,
            timestamp=datetime.now(),
            points=[],
            value=0.0,
            unit="mm"
        )
        
        print(f"[Measurement] Started {measurement_type.value}")
        return measurement_id
    
    def add_point(self, point: np.ndarray) -> None:
        """
        Add point to active measurement.
        
        Args:
            point: 3D point coordinates
        """
        if self.active_measurement is None:
            raise ValueError("No active measurement")
        
        self.active_measurement.points.append(point)
        
        # Update measurement value
        self._update_measurement_value()
        
        print(f"[Measurement] Added point {len(self.active_measurement.points)}")
    
    def _update_measurement_value(self) -> None:
        """Update measurement value based on points."""
        if not self.active_measurement:
            return
        
        points = self.active_measurement.points
        m_type = self.active_measurement.measurement_type
        
        if m_type == MeasurementType.DISTANCE:
            if len(points) >= 2:
                distance = np.linalg.norm(points[-1] - points[-2])
                self.active_measurement.value = distance * self.scale_factor
        
        elif m_type == MeasurementType.ANGLE:
            if len(points) >= 3:
                # Calculate angle between three points
                v1 = points[0] - points[1]
                v2 = points[2] - points[1]
                
                cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                angle = np.arccos(np.clip(cos_angle, -1, 1))
                
                self.active_measurement.value = np.degrees(angle)
                self.active_measurement.unit = "degrees"
        
        elif m_type == MeasurementType.AREA:
            if len(points) >= 3:
                # Triangulate polygon and sum areas
                area = self._calculate_polygon_area(points)
                self.active_measurement.value = area * (self.scale_factor ** 2)
                self.active_measurement.unit = "mm²"
        
        elif m_type == MeasurementType.DIAMETER:
            if len(points) >= 2:
                diameter = np.linalg.norm(points[-1] - points[-2])
                self.active_measurement.value = diameter * self.scale_factor
    
    def _calculate_polygon_area(self, points: List[np.ndarray]) -> float:
        """Calculate area of polygon defined by points."""
        if len(points) < 3:
            return 0.0
        
        # Project to 2D (use XY plane)
        points_2d = np.array([[p[0], p[1]] for p in points])
        
        # Shoelace formula
        x = points_2d[:, 0]
        y = points_2d[:, 1]
        
        area = 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
        
        return area
    
    def finish_measurement(self, label: str = "") -> Measurement:
        """
        Finish active measurement.
        
        Args:
            label: Optional label for measurement
            
        Returns:
            Completed measurement
        """
        if self.active_measurement is None:
            raise ValueError("No active measurement")
        
        self.active_measurement.label = label
        self.measurements.append(self.active_measurement)
        
        result = self.active_measurement
        self.active_measurement = None
        
        print(f"[Measurement] Finished: {result.value:.2f} {result.unit}")
        
        return result
    
    def delete_measurement(self, measurement_id: str) -> bool:
        """
        Delete measurement.
        
        Args:
            measurement_id: Measurement to delete
            
        Returns:
            Success status
        """
        for i, m in enumerate(self.measurements):
            if m.measurement_id == measurement_id:
                del self.measurements[i]
                print(f"[Measurement] Deleted: {measurement_id}")
                return True
        
        return False
    
    def set_scale(self, known_distance: float, measured_distance: float) -> None:
        """
        Calibrate scale using known distance.
        
        Args:
            known_distance: Real-world distance (mm)
            measured_distance: Measured distance in 3D space
        """
        self.scale_factor = known_distance / measured_distance
        print(f"[Measurement] Scale calibrated: {self.scale_factor:.4f} mm/unit")
    
    def get_all_measurements(self) -> List[Dict]:
        """Get all measurements as dictionaries."""
        return [
            {
                'id': m.measurement_id,
                'type': m.measurement_type.value,
                'value': m.value,
                'unit': m.unit,
                'label': m.label,
                'num_points': len(m.points),
                'timestamp': m.timestamp.isoformat()
            }
            for m in self.measurements
        ]


class ExportUtilities:
    """
    Export utilities for screenshots, videos, and 3D models.
    
    Supports multiple formats:
    - Images: PNG, JPG
    - Videos: MP4, GIF
    - 3D models: OBJ, PLY, STL, glTF/GLB
    """
    
    def __init__(self):
        """Initialize export utilities."""
        self.export_history = []
        
    def export_screenshot(
        self,
        filename: str,
        format: ExportFormat = ExportFormat.PNG,
        resolution: Tuple[int, int] = (1920, 1080)
    ) -> Dict:
        """
        Export screenshot of current view.
        
        Args:
            filename: Output filename
            format: Image format
            resolution: Image resolution
            
        Returns:
            Export result
        """
        print(f"[Export] Capturing screenshot: {filename}")
        
        # Generate JavaScript code for capture
        js_code = f"""
// Capture screenshot
renderer.setSize({resolution[0]}, {resolution[1]});
renderer.render(scene, camera);

const dataURL = renderer.domElement.toDataURL('image/{format.value}');
const link = document.createElement('a');
link.download = '{filename}';
link.href = dataURL;
link.click();
"""
        
        result = {
            'success': True,
            'filename': filename,
            'format': format.value,
            'resolution': resolution,
            'code': js_code,
            'timestamp': datetime.now().isoformat()
        }
        
        self.export_history.append(result)
        
        return result
    
    def export_video(
        self,
        filename: str,
        duration: float = 5.0,
        fps: int = 30,
        rotation: bool = True
    ) -> Dict:
        """
        Export video of 3D model.
        
        Args:
            filename: Output filename
            duration: Video duration in seconds
            fps: Frames per second
            rotation: Rotate model during recording
            
        Returns:
            Export result
        """
        print(f"[Export] Recording video: {filename} ({duration}s @ {fps}fps)")
        
        num_frames = int(duration * fps)
        
        # Generate video capture code
        js_code = f"""
// Video capture setup
const capturer = new CCapture({{
    format: 'webm',
    framerate: {fps},
    name: '{filename}'
}});

let frame = 0;
const totalFrames = {num_frames};

capturer.start();

function captureFrame() {{
    if (frame < totalFrames) {{
        {"camera.position.x = Math.cos(frame / totalFrames * Math.PI * 2) * 5;" if rotation else ""}
        {"camera.position.z = Math.sin(frame / totalFrames * Math.PI * 2) * 5;" if rotation else ""}
        camera.lookAt(0, 0, 0);
        
        renderer.render(scene, camera);
        capturer.capture(renderer.domElement);
        
        frame++;
        requestAnimationFrame(captureFrame);
    }} else {{
        capturer.stop();
        capturer.save();
    }}
}}

captureFrame();
"""
        
        result = {
            'success': True,
            'filename': filename,
            'duration': duration,
            'fps': fps,
            'frames': num_frames,
            'code': js_code,
            'timestamp': datetime.now().isoformat()
        }
        
        self.export_history.append(result)
        
        return result
    
    def export_3d_model(
        self,
        filename: str,
        format: ExportFormat,
        vertices: np.ndarray,
        faces: Optional[np.ndarray] = None,
        vertex_colors: Optional[np.ndarray] = None,
        normals: Optional[np.ndarray] = None
    ) -> Dict:
        """
        Export 3D model to file.
        
        Args:
            filename: Output filename
            format: 3D format
            vertices: Vertex coordinates
            faces: Face indices
            vertex_colors: Vertex colors
            normals: Vertex normals
            
        Returns:
            Export result
        """
        print(f"[Export] Exporting 3D model: {filename} ({format.value})")
        
        if format == ExportFormat.OBJ:
            content = self._generate_obj(vertices, faces, vertex_colors, normals)
        elif format == ExportFormat.PLY:
            content = self._generate_ply(vertices, faces, vertex_colors)
        elif format == ExportFormat.STL:
            content = self._generate_stl(vertices, faces, normals)
        elif format in [ExportFormat.GLTF, ExportFormat.GLB]:
            content = self._generate_gltf(vertices, faces, vertex_colors, normals)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        result = {
            'success': True,
            'filename': filename,
            'format': format.value,
            'num_vertices': len(vertices),
            'num_faces': len(faces) if faces is not None else 0,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        
        self.export_history.append(result)
        
        return result
    
    def _generate_obj(
        self,
        vertices: np.ndarray,
        faces: Optional[np.ndarray],
        vertex_colors: Optional[np.ndarray],
        normals: Optional[np.ndarray]
    ) -> str:
        """Generate OBJ file content."""
        lines = ["# OBJ file generated by AgroPulse\n"]
        
        # Vertices
        for i, v in enumerate(vertices):
            if vertex_colors is not None:
                c = vertex_colors[i]
                lines.append(f"v {v[0]} {v[1]} {v[2]} {c[0]} {c[1]} {c[2]}\n")
            else:
                lines.append(f"v {v[0]} {v[1]} {v[2]}\n")
        
        # Normals
        if normals is not None:
            for n in normals:
                lines.append(f"vn {n[0]} {n[1]} {n[2]}\n")
        
        # Faces
        if faces is not None:
            for f in faces:
                # OBJ indices are 1-based
                lines.append(f"f {f[0]+1} {f[1]+1} {f[2]+1}\n")
        
        return ''.join(lines)
    
    def _generate_ply(
        self,
        vertices: np.ndarray,
        faces: Optional[np.ndarray],
        vertex_colors: Optional[np.ndarray]
    ) -> str:
        """Generate PLY file content."""
        has_colors = vertex_colors is not None
        has_faces = faces is not None
        
        lines = [
            "ply\n",
            "format ascii 1.0\n",
            f"element vertex {len(vertices)}\n",
            "property float x\n",
            "property float y\n",
            "property float z\n"
        ]
        
        if has_colors:
            lines.extend([
                "property uchar red\n",
                "property uchar green\n",
                "property uchar blue\n"
            ])
        
        if has_faces:
            lines.append(f"element face {len(faces)}\n")
            lines.append("property list uchar int vertex_indices\n")
        
        lines.append("end_header\n")
        
        # Vertex data
        for i, v in enumerate(vertices):
            if has_colors:
                c = (vertex_colors[i] * 255).astype(int)
                lines.append(f"{v[0]} {v[1]} {v[2]} {c[0]} {c[1]} {c[2]}\n")
            else:
                lines.append(f"{v[0]} {v[1]} {v[2]}\n")
        
        # Face data
        if has_faces:
            for f in faces:
                lines.append(f"3 {f[0]} {f[1]} {f[2]}\n")
        
        return ''.join(lines)
    
    def _generate_stl(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        normals: Optional[np.ndarray]
    ) -> str:
        """Generate STL file content."""
        if faces is None:
            raise ValueError("STL format requires faces")
        
        lines = ["solid model\n"]
        
        for f in faces:
            # Get face vertices
            v0, v1, v2 = vertices[f[0]], vertices[f[1]], vertices[f[2]]
            
            # Calculate face normal if not provided
            if normals is not None:
                n = normals[f[0]]  # Use first vertex normal
            else:
                edge1 = v1 - v0
                edge2 = v2 - v0
                n = np.cross(edge1, edge2)
                n = n / np.linalg.norm(n)
            
            lines.append(f"  facet normal {n[0]} {n[1]} {n[2]}\n")
            lines.append("    outer loop\n")
            lines.append(f"      vertex {v0[0]} {v0[1]} {v0[2]}\n")
            lines.append(f"      vertex {v1[0]} {v1[1]} {v1[2]}\n")
            lines.append(f"      vertex {v2[0]} {v2[1]} {v2[2]}\n")
            lines.append("    endloop\n")
            lines.append("  endfacet\n")
        
        lines.append("endsolid model\n")
        
        return ''.join(lines)
    
    def _generate_gltf(
        self,
        vertices: np.ndarray,
        faces: Optional[np.ndarray],
        vertex_colors: Optional[np.ndarray],
        normals: Optional[np.ndarray]
    ) -> str:
        """Generate glTF file content."""
        # glTF is JSON-based
        gltf = {
            "asset": {
                "version": "2.0",
                "generator": "AgroPulse 3D Visualization Engine"
            },
            "scene": 0,
            "scenes": [
                {
                    "nodes": [0]
                }
            ],
            "nodes": [
                {
                    "mesh": 0
                }
            ],
            "meshes": [
                {
                    "primitives": [
                        {
                            "attributes": {
                                "POSITION": 0
                            },
                            "mode": 4  # TRIANGLES
                        }
                    ]
                }
            ],
            "accessors": [
                {
                    "bufferView": 0,
                    "componentType": 5126,  # FLOAT
                    "count": len(vertices),
                    "type": "VEC3",
                    "max": vertices.max(axis=0).tolist(),
                    "min": vertices.min(axis=0).tolist()
                }
            ],
            "bufferViews": [
                {
                    "buffer": 0,
                    "byteLength": len(vertices) * 12,  # 3 floats * 4 bytes
                    "target": 34962  # ARRAY_BUFFER
                }
            ],
            "buffers": [
                {
                    "byteLength": len(vertices) * 12
                }
            ]
        }
        
        return json.dumps(gltf, indent=2)
    
    def get_export_history(self) -> List[Dict]:
        """Get export history."""
        return self.export_history
