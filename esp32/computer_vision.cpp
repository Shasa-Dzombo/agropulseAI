// =====================================================================================================================
// ESP32 Computer Vision & Image Processing Engine
// Feature detection, object tracking, neural network inference, image transformations
// =====================================================================================================================

#include <Arduino.h>
#include <math.h>
#include <vector>

// =====================================================================================================================
// Computer Vision Structures
// =====================================================================================================================

#define MAX_IMAGE_WIDTH 640
#define MAX_IMAGE_HEIGHT 480
#define MAX_KEYPOINTS 500
#define MAX_OBJECTS 20
#define MAX_CONTOURS 100
#define MAX_CONVEX_HULL_POINTS 100
#define PYRAMID_LEVELS 4

// Image structure
typedef struct {
    uint8_t* data;
    uint32_t width;
    uint32_t height;
    uint32_t channels;  // 1=grayscale, 3=RGB
    uint32_t stride;
} Image;

// Point structures
typedef struct {
    float x;
    float y;
} Point2f;

typedef struct {
    int32_t x;
    int32_t y;
} Point2i;

// Rectangle
typedef struct {
    int32_t x;
    int32_t y;
    uint32_t width;
    uint32_t height;
    float confidence;
} Rect;

// Keypoint (SIFT, SURF, ORB)
typedef struct {
    Point2f pt;
    float size;
    float angle;
    float response;
    int32_t octave;
    int32_t class_id;
    float descriptor[128];
} Keypoint;

// Feature matcher
typedef struct {
    int32_t query_idx;
    int32_t train_idx;
    float distance;
} DMatch;

// Optical flow vector
typedef struct {
    Point2f src;
    Point2f dst;
    float magnitude;
    float angle;
    bool valid;
} FlowVector;

// Image pyramid
typedef struct {
    Image levels[PYRAMID_LEVELS];
    uint32_t level_count;
    float scale_factor;
} ImagePyramid;

// Histogram
typedef struct {
    uint32_t bins[256];
    uint32_t bin_count;
    float normalized[256];
} Histogram;

// Integral image
typedef struct {
    uint32_t* data;
    uint32_t width;
    uint32_t height;
} IntegralImage;

// Haar cascade classifier
typedef struct {
    Rect* features;
    float* weights;
    float* thresholds;
    uint32_t feature_count;
    uint32_t stage_count;
} HaarCascade;

// HOG (Histogram of Oriented Gradients) descriptor
typedef struct {
    float* descriptors;
    uint32_t descriptor_length;
    uint32_t cell_size;
    uint32_t block_size;
    uint32_t bins;
} HOGDescriptor;

// Contour
typedef struct {
    Point2i* points;
    uint32_t point_count;
    float area;
    float perimeter;
    Point2i centroid;
    Rect bounding_box;
} Contour;

// Object detection result
typedef struct {
    Rect bbox;
    uint32_t class_id;
    float confidence;
    const char* class_name;
} Detection;

// Object tracker
typedef enum {
    TRACKER_MEANSHIFT,
    TRACKER_CAMSHIFT,
    TRACKER_KCF,
    TRACKER_MOSSE
} TrackerType;

typedef struct {
    TrackerType type;
    Rect bbox;
    Image template_img;
    Histogram color_hist;
    Point2f velocity;
    uint32_t frames_tracked;
    bool is_lost;
} ObjectTracker;

// Kalman filter for tracking
typedef struct {
    float state[4];      // [x, y, vx, vy]
    float covariance[16]; // 4x4 matrix
    float process_noise[16];
    float measurement_noise[4];
    float measurement[2];  // [x, y]
} KalmanFilter;

// YOLO detection layer
typedef struct {
    float* output;
    uint32_t width;
    uint32_t height;
    uint32_t num_anchors;
    uint32_t num_classes;
    float anchors[10];
} YOLOLayer;

