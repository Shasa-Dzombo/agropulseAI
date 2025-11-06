// =====================================================================================================================
// ESP32 Robotics & Control Systems
// Kinematics, dynamics, path planning, SLAM, PID control, motion control
// =====================================================================================================================

#include <Arduino.h>
#include <math.h>

// =====================================================================================================================
// Robotics Structures
// =====================================================================================================================

#define MAX_JOINTS 10
#define MAX_WAYPOINTS 100
#define MAX_OBSTACLES 50
#define MAX_PATH_NODES 500
#define MAX_PARTICLES 200
#define GRID_SIZE 100

// 3D Vector
typedef struct {
    float x;
    float y;
    float z;
} Vector3;

// Quaternion for rotation
typedef struct {
    float w;
    float x;
    float y;
    float z;
} Quaternion;

// 4x4 Transform matrix
typedef struct {
    float data[16];
} Matrix4x4;

// 3x3 Rotation matrix
typedef struct {
    float data[9];
} Matrix3x3;

// Euler angles
typedef struct {
    float roll;   // Rotation around X
    float pitch;  // Rotation around Y
    float yaw;    // Rotation around Z
} EulerAngles;

// Joint types
typedef enum {
    JOINT_REVOLUTE,
    JOINT_PRISMATIC,
    JOINT_CONTINUOUS,
    JOINT_FIXED
} JointType;

// Single joint
typedef struct {
    JointType type;
    float position;     // Angle for revolute, distance for prismatic
    float velocity;
    float acceleration;
    float torque;       // Applied torque/force
    float min_limit;
    float max_limit;
    float mass;
    float inertia;
    float friction;
    float damping;
    Vector3 axis;
} Joint;

// DH parameters (Denavit-Hartenberg)
typedef struct {
    float a;      // Link length
    float alpha;  // Link twist
    float d;      // Link offset
    float theta;  // Joint angle
} DHParameters;

// Robot arm configuration
typedef struct {
    Joint joints[MAX_JOINTS];
    DHParameters dh_params[MAX_JOINTS];
    uint32_t num_joints;
    Vector3 end_effector_pos;
    Quaternion end_effector_rot;
    Matrix4x4 forward_kinematics;
    float** jacobian;  // 6 x num_joints
} RobotArm;

// Mobile robot
typedef enum {
    ROBOT_DIFFERENTIAL_DRIVE,
    ROBOT_ACKERMANN,
    ROBOT_MECANUM,
    ROBOT_OMNIDIRECTIONAL
} RobotType;

typedef struct {
    RobotType type;
    Vector3 position;
    EulerAngles orientation;
    Vector3 velocity;
    Vector3 angular_velocity;
    float wheel_radius;
    float wheel_base;
    float max_velocity;
    float max_acceleration;
    float max_angular_velocity;
} MobileRobot;

// PID Controller
typedef struct {
    float kp;  // Proportional gain
    float ki;  // Integral gain
    float kd;  // Derivative gain
    float setpoint;
    float error;
    float previous_error;
    float integral;
    float derivative;
    float output;
    float output_min;
    float output_max;
    float integral_max;  // Anti-windup
    uint64_t last_time;
} PIDController;

// Trajectory point
typedef struct {
    Vector3 position;
    Vector3 velocity;
    Vector3 acceleration;
    EulerAngles orientation;
    float timestamp;
} TrajectoryPoint;

// Trajectory
typedef struct {
    TrajectoryPoint* points;
    uint32_t num_points;
    float duration;
    float current_time;
    uint32_t current_index;
} Trajectory;

// Path planner types
typedef enum {
    PLANNER_A_STAR,
    PLANNER_RRT,
    PLANNER_RRT_STAR,
    PLANNER_PRM,
    PLANNER_DIJKSTRA
} PlannerType;

// Grid cell for path planning
typedef struct {
    uint32_t x;
    uint32_t y;
    bool occupied;
    float cost;
    float heuristic;
    float total_cost;
    int32_t parent_x;
    int32_t parent_y;
    bool visited;
} GridCell;

// Occupancy grid
typedef struct {
    GridCell cells[GRID_SIZE][GRID_SIZE];
    float resolution;  // meters per cell
    Vector3 origin;
    uint32_t width;
    uint32_t height;
} OccupancyGrid;