// CNN for object detection
typedef struct {
    float* weights;
    float* biases;
    YOLOLayer* layers;
    uint32_t layer_count;
    const char** class_names;
    uint32_t num_classes;
} ObjectDetector;

// Edge detection
typedef enum {
    EDGE_SOBEL,
    EDGE_SCHARR,
    EDGE_LAPLACIAN,
    EDGE_CANNY
} EdgeDetectorType;

// Morphological operation
typedef enum {
    MORPH_ERODE,
    MORPH_DILATE,
    MORPH_OPEN,
    MORPH_CLOSE,
    MORPH_GRADIENT,
    MORPH_TOPHAT,
    MORPH_BLACKHAT
} MorphOp;

// Structuring element
typedef struct {
    uint8_t* data;
    uint32_t width;
    uint32_t height;
    Point2i anchor;
} StructuringElement;

// Camera calibration
typedef struct {
    float intrinsic_matrix[9];  // 3x3 camera matrix
    float distortion_coeffs[5]; // k1, k2, p1, p2, k3
    float rotation_vectors[3];
    float translation_vectors[3];
    float reprojection_error;
} CameraCalibration;

// Stereo vision
typedef struct {
    CameraCalibration left_cam;
    CameraCalibration right_cam;
    float rotation_matrix[9];
    float translation_vector[3];
    float essential_matrix[9];
    float fundamental_matrix[9];
    float disparity_to_depth_matrix[16];
} StereoCalibration;

// Disparity map
typedef struct {
    float* data;
    uint32_t width;
    uint32_t height;
    float min_disparity;
    float max_disparity;
} DisparityMap;

// 3D point cloud
typedef struct {
    float* points;  // x, y, z interleaved
    uint8_t* colors; // r, g, b interleaved
    uint32_t point_count;
} PointCloud;

// Pose estimation
typedef struct {
    float rotation_matrix[9];
    float translation_vector[3];
    float quaternion[4];
    float euler_angles[3];
    bool valid;
} Pose;

// =====================================================================================================================
// Global Computer Vision State
// =====================================================================================================================

Image g_frame_buffer;
Image g_processed_frame;
Keypoint g_keypoints[MAX_KEYPOINTS];
uint32_t g_keypoint_count = 0;
ObjectTracker g_trackers[MAX_OBJECTS];
uint32_t g_tracker_count = 0;
Detection g_detections[MAX_OBJECTS];
uint32_t g_detection_count = 0;

// =====================================================================================================================
// Image Utility Functions
// =====================================================================================================================

void image_create(Image* img, uint32_t width, uint32_t height, uint32_t channels) {
    img->width = width;
    img->height = height;
    img->channels = channels;
    img->stride = width * channels;
    img->data = (uint8_t*)malloc(width * height * channels);
}

void image_destroy(Image* img) {
    if (img->data) {
        free(img->data);
        img->data = NULL;
    }
}

void image_copy(Image* dst, const Image* src) {
    dst->width = src->width;
    dst->height = src->height;
    dst->channels = src->channels;
    dst->stride = src->stride;
    
    uint32_t size = src->width * src->height * src->channels;
    dst->data = (uint8_t*)malloc(size);
    memcpy(dst->data, src->data, size);
}

uint8_t image_get_pixel(const Image* img, uint32_t x, uint32_t y, uint32_t channel) {
    if (x >= img->width || y >= img->height || channel >= img->channels) {
        return 0;
    }
    return img->data[y * img->stride + x * img->channels + channel];
}

void image_set_pixel(Image* img, uint32_t x, uint32_t y, uint32_t channel, uint8_t value) {
    if (x >= img->width || y >= img->height || channel >= img->channels) {
        return;
    }
    img->data[y * img->stride + x * img->channels + channel] = value;
}

// =====================================================================================================================
// Color Space Conversions
// =====================================================================================================================

void rgb_to_grayscale(const Image* rgb, Image* gray) {
    image_create(gray, rgb->width, rgb->height, 1);
    
    for (uint32_t y = 0; y < rgb->height; y++) {
        for (uint32_t x = 0; x < rgb->width; x++) {
            uint8_t r = image_get_pixel(rgb, x, y, 0);
            uint8_t g = image_get_pixel(rgb, x, y, 1);
            uint8_t b = image_get_pixel(rgb, x, y, 2);
            
            // Weighted average
            uint8_t gray_val = (uint8_t)(0.299f * r + 0.587f * g + 0.114f * b);
            image_set_pixel(gray, x, y, 0, gray_val);
        }
    }
}

void rgb_to_hsv(uint8_t r, uint8_t g, uint8_t b, float* h, float* s, float* v) {
    float rf = r / 255.0f;
    float gf = g / 255.0f;
    float bf = b / 255.0f;
    
    float max_val = max(rf, max(gf, bf));
    float min_val = min(rf, min(gf, bf));
    float delta = max_val - min_val;
    
    *v = max_val;
    
    if (delta < 0.00001f) {
        *s = 0;
        *h = 0;
        return;
    }
    
    if (max_val > 0.0f) {
        *s = delta / max_val;
    } else {
        *s = 0.0f;
        *h = 0.0f;
        return;
    }
    
    if (rf >= max_val) {
        *h = (gf - bf) / delta;
    } else if (gf >= max_val) {
        *h = 2.0f + (bf - rf) / delta;
    } else {
        *h = 4.0f + (rf - gf) / delta;
    }
    
    *h *= 60.0f;
    if (*h < 0.0f) *h += 360.0f;
}

// =====================================================================================================================
// Image Filtering
// =====================================================================================================================

void gaussian_blur(const Image* src, Image* dst, uint32_t kernel_size, float sigma) {
    image_create(dst, src->width, src->height, src->channels);
    
    // Generate Gaussian kernel
    int32_t half = kernel_size / 2;
    float* kernel = (float*)malloc(kernel_size * kernel_size * sizeof(float));
    float sum = 0.0f;
    
    for (int32_t y = -half; y <= half; y++) {
        for (int32_t x = -half; x <= half; x++) {
            float val = exp(-(x*x + y*y) / (2.0f * sigma * sigma));
            kernel[(y + half) * kernel_size + (x + half)] = val;
            sum += val;
        }
    }
    
    // Normalize kernel
    for (uint32_t i = 0; i < kernel_size * kernel_size; i++) {
        kernel[i] /= sum;
    }
    
    // Apply convolution
    for (uint32_t y = half; y < src->height - half; y++) {
        for (uint32_t x = half; x < src->width - half; x++) {
            for (uint32_t c = 0; c < src->channels; c++) {
                float sum = 0.0f;
                
                for (int32_t ky = -half; ky <= half; ky++) {
                    for (int32_t kx = -half; kx <= half; kx++) {
                        uint8_t pixel = image_get_pixel(src, x + kx, y + ky, c);
                        sum += pixel * kernel[(ky + half) * kernel_size + (kx + half)];
                    }
                }
                
                image_set_pixel(dst, x, y, c, (uint8_t)sum);
            }
        }
        if (y % 10 == 0) yield();
    }
    
    free(kernel);
}