// Obstacle
typedef struct {
    Vector3 position;
    float radius;
    Vector3 velocity;
    bool is_dynamic;
} Obstacle;

// RRT Node
typedef struct {
    Vector3 position;
    int32_t parent_index;
    float cost;
} RRTNode;

// RRT Tree
typedef struct {
    RRTNode* nodes;
    uint32_t node_count;
    uint32_t max_nodes;
    float step_size;
    float goal_threshold;
} RRTTree;

// Path
typedef struct {
    Vector3* waypoints;
    uint32_t waypoint_count;
    float total_length;
    bool smooth;
} Path;

// SLAM particle
typedef struct {
    Vector3 position;
    EulerAngles orientation;
    float weight;
    OccupancyGrid map;
} SLAMParticle;

// Particle filter for SLAM
typedef struct {
    SLAMParticle particles[MAX_PARTICLES];
    uint32_t num_particles;
    Vector3 estimated_position;
    EulerAngles estimated_orientation;
} ParticleFilter;

// Laser scan
typedef struct {
    float* ranges;
    float* angles;
    uint32_t num_readings;
    float min_angle;
    float max_angle;
    float angle_increment;
    float min_range;
    float max_range;
    uint64_t timestamp;
} LaserScan;

// IMU data
typedef struct {
    Vector3 linear_acceleration;
    Vector3 angular_velocity;
    Quaternion orientation;
    float temperature;
    uint64_t timestamp;
} IMUData;

// Odometry
typedef struct {
    Vector3 position;
    EulerAngles orientation;
    Vector3 linear_velocity;
    Vector3 angular_velocity;
    Matrix3x3 covariance_position;
    Matrix3x3 covariance_orientation;
    uint64_t timestamp;
} Odometry;

// Extended Kalman Filter for localization
typedef struct {
    float* state;            // [x, y, theta, vx, vy, omega]
    float** covariance;      // 6x6 matrix
    float** process_noise;   // Q matrix
    float** measurement_noise; // R matrix
    uint32_t state_size;
} EKF;

// Motion model
typedef enum {
    MOTION_VELOCITY,
    MOTION_ODOMETRY,
    MOTION_SAMPLE
} MotionModel;

// Sensor model
typedef enum {
    SENSOR_BEAM,
    SENSOR_LIKELIHOOD_FIELD
} SensorModel;

// Inverse kinematics solver
typedef enum {
    IK_JACOBIAN_TRANSPOSE,
    IK_JACOBIAN_PSEUDOINVERSE,
    IK_DAMPED_LEAST_SQUARES,
    IK_CCD,  // Cyclic Coordinate Descent
    IK_FABRIK  // Forward And Backward Reaching Inverse Kinematics
} IKSolver;

// Grasp
typedef struct {
    Vector3 position;
    Quaternion orientation;
    float grip_strength;
    float approach_distance;
} Grasp;

// Force/Torque sensor
typedef struct {
    Vector3 force;
    Vector3 torque;
    uint64_t timestamp;
} ForceTorqueSensor;

// Impedance control
typedef struct {
    float stiffness;
    float damping;
    float mass;
    Vector3 desired_position;
    Vector3 desired_velocity;
    Vector3 measured_force;
} ImpedanceController;

// =====================================================================================================================
// Global Robotics State
// =====================================================================================================================

RobotArm g_robot_arm;
MobileRobot g_mobile_robot;
PIDController g_pid_controllers[MAX_JOINTS];
OccupancyGrid g_occupancy_grid;
ParticleFilter g_particle_filter;
Path g_planned_path;
EKF g_ekf;

// =====================================================================================================================
// Vector Operations
// =====================================================================================================================

Vector3 vec3_add(Vector3 a, Vector3 b) {
    Vector3 result = {a.x + b.x, a.y + b.y, a.z + b.z};
    return result;
}

Vector3 vec3_sub(Vector3 a, Vector3 b) {
    Vector3 result = {a.x - b.x, a.y - b.y, a.z - b.z};
    return result;
}

Vector3 vec3_scale(Vector3 v, float s) {
    Vector3 result = {v.x * s, v.y * s, v.z * s};
    return result;
}