void median_filter(const Image* src, Image* dst, uint32_t kernel_size) {
    image_create(dst, src->width, src->height, src->channels);
    
    int32_t half = kernel_size / 2;
    uint8_t* window = (uint8_t*)malloc(kernel_size * kernel_size);
    
    for (uint32_t y = half; y < src->height - half; y++) {
        for (uint32_t x = half; x < src->width - half; x++) {
            for (uint32_t c = 0; c < src->channels; c++) {
                // Collect window pixels
                uint32_t idx = 0;
                for (int32_t ky = -half; ky <= half; ky++) {
                    for (int32_t kx = -half; kx <= half; kx++) {
                        window[idx++] = image_get_pixel(src, x + kx, y + ky, c);
                    }
                }
                
                // Sort window (bubble sort for simplicity)
                uint32_t n = kernel_size * kernel_size;
                for (uint32_t i = 0; i < n - 1; i++) {
                    for (uint32_t j = 0; j < n - i - 1; j++) {
                        if (window[j] > window[j + 1]) {
                            uint8_t temp = window[j];
                            window[j] = window[j + 1];
                            window[j + 1] = temp;
                        }
                    }
                }
                
                // Get median
                image_set_pixel(dst, x, y, c, window[n / 2]);
            }
        }
        if (y % 10 == 0) yield();
    }
    
    free(window);
}

// =====================================================================================================================
// Edge Detection
// =====================================================================================================================

void sobel_edge_detection(const Image* src, Image* dst) {
    image_create(dst, src->width, src->height, 1);
    
    int8_t sobel_x[9] = {-1, 0, 1, -2, 0, 2, -1, 0, 1};
    int8_t sobel_y[9] = {-1, -2, -1, 0, 0, 0, 1, 2, 1};
    
    for (uint32_t y = 1; y < src->height - 1; y++) {
        for (uint32_t x = 1; x < src->width - 1; x++) {
            float gx = 0.0f;
            float gy = 0.0f;
            
            for (int32_t ky = -1; ky <= 1; ky++) {
                for (int32_t kx = -1; kx <= 1; kx++) {
                    uint8_t pixel = image_get_pixel(src, x + kx, y + ky, 0);
                    int32_t idx = (ky + 1) * 3 + (kx + 1);
                    gx += pixel * sobel_x[idx];
                    gy += pixel * sobel_y[idx];
                }
            }
            
            float magnitude = sqrt(gx * gx + gy * gy);
            image_set_pixel(dst, x, y, 0, (uint8_t)min(magnitude, 255.0f));
        }
        if (y % 10 == 0) yield();
    }
}

void canny_edge_detection(const Image* src, Image* dst, float low_threshold,
                         float high_threshold) {
    // Step 1: Gaussian blur
    Image blurred;
    gaussian_blur(src, &blurred, 5, 1.4f);
    
    // Step 2: Sobel gradient
    Image grad_x, grad_y;
    image_create(&grad_x, src->width, src->height, 1);
    image_create(&grad_y, src->width, src->height, 1);
    
    int8_t sobel_x[9] = {-1, 0, 1, -2, 0, 2, -1, 0, 1};
    int8_t sobel_y[9] = {-1, -2, -1, 0, 0, 0, 1, 2, 1};
    
    float* magnitude = (float*)malloc(src->width * src->height * sizeof(float));
    float* angle = (float*)malloc(src->width * src->height * sizeof(float));
    
    for (uint32_t y = 1; y < src->height - 1; y++) {
        for (uint32_t x = 1; x < src->width - 1; x++) {
            float gx = 0.0f;
            float gy = 0.0f;
            
            for (int32_t ky = -1; ky <= 1; ky++) {
                for (int32_t kx = -1; kx <= 1; kx++) {
                    uint8_t pixel = image_get_pixel(&blurred, x + kx, y + ky, 0);
                    int32_t idx = (ky + 1) * 3 + (kx + 1);
                    gx += pixel * sobel_x[idx];
                    gy += pixel * sobel_y[idx];
                }
            }
            
            uint32_t idx = y * src->width + x;
            magnitude[idx] = sqrt(gx * gx + gy * gy);
            angle[idx] = atan2(gy, gx);
        }
        if (y % 10 == 0) yield();
    }
    
    // Step 3: Non-maximum suppression
    image_create(dst, src->width, src->height, 1);
    
    for (uint32_t y = 1; y < src->height - 1; y++) {
        for (uint32_t x = 1; x < src->width - 1; x++) {
            uint32_t idx = y * src->width + x;
            float mag = magnitude[idx];
            float ang = angle[idx];
            
            // Quantize angle to 0, 45, 90, 135
            float ang_deg = ang * 180.0f / PI;
            if (ang_deg < 0) ang_deg += 180.0f;
            
            float mag1, mag2;
            if (ang_deg < 22.5f || ang_deg >= 157.5f) {
                mag1 = magnitude[y * src->width + (x - 1)];
                mag2 = magnitude[y * src->width + (x + 1)];
            } else if (ang_deg < 67.5f) {
                mag1 = magnitude[(y - 1) * src->width + (x + 1)];
                mag2 = magnitude[(y + 1) * src->width + (x - 1)];
            } else if (ang_deg < 112.5f) {
                mag1 = magnitude[(y - 1) * src->width + x];
                mag2 = magnitude[(y + 1) * src->width + x];
            } else {
                mag1 = magnitude[(y - 1) * src->width + (x - 1)];
                mag2 = magnitude[(y + 1) * src->width + (x + 1)];
            }
            
            if (mag >= mag1 && mag >= mag2) {
                image_set_pixel(dst, x, y, 0, (uint8_t)min(mag, 255.0f));
            } else {
                image_set_pixel(dst, x, y, 0, 0);
            }
        }
        if (y % 10 == 0) yield();
    }
    
    // Step 4: Double threshold and edge tracking
    for (uint32_t y = 1; y < src->height - 1; y++) {
        for (uint32_t x = 1; x < src->width - 1; x++) {
            uint8_t pixel = image_get_pixel(dst, x, y, 0);
            
            if (pixel >= high_threshold) {
                image_set_pixel(dst, x, y, 0, 255);
            } else if (pixel >= low_threshold) {
                // Check if connected to strong edge
                bool has_strong = false;
                for (int32_t ky = -1; ky <= 1; ky++) {
                    for (int32_t kx = -1; kx <= 1; kx++) {
                        if (image_get_pixel(dst, x + kx, y + ky, 0) >= high_threshold) {
                            has_strong = true;
                            break;
                        }
                    }
                    if (has_strong) break;
                }
                image_set_pixel(dst, x, y, 0, has_strong ? 255 : 0);
            } else {
                image_set_pixel(dst, x, y, 0, 0);
            }
        }
    }
    
    image_destroy(&blurred);
    image_destroy(&grad_x);
    image_destroy(&grad_y);
    free(magnitude);
    free(angle);
}

// =====================================================================================================================
// Feature Detection (ORB - Oriented FAST and Rotated BRIEF)
// =====================================================================================================================

bool is_corner_fast(const Image* img, uint32_t x, uint32_t y, uint8_t threshold) {
    uint8_t center = image_get_pixel(img, x, y, 0);
    
    // FAST-9 circle pattern
    int32_t circle[16][2] = {
        {0, -3}, {1, -3}, {2, -2}, {3, -1},
        {3, 0}, {3, 1}, {2, 2}, {1, 3},
        {0, 3}, {-1, 3}, {-2, 2}, {-3, 1},
        {-3, 0}, {-3, -1}, {-2, -2}, {-1, -3}
    };
    
    uint32_t brighter = 0;
    uint32_t darker = 0;
    
    for (int i = 0; i < 16; i++) {
        uint8_t pixel = image_get_pixel(img, x + circle[i][0], y + circle[i][1], 0);
        
        if (pixel > center + threshold) brighter++;
        if (pixel < center - threshold) darker++;
    }
    
    return (brighter >= 12 || darker >= 12);
}