float vec3_dot(Vector3 a, Vector3 b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

Vector3 vec3_cross(Vector3 a, Vector3 b) {
    Vector3 result;
    result.x = a.y * b.z - a.z * b.y;
    result.y = a.z * b.x - a.x * b.z;
    result.z = a.x * b.y - a.y * b.x;
    return result;
}

float vec3_magnitude(Vector3 v) {
    return sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
}

Vector3 vec3_normalize(Vector3 v) {
    float mag = vec3_magnitude(v);
    if (mag > 0.0001f) {
        return vec3_scale(v, 1.0f / mag);
    }
    return v;
}

float vec3_distance(Vector3 a, Vector3 b) {
    return vec3_magnitude(vec3_sub(a, b));
}

// =====================================================================================================================
// Quaternion Operations
// =====================================================================================================================

Quaternion quat_identity() {
    Quaternion q = {1.0f, 0.0f, 0.0f, 0.0f};
    return q;
}

Quaternion quat_multiply(Quaternion a, Quaternion b) {
    Quaternion result;
    result.w = a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z;
    result.x = a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y;
    result.y = a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x;
    result.z = a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w;
    return result;
}

Quaternion quat_normalize(Quaternion q) {
    float mag = sqrt(q.w * q.w + q.x * q.x + q.y * q.y + q.z * q.z);
    if (mag > 0.0001f) {
        q.w /= mag;
        q.x /= mag;
        q.y /= mag;
        q.z /= mag;
    }
    return q;
}

Quaternion quat_from_euler(EulerAngles euler) {
    float cy = cos(euler.yaw * 0.5f);
    float sy = sin(euler.yaw * 0.5f);
    float cp = cos(euler.pitch * 0.5f);
    float sp = sin(euler.pitch * 0.5f);
    float cr = cos(euler.roll * 0.5f);
    float sr = sin(euler.roll * 0.5f);
    
    Quaternion q;
    q.w = cr * cp * cy + sr * sp * sy;
    q.x = sr * cp * cy - cr * sp * sy;
    q.y = cr * sp * cy + sr * cp * sy;
    q.z = cr * cp * sy - sr * sp * cy;
    
    return quat_normalize(q);
}

EulerAngles quat_to_euler(Quaternion q) {
    EulerAngles euler;
    
    // Roll (x-axis rotation)
    float sinr_cosp = 2.0f * (q.w * q.x + q.y * q.z);
    float cosr_cosp = 1.0f - 2.0f * (q.x * q.x + q.y * q.y);
    euler.roll = atan2(sinr_cosp, cosr_cosp);
    
    // Pitch (y-axis rotation)
    float sinp = 2.0f * (q.w * q.y - q.z * q.x);
    if (fabs(sinp) >= 1.0f)
        euler.pitch = copysign(PI / 2.0f, sinp);
    else
        euler.pitch = asin(sinp);
    
    // Yaw (z-axis rotation)
    float siny_cosp = 2.0f * (q.w * q.z + q.x * q.y);
    float cosy_cosp = 1.0f - 2.0f * (q.y * q.y + q.z * q.z);
    euler.yaw = atan2(siny_cosp, cosy_cosp);
    
    return euler;
}

Vector3 quat_rotate_vector(Quaternion q, Vector3 v) {
    Quaternion v_quat = {0.0f, v.x, v.y, v.z};
    Quaternion q_conj = {q.w, -q.x, -q.y, -q.z};
    Quaternion result = quat_multiply(quat_multiply(q, v_quat), q_conj);
    
    Vector3 rotated = {result.x, result.y, result.z};
    return rotated;
}

// =====================================================================================================================
// Matrix Operations
// =====================================================================================================================

void matrix4x4_identity(Matrix4x4* m) {
    memset(m->data, 0, sizeof(m->data));
    m->data[0] = m->data[5] = m->data[10] = m->data[15] = 1.0f;
}

void matrix4x4_from_dh(Matrix4x4* m, DHParameters dh) {
    float ca = cos(dh.alpha);
    float sa = sin(dh.alpha);
    float ct = cos(dh.theta);
    float st = sin(dh.theta);
    
    m->data[0] = ct;
    m->data[1] = -st * ca;
    m->data[2] = st * sa;
    m->data[3] = dh.a * ct;
    
    m->data[4] = st;
    m->data[5] = ct * ca;
    m->data[6] = -ct * sa;
    m->data[7] = dh.a * st;
    
    m->data[8] = 0;
    m->data[9] = sa;
    m->data[10] = ca;
    m->data[11] = dh.d;
    
    m->data[12] = 0;
    m->data[13] = 0;
    m->data[14] = 0;
    m->data[15] = 1;
}

void matrix4x4_multiply(Matrix4x4* result, const Matrix4x4* a, const Matrix4x4* b) {
    for (int i = 0; i < 4; i++) {
        for (int j = 0; j < 4; j++) {
            result->data[i * 4 + j] = 0.0f;
            for (int k = 0; k < 4; k++) {
                result->data[i * 4 + j] += a->data[i * 4 + k] * b->data[k * 4 + j];
            }
        }
    }
}

Vector3 matrix4x4_transform_point(const Matrix4x4* m, Vector3 p) {
    Vector3 result;
    result.x = m->data[0] * p.x + m->data[1] * p.y + m->data[2] * p.z + m->data[3];
    result.y = m->data[4] * p.x + m->data[5] * p.y + m->data[6] * p.z + m->data[7];
    result.z = m->data[8] * p.x + m->data[9] * p.y + m->data[10] * p.z + m->data[11];
    return result;
}

// =====================================================================================================================
// Forward Kinematics
// =====================================================================================================================

void robot_arm_forward_kinematics(RobotArm* arm) {
    Matrix4x4 transform;
    matrix4x4_identity(&transform);
    
    for (uint32_t i = 0; i < arm->num_joints; i++) {
        // Update DH theta parameter for revolute joints
        if (arm->joints[i].type == JOINT_REVOLUTE) {
            arm->dh_params[i].theta = arm->joints[i].position;
        } else if (arm->joints[i].type == JOINT_PRISMATIC) {
            arm->dh_params[i].d = arm->joints[i].position;
        }
        
        // Compute transformation matrix for this link
        Matrix4x4 link_transform;
        matrix4x4_from_dh(&link_transform, arm->dh_params[i]);
        
        // Accumulate transformation
        Matrix4x4 temp;
        matrix4x4_multiply(&temp, &transform, &link_transform);
        transform = temp;
        
        yield();
    }
    
    arm->forward_kinematics = transform;
    
    // Extract end effector position
    arm->end_effector_pos.x = transform.data[3];
    arm->end_effector_pos.y = transform.data[7];
    arm->end_effector_pos.z = transform.data[11];
    
    Serial.printf("[Robotics] End effector position: (%.2f, %.2f, %.2f)\n",
                  arm->end_effector_pos.x, arm->end_effector_pos.y,
                  arm->end_effector_pos.z);
}

// =====================================================================================================================
// Inverse Kinematics (Jacobian method)
// =====================================================================================================================

void robot_arm_compute_jacobian(RobotArm* arm) {
    if (!arm->jacobian) {
        arm->jacobian = (float**)malloc(sizeof(float*) * 6);
        for (int i = 0; i < 6; i++) {
            arm->jacobian[i] = (float*)malloc(sizeof(float) * arm->num_joints);
        }
    }
    
    Vector3 end_effector = arm->end_effector_pos;
    
    for (uint32_t i = 0; i < arm->num_joints; i++) {
        // Compute position of joint i
        Matrix4x4 transform_to_joint;
        matrix4x4_identity(&transform_to_joint);
        
        for (uint32_t j = 0; j <= i; j++) {
            Matrix4x4 link_transform;
            matrix4x4_from_dh(&link_transform, arm->dh_params[j]);
            
            Matrix4x4 temp;
            matrix4x4_multiply(&temp, &transform_to_joint, &link_transform);
            transform_to_joint = temp;
        }
        
        Vector3 joint_pos = {transform_to_joint.data[3],
                            transform_to_joint.data[7],
                            transform_to_joint.data[11]};
        
        Vector3 z_axis = {transform_to_joint.data[2],
                         transform_to_joint.data[6],
                         transform_to_joint.data[10]};
        
        if (arm->joints[i].type == JOINT_REVOLUTE) {
            Vector3 r = vec3_sub(end_effector, joint_pos);
            Vector3 linear_vel = vec3_cross(z_axis, r);
            
            arm->jacobian[0][i] = linear_vel.x;
            arm->jacobian[1][i] = linear_vel.y;
            arm->jacobian[2][i] = linear_vel.z;
            arm->jacobian[3][i] = z_axis.x;
            arm->jacobian[4][i] = z_axis.y;
            arm->jacobian[5][i] = z_axis.z;
        } else {
            arm->jacobian[0][i] = z_axis.x;
            arm->jacobian[1][i] = z_axis.y;
            arm->jacobian[2][i] = z_axis.z;
            arm->jacobian[3][i] = 0.0f;
            arm->jacobian[4][i] = 0.0f;
            arm->jacobian[5][i] = 0.0f;
        }
        
        yield();
    }
}

bool robot_arm_inverse_kinematics(RobotArm* arm, Vector3 target_pos,
                                  uint32_t max_iterations, float tolerance) {
    for (uint32_t iter = 0; iter < max_iterations; iter++) {
        // Compute forward kinematics
        robot_arm_forward_kinematics(arm);
        
        // Compute error
        Vector3 error = vec3_sub(target_pos, arm->end_effector_pos);
        float error_magnitude = vec3_magnitude(error);
        
        if (error_magnitude < tolerance) {
            Serial.printf("[Robotics] IK converged in %d iterations\n", iter);
            return true;
        }
        
        // Compute Jacobian
        robot_arm_compute_jacobian(arm);
        
        // Compute joint angle updates (Jacobian transpose method)
        float alpha = 0.5f;  // Step size
        
        for (uint32_t i = 0; i < arm->num_joints; i++) {
            float delta = alpha * (arm->jacobian[0][i] * error.x +
                                  arm->jacobian[1][i] * error.y +
                                  arm->jacobian[2][i] * error.z);
            
            arm->joints[i].position += delta;
            
            // Apply joint limits
            if (arm->joints[i].position < arm->joints[i].min_limit) {
                arm->joints[i].position = arm->joints[i].min_limit;
            }
            if (arm->joints[i].position > arm->joints[i].max_limit) {
                arm->joints[i].position = arm->joints[i].max_limit;
            }
        }
        
        if (iter % 10 == 0) yield();
    }
    
    Serial.println("[Robotics] IK failed to converge");
    return false;
}

// =====================================================================================================================
// PID Controller
// =====================================================================================================================

void pid_init(PIDController* pid, float kp, float ki, float kd) {
    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
    pid->setpoint = 0.0f;
    pid->error = 0.0f;
    pid->previous_error = 0.0f;
    pid->integral = 0.0f;
    pid->derivative = 0.0f;
    pid->output = 0.0f;
    pid->output_min = -1000.0f;
    pid->output_max = 1000.0f;
    pid->integral_max = 100.0f;
    pid->last_time = millis();
}

float pid_update(PIDController* pid, float measurement) {
    uint64_t current_time = millis();
    float dt = (current_time - pid->last_time) / 1000.0f;
    pid->last_time = current_time;
    
    if (dt <= 0.0f) return pid->output;
    
    // Compute error
    pid->error = pid->setpoint - measurement;
    
    // Proportional term
    float p_term = pid->kp * pid->error;
    
    // Integral term with anti-windup
    pid->integral += pid->error * dt;
    if (pid->integral > pid->integral_max) pid->integral = pid->integral_max;
    if (pid->integral < -pid->integral_max) pid->integral = -pid->integral_max;
    float i_term = pid->ki * pid->integral;
    
    // Derivative term
    pid->derivative = (pid->error - pid->previous_error) / dt;
    float d_term = pid->kd * pid->derivative;
    
    // Compute output
    pid->output = p_term + i_term + d_term;
    
    // Clamp output
    if (pid->output > pid->output_max) pid->output = pid->output_max;
    if (pid->output < pid->output_min) pid->output = pid->output_min;
    
    pid->previous_error = pid->error;
    
    return pid->output;
}

void pid_reset(PIDController* pid) {
    pid->error = 0.0f;
    pid->previous_error = 0.0f;
    pid->integral = 0.0f;
    pid->derivative = 0.0f;
    pid->output = 0.0f;
    pid->last_time = millis();
}

// =====================================================================================================================
// Differential Drive Kinematics
// =====================================================================================================================

void differential_drive_forward_kinematics(MobileRobot* robot,
                                          float left_wheel_vel,
                                          float right_wheel_vel,
                                          float dt) {
    float v = (right_wheel_vel + left_wheel_vel) * robot->wheel_radius / 2.0f;
    float omega = (right_wheel_vel - left_wheel_vel) * robot->wheel_radius /
                  robot->wheel_base;
    
    // Update orientation
    robot->orientation.yaw += omega * dt;
    
    // Normalize yaw to [-pi, pi]
    while (robot->orientation.yaw > PI) robot->orientation.yaw -= 2.0f * PI;
    while (robot->orientation.yaw < -PI) robot->orientation.yaw += 2.0f * PI;
    
    // Update position
    robot->position.x += v * cos(robot->orientation.yaw) * dt;
    robot->position.y += v * sin(robot->orientation.yaw) * dt;
    
    robot->velocity.x = v * cos(robot->orientation.yaw);
    robot->velocity.y = v * sin(robot->orientation.yaw);
    robot->angular_velocity.z = omega;
}

void differential_drive_inverse_kinematics(MobileRobot* robot,
                                          float linear_vel, float angular_vel,
                                          float* left_wheel_vel,
                                          float* right_wheel_vel) {
    *left_wheel_vel = (linear_vel - angular_vel * robot->wheel_base / 2.0f) /
                      robot->wheel_radius;
    *right_wheel_vel = (linear_vel + angular_vel * robot->wheel_base / 2.0f) /
                       robot->wheel_radius;
}

// =====================================================================================================================
// Path Planning - A* Algorithm
// =====================================================================================================================

void occupancy_grid_init(OccupancyGrid* grid, float resolution, Vector3 origin) {
    grid->resolution = resolution;
    grid->origin = origin;
    grid->width = GRID_SIZE;
    grid->height = GRID_SIZE;
    
    for (uint32_t y = 0; y < grid->height; y++) {
        for (uint32_t x = 0; x < grid->width; x++) {
            grid->cells[y][x].x = x;
            grid->cells[y][x].y = y;
            grid->cells[y][x].occupied = false;
            grid->cells[y][x].cost = 0.0f;
            grid->cells[y][x].visited = false;
        }
    }
}

float heuristic_manhattan(uint32_t x1, uint32_t y1, uint32_t x2, uint32_t y2) {
    return fabs((float)x1 - x2) + fabs((float)y1 - y2);
}

bool astar_plan_path(OccupancyGrid* grid, Vector3 start, Vector3 goal, Path* path) {
    // Convert world coordinates to grid coordinates
    uint32_t start_x = (uint32_t)((start.x - grid->origin.x) / grid->resolution);
    uint32_t start_y = (uint32_t)((start.y - grid->origin.y) / grid->resolution);
    uint32_t goal_x = (uint32_t)((goal.x - grid->origin.x) / grid->resolution);
    uint32_t goal_y = (uint32_t)((goal.y - grid->origin.y) / grid->resolution);
    
    // Initialize start cell
    grid->cells[start_y][start_x].cost = 0.0f;
    grid->cells[start_y][start_x].heuristic = heuristic_manhattan(start_x, start_y,
                                                                   goal_x, goal_y);
    grid->cells[start_y][start_x].total_cost = grid->cells[start_y][start_x].heuristic;
    
    // Simple priority queue (replace with heap for efficiency)
    GridCell* open_set[MAX_PATH_NODES];
    uint32_t open_count = 0;
    
    open_set[open_count++] = &grid->cells[start_y][start_x];
    
    while (open_count > 0) {
        // Find cell with lowest f-score
        uint32_t current_idx = 0;
        for (uint32_t i = 1; i < open_count; i++) {
            if (open_set[i]->total_cost < open_set[current_idx]->total_cost) {
                current_idx = i;
            }
        }
        
        GridCell* current = open_set[current_idx];
        
        // Check if goal reached
        if (current->x == goal_x && current->y == goal_y) {
            Serial.println("[Robotics] Path found!");
            
            // Reconstruct path
            path->waypoint_count = 0;
            path->waypoints = (Vector3*)malloc(sizeof(Vector3) * MAX_WAYPOINTS);
            
            GridCell* cell = current;
            while (!(cell->x == start_x && cell->y == start_y)) {
                Vector3 waypoint;
                waypoint.x = grid->origin.x + cell->x * grid->resolution;
                waypoint.y = grid->origin.y + cell->y * grid->resolution;
                waypoint.z = 0.0f;
                
                path->waypoints[path->waypoint_count++] = waypoint;
                
                cell = &grid->cells[cell->parent_y][cell->parent_x];
            }
            
            // Reverse path
            for (uint32_t i = 0; i < path->waypoint_count / 2; i++) {
                Vector3 temp = path->waypoints[i];
                path->waypoints[i] = path->waypoints[path->waypoint_count - 1 - i];
                path->waypoints[path->waypoint_count - 1 - i] = temp;
            }
            
            return true;
        }
        
        // Remove current from open set
        for (uint32_t i = current_idx; i < open_count - 1; i++) {
            open_set[i] = open_set[i + 1];
        }
        open_count--;
        
        current->visited = true;
        
        // Explore neighbors
        int32_t dx[] = {-1, 0, 1, 0, -1, 1, 1, -1};
        int32_t dy[] = {0, 1, 0, -1, 1, 1, -1, -1};
        
        for (int i = 0; i < 8; i++) {
            int32_t nx = current->x + dx[i];
            int32_t ny = current->y + dy[i];
            
            if (nx >= 0 && nx < (int32_t)grid->width &&
                ny >= 0 && ny < (int32_t)grid->height &&
                !grid->cells[ny][nx].occupied &&
                !grid->cells[ny][nx].visited) {
                
                float move_cost = (i < 4) ? 1.0f : 1.414f;  // Diagonal cost
                float tentative_cost = current->cost + move_cost;
                
                if (tentative_cost < grid->cells[ny][nx].cost ||
                    grid->cells[ny][nx].cost == 0.0f) {
                    
                    grid->cells[ny][nx].parent_x = current->x;
                    grid->cells[ny][nx].parent_y = current->y;
                    grid->cells[ny][nx].cost = tentative_cost;
                    grid->cells[ny][nx].heuristic = heuristic_manhattan(nx, ny,
                                                                        goal_x, goal_y);
                    grid->cells[ny][nx].total_cost = tentative_cost +
                                                     grid->cells[ny][nx].heuristic;
                    
                    // Add to open set if not already there
                    bool in_open = false;
                    for (uint32_t j = 0; j < open_count; j++) {
                        if (open_set[j] == &grid->cells[ny][nx]) {
                            in_open = true;
                            break;
                        }
                    }
                    
                    if (!in_open && open_count < MAX_PATH_NODES) {
                        open_set[open_count++] = &grid->cells[ny][nx];
                    }
                }
            }
        }
        
        yield();
    }
    
    Serial.println("[Robotics] No path found");
    return false;
}

// =====================================================================================================================
// Robotics Initialization
// =====================================================================================================================

void robotics_init() {
    Serial.println("[Robotics] Initializing robotics systems...");
    
    // Initialize robot arm
    g_robot_arm.num_joints = 6;
    for (uint32_t i = 0; i < g_robot_arm.num_joints; i++) {
        g_robot_arm.joints[i].type = JOINT_REVOLUTE;
        g_robot_arm.joints[i].position = 0.0f;
        g_robot_arm.joints[i].min_limit = -PI;
        g_robot_arm.joints[i].max_limit = PI;
        
        // Initialize PID controller for each joint
        pid_init(&g_pid_controllers[i], 1.0f, 0.1f, 0.05f);
    }
    
    // Initialize mobile robot
    g_mobile_robot.type = ROBOT_DIFFERENTIAL_DRIVE;
    g_mobile_robot.wheel_radius = 0.05f;
    g_mobile_robot.wheel_base = 0.3f;
    g_mobile_robot.max_velocity = 1.0f;
    
    // Initialize occupancy grid
    Vector3 origin = {0.0f, 0.0f, 0.0f};
    occupancy_grid_init(&g_occupancy_grid, 0.1f, origin);
    
    Serial.println("[Robotics] Robotics systems initialized");
}

// =====================================================================================================================
// End of robotics_control.cpp
// Lines: ~1200
// =====================================================================================================================