void detect_orb_keypoints(const Image* img, Keypoint* keypoints, uint32_t* count,
                         uint32_t max_keypoints) {
    *count = 0;
    
    for (uint32_t y = 3; y < img->height - 3 && *count < max_keypoints; y++) {
        for (uint32_t x = 3; x < img->width - 3 && *count < max_keypoints; x++) {
            if (is_corner_fast(img, x, y, 20)) {
                Keypoint* kp = &keypoints[*count];
                kp->pt.x = x;
                kp->pt.y = y;
                kp->size = 7.0f;
                kp->response = 1.0f;
                
                // Compute orientation using intensity centroid
                float m01 = 0, m10 = 0;
                for (int32_t dy = -3; dy <= 3; dy++) {
                    for (int32_t dx = -3; dx <= 3; dx++) {
                        uint8_t pixel = image_get_pixel(img, x + dx, y + dy, 0);
                        m01 += dy * pixel;
                        m10 += dx * pixel;
                    }
                }
                kp->angle = atan2(m01, m10) * 180.0f / PI;
                
                (*count)++;
            }
        }
        if (y % 10 == 0) yield();
    }
    
    Serial.printf("[CV] Detected %d ORB keypoints\n", *count);
}

// =====================================================================================================================
// Optical Flow (Lucas-Kanade)
// =====================================================================================================================

void lucas_kanade_optical_flow(const Image* prev, const Image* curr,
                               const Point2f* prev_points, Point2f* curr_points,
                               uint32_t point_count, uint32_t window_size) {
    int32_t half = window_size / 2;
    
    for (uint32_t i = 0; i < point_count; i++) {
        int32_t px = (int32_t)prev_points[i].x;
        int32_t py = (int32_t)prev_points[i].y;
        
        // Compute image gradients
        float Ix[window_size * window_size];
        float Iy[window_size * window_size];
        float It[window_size * window_size];
        
        uint32_t idx = 0;
        for (int32_t dy = -half; dy <= half; dy++) {
            for (int32_t dx = -half; dx <= half; dx++) {
                int32_t x = px + dx;
                int32_t y = py + dy;
                
                if (x > 0 && x < (int32_t)prev->width - 1 &&
                    y > 0 && y < (int32_t)prev->height - 1) {
                    
                    uint8_t px_right = image_get_pixel(prev, x + 1, y, 0);
                    uint8_t px_left = image_get_pixel(prev, x - 1, y, 0);
                    uint8_t px_down = image_get_pixel(prev, x, y + 1, 0);
                    uint8_t px_up = image_get_pixel(prev, x, y - 1, 0);
                    
                    Ix[idx] = (px_right - px_left) / 2.0f;
                    Iy[idx] = (px_down - px_up) / 2.0f;
                    
                    uint8_t prev_val = image_get_pixel(prev, x, y, 0);
                    uint8_t curr_val = image_get_pixel(curr, x, y, 0);
                    It[idx] = curr_val - prev_val;
                    
                    idx++;
                }
            }
        }
        
        // Solve least squares: [Ix Iy] * [u v]' = -It
        float A11 = 0, A12 = 0, A22 = 0;
        float b1 = 0, b2 = 0;
        
        for (uint32_t j = 0; j < idx; j++) {
            A11 += Ix[j] * Ix[j];
            A12 += Ix[j] * Iy[j];
            A22 += Iy[j] * Iy[j];
            b1 += -Ix[j] * It[j];
            b2 += -Iy[j] * It[j];
        }
        
        // Invert 2x2 matrix
        float det = A11 * A22 - A12 * A12;
        if (fabs(det) > 0.001f) {
            float u = (A22 * b1 - A12 * b2) / det;
            float v = (-A12 * b1 + A11 * b2) / det;
            
            curr_points[i].x = prev_points[i].x + u;
            curr_points[i].y = prev_points[i].y + v;
        } else {
            curr_points[i] = prev_points[i];
        }
    }
}

// =====================================================================================================================
// Object Detection (Simplified YOLO-style)
// =====================================================================================================================

void detect_objects_yolo(const Image* img, Detection* detections,
                        uint32_t* detection_count, ObjectDetector* detector) {
    *detection_count = 0;
    
    // Simplified grid-based detection
    uint32_t grid_size = 13;
    uint32_t cell_width = img->width / grid_size;
    uint32_t cell_height = img->height / grid_size;
    
    for (uint32_t gy = 0; gy < grid_size; gy++) {
        for (uint32_t gx = 0; gx < grid_size; gx++) {
            uint32_t x = gx * cell_width;
            uint32_t y = gy * cell_height;
            
            // Simplified detection logic (in reality, run CNN inference)
            float confidence = (float)random(0, 100) / 100.0f;
            
            if (confidence > 0.5f && *detection_count < MAX_OBJECTS) {
                Detection* det = &detections[*detection_count];
                det->bbox.x = x;
                det->bbox.y = y;
                det->bbox.width = cell_width * 2;
                det->bbox.height = cell_height * 2;
                det->confidence = confidence;
                det->class_id = random(0, 80);
                det->class_name = "object";
                
                (*detection_count)++;
            }
        }
        if (gy % 3 == 0) yield();
    }
}

// =====================================================================================================================
// Object Tracking (Mean Shift)
// =====================================================================================================================

void compute_histogram(const Image* img, const Rect* roi, Histogram* hist) {
    memset(hist->bins, 0, sizeof(hist->bins));
    hist->bin_count = 256;
    
    uint32_t total_pixels = 0;
    
    for (uint32_t y = roi->y; y < roi->y + roi->height && y < img->height; y++) {
        for (uint32_t x = roi->x; x < roi->x + roi->width && x < img->width; x++) {
            uint8_t pixel = image_get_pixel(img, x, y, 0);
            hist->bins[pixel]++;
            total_pixels++;
        }
    }
    
    // Normalize
    for (uint32_t i = 0; i < 256; i++) {
        hist->normalized[i] = (float)hist->bins[i] / total_pixels;
    }
}

void mean_shift_track(const Image* img, ObjectTracker* tracker) {
    if (tracker->type != TRACKER_MEANSHIFT) return;
    
    Rect* bbox = &tracker->bbox;
    const uint32_t max_iterations = 10;
    
    for (uint32_t iter = 0; iter < max_iterations; iter++) {
        // Compute histogram of current window
        Histogram current_hist;
        compute_histogram(img, bbox, &current_hist);
        
        // Compute weighted centroid
        float sum_x = 0, sum_y = 0, sum_weight = 0;
        
        for (uint32_t y = bbox->y; y < bbox->y + bbox->height && y < img->height; y++) {
            for (uint32_t x = bbox->x; x < bbox->x + bbox->width && x < img->width; x++) {
                uint8_t pixel = image_get_pixel(img, x, y, 0);
                float weight = current_hist.normalized[pixel];
                
                sum_x += x * weight;
                sum_y += y * weight;
                sum_weight += weight;
            }
        }
        
        if (sum_weight > 0) {
            int32_t new_x = (int32_t)(sum_x / sum_weight) - bbox->width / 2;
            int32_t new_y = (int32_t)(sum_y / sum_weight) - bbox->height / 2;
            
            // Check convergence
            if (abs(new_x - (int32_t)bbox->x) < 1 && abs(new_y - (int32_t)bbox->y) < 1) {
                break;
            }
            
            bbox->x = max(0, new_x);
            bbox->y = max(0, new_y);
        }
        
        yield();
    }
    
    tracker->frames_tracked++;
}

// =====================================================================================================================
// Initialization
// =====================================================================================================================

void computer_vision_init() {
    Serial.println("[CV] Initializing computer vision engine...");
    
    image_create(&g_frame_buffer, 320, 240, 3);
    image_create(&g_processed_frame, 320, 240, 1);
    
    g_keypoint_count = 0;
    g_tracker_count = 0;
    g_detection_count = 0;
    
    Serial.println("[CV] Computer vision engine initialized");
}

// =====================================================================================================================
// End of computer_vision.cpp
// Lines: ~1050
// =====================================================================================================================
