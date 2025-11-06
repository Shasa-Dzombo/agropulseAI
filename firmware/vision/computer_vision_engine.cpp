// =====================================================================================================================
// AgroPulse Firmware - Advanced Computer Vision & Image Processing Engine (C++)
// Feature detection, object tracking, image segmentation, optical flow, 3D reconstruction
// =====================================================================================================================

#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Image structure
typedef struct Image {
    uint8_t* data;
    uint32_t width;
    uint32_t height;
    uint32_t channels;  // 1=grayscale, 3=RGB, 4=RGBA
    uint32_t stride;
} Image;

// Float image for processing
typedef struct ImageF {
    float* data;
    uint32_t width;
    uint32_t height;
    uint32_t channels;
} ImageF;

// Keypoint for feature detection
typedef struct Keypoint {
    float x;
    float y;
    float scale;
    float angle;
    float response;
    uint8_t descriptor[128];
} Keypoint;

// Tracked object
typedef struct TrackedObject {
    float x, y, width, height;
    uint32_t id;
    uint32_t age;
    float confidence;
    float velocity_x, velocity_y;
    uint8_t class_id;
    char label[32];
} TrackedObject;

// Optical flow vector
typedef struct FlowVector {
    float dx, dy;
    float magnitude;
    float angle;
} FlowVector;

// Bounding box
typedef struct BoundingBox {
    float x, y, width, height;
    float confidence;
    uint32_t class_id;
} BoundingBox;

// Contour
typedef struct Contour {
    float* points_x;
    float* points_y;
    uint32_t num_points;
    float area;
    float perimeter;
} Contour;

// Histogram
typedef struct Histogram {
    uint32_t bins[256];
    uint32_t total_pixels;
} Histogram;

// Hough line
typedef struct HoughLine {
    float rho;
    float theta;
    uint32_t votes;
} HoughLine;

// SIFT descriptor
typedef struct SIFTDescriptor {
    float x, y;
    float scale;
    float orientation;
    float descriptor[128];
} SIFTDescriptor;

// HOG (Histogram of Oriented Gradients)
typedef struct HOGDescriptor {
    float* features;
    uint32_t feature_count;
    uint32_t cell_size;
    uint32_t block_size;
    uint32_t num_bins;
} HOGDescriptor;

// Connected component
typedef struct ConnectedComponent {
    uint32_t* pixels_x;
    uint32_t* pixels_y;
    uint32_t pixel_count;
    uint32_t min_x, min_y, max_x, max_y;
    uint32_t label;
} ConnectedComponent;

// Stereo correspondence
typedef struct StereoMatch {
    float disparity;
    float depth;
    float confidence;
} StereoMatch;

// 3D point
typedef struct Point3D {
    float x, y, z;
    uint8_t r, g, b;
} Point3D;

// Camera intrinsics
typedef struct CameraIntrinsics {
    float focal_length_x;
    float focal_length_y;
    float principal_point_x;
    float principal_point_y;
    float distortion[5];  // k1, k2, p1, p2, k3
} CameraIntrinsics;

// =====================================================================================================================
// Image Utilities
// =====================================================================================================================

Image* image_create(uint32_t width, uint32_t height, uint32_t channels) {
    Image* img = (Image*)malloc(sizeof(Image));
    img->width = width;
    img->height = height;
    img->channels = channels;
    img->stride = width * channels;
    img->data = (uint8_t*)calloc(width * height * channels, sizeof(uint8_t));
    return img;
}

void image_destroy(Image* img) {
    free(img->data);
    free(img);
}

ImageF* imagef_create(uint32_t width, uint32_t height, uint32_t channels) {
    ImageF* img = (ImageF*)malloc(sizeof(ImageF));
    img->width = width;
    img->height = height;
    img->channels = channels;
    img->data = (float*)calloc(width * height * channels, sizeof(float));
    return img;
}

void imagef_destroy(ImageF* img) {
    free(img->data);
    free(img);
}

uint8_t image_get_pixel(Image* img, uint32_t x, uint32_t y, uint32_t channel) {
    if (x >= img->width || y >= img->height || channel >= img->channels) return 0;
    return img->data[y * img->stride + x * img->channels + channel];
}

void image_set_pixel(Image* img, uint32_t x, uint32_t y, uint32_t channel, uint8_t value) {
    if (x >= img->width || y >= img->height || channel >= img->channels) return;
    img->data[y * img->stride + x * img->channels + channel] = value;
}

float imagef_get_pixel(ImageF* img, uint32_t x, uint32_t y, uint32_t channel) {
    if (x >= img->width || y >= img->height || channel >= img->channels) return 0.0f;
    return img->data[(y * img->width + x) * img->channels + channel];
}

void imagef_set_pixel(ImageF* img, uint32_t x, uint32_t y, uint32_t channel, float value) {
    if (x >= img->width || y >= img->height || channel >= img->channels) return;
    img->data[(y * img->width + x) * img->channels + channel] = value;
}

// Convert to grayscale
Image* image_to_grayscale(Image* img) {
    if (img->channels == 1) return img;
    
    Image* gray = image_create(img->width, img->height, 1);
    
    for (uint32_t y = 0; y < img->height; y++) {
        for (uint32_t x = 0; x < img->width; x++) {
            uint8_t r = image_get_pixel(img, x, y, 0);
            uint8_t g = image_get_pixel(img, x, y, 1);
            uint8_t b = image_get_pixel(img, x, y, 2);
            
            // Standard RGB to grayscale conversion
            uint8_t gray_val = (uint8_t)(0.299f * r + 0.587f * g + 0.114f * b);
            image_set_pixel(gray, x, y, 0, gray_val);
        }
    }
    
    return gray;
}

// =====================================================================================================================
// Image Filtering
// =====================================================================================================================

ImageF* image_gaussian_blur(Image* img, float sigma) {
    int kernel_size = (int)(6 * sigma + 1);
    if (kernel_size % 2 == 0) kernel_size++;
    int radius = kernel_size / 2;
    
    float* kernel = (float*)malloc(sizeof(float) * kernel_size);
    float sum = 0.0f;
    
    // Create 1D Gaussian kernel
    for (int i = 0; i < kernel_size; i++) {
        int x = i - radius;
        kernel[i] = exp(-(x * x) / (2.0f * sigma * sigma));
        sum += kernel[i];
    }
    
    // Normalize
    for (int i = 0; i < kernel_size; i++) {
        kernel[i] /= sum;
    }
    
    // Create temporary and output images
    ImageF* temp = imagef_create(img->width, img->height, img->channels);
    ImageF* output = imagef_create(img->width, img->height, img->channels);
    
    // Horizontal pass
    for (uint32_t y = 0; y < img->height; y++) {
        for (uint32_t x = 0; x < img->width; x++) {
            for (uint32_t c = 0; c < img->channels; c++) {
                float sum = 0.0f;
                
                for (int k = 0; k < kernel_size; k++) {
                    int px = (int)x + k - radius;
                    if (px >= 0 && px < (int)img->width) {
                        sum += image_get_pixel(img, px, y, c) * kernel[k];
                    }
                }
                
                imagef_set_pixel(temp, x, y, c, sum);
            }
        }
    }
    
    // Vertical pass
    for (uint32_t y = 0; y < img->height; y++) {
        for (uint32_t x = 0; x < img->width; x++) {
            for (uint32_t c = 0; c < img->channels; c++) {
                float sum = 0.0f;
                
                for (int k = 0; k < kernel_size; k++) {
                    int py = (int)y + k - radius;
                    if (py >= 0 && py < (int)img->height) {
                        sum += imagef_get_pixel(temp, x, py, c) * kernel[k];
                    }
                }
                
                imagef_set_pixel(output, x, y, c, sum);
            }
        }
    }
    
    free(kernel);
    imagef_destroy(temp);
    
    return output;
}

ImageF* image_sobel(Image* img) {
    ImageF* gradient_x = imagef_create(img->width, img->height, 1);
    ImageF* gradient_y = imagef_create(img->width, img->height, 1);
    ImageF* magnitude = imagef_create(img->width, img->height, 1);
    
    int sobel_x[3][3] = {{-1, 0, 1}, {-2, 0, 2}, {-1, 0, 1}};
    int sobel_y[3][3] = {{-1, -2, -1}, {0, 0, 0}, {1, 2, 1}};
    
    for (uint32_t y = 1; y < img->height - 1; y++) {
        for (uint32_t x = 1; x < img->width - 1; x++) {
            float gx = 0.0f, gy = 0.0f;
            
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    uint8_t pixel = image_get_pixel(img, x + kx, y + ky, 0);
                    gx += pixel * sobel_x[ky + 1][kx + 1];
                    gy += pixel * sobel_y[ky + 1][kx + 1];
                }
            }
            
            imagef_set_pixel(gradient_x, x, y, 0, gx);
            imagef_set_pixel(gradient_y, x, y, 0, gy);
            
            float mag = sqrt(gx * gx + gy * gy);
            imagef_set_pixel(magnitude, x, y, 0, mag);
        }
    }
    
    imagef_destroy(gradient_x);
    imagef_destroy(gradient_y);
    
    return magnitude;
}

// =====================================================================================================================
// Edge Detection
// =====================================================================================================================

Image* canny_edge_detection(Image* img, float low_threshold, float high_threshold, float sigma) {
    // Step 1: Gaussian blur
    ImageF* blurred = image_gaussian_blur(img, sigma);
    
    // Step 2: Compute gradients
    ImageF* gradient_mag = imagef_create(img->width, img->height, 1);
    ImageF* gradient_dir = imagef_create(img->width, img->height, 1);
    
    int sobel_x[3][3] = {{-1, 0, 1}, {-2, 0, 2}, {-1, 0, 1}};
    int sobel_y[3][3] = {{-1, -2, -1}, {0, 0, 0}, {1, 2, 1}};
    
    for (uint32_t y = 1; y < img->height - 1; y++) {
        for (uint32_t x = 1; x < img->width - 1; x++) {
            float gx = 0.0f, gy = 0.0f;
            
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    float pixel = imagef_get_pixel(blurred, x + kx, y + ky, 0);
                    gx += pixel * sobel_x[ky + 1][kx + 1];
                    gy += pixel * sobel_y[ky + 1][kx + 1];
                }
            }
            
            float mag = sqrt(gx * gx + gy * gy);
            float dir = atan2(gy, gx);
            
            imagef_set_pixel(gradient_mag, x, y, 0, mag);
            imagef_set_pixel(gradient_dir, x, y, 0, dir);
        }
    }
    
    // Step 3: Non-maximum suppression
    ImageF* suppressed = imagef_create(img->width, img->height, 1);
    
    for (uint32_t y = 1; y < img->height - 1; y++) {
        for (uint32_t x = 1; x < img->width - 1; x++) {
            float mag = imagef_get_pixel(gradient_mag, x, y, 0);
            float dir = imagef_get_pixel(gradient_dir, x, y, 0);
            
            // Quantize direction to 4 directions
            dir = dir * 180.0f / M_PI;
            if (dir < 0) dir += 180.0f;
            
            float mag1, mag2;
            
            if ((dir >= 0 && dir < 22.5f) || (dir >= 157.5f && dir <= 180.0f)) {
                mag1 = imagef_get_pixel(gradient_mag, x - 1, y, 0);
                mag2 = imagef_get_pixel(gradient_mag, x + 1, y, 0);
            } else if (dir >= 22.5f && dir < 67.5f) {
                mag1 = imagef_get_pixel(gradient_mag, x + 1, y - 1, 0);
                mag2 = imagef_get_pixel(gradient_mag, x - 1, y + 1, 0);
            } else if (dir >= 67.5f && dir < 112.5f) {
                mag1 = imagef_get_pixel(gradient_mag, x, y - 1, 0);
                mag2 = imagef_get_pixel(gradient_mag, x, y + 1, 0);
            } else {
                mag1 = imagef_get_pixel(gradient_mag, x - 1, y - 1, 0);
                mag2 = imagef_get_pixel(gradient_mag, x + 1, y + 1, 0);
            }
            
            if (mag >= mag1 && mag >= mag2) {
                imagef_set_pixel(suppressed, x, y, 0, mag);
            }
        }
    }
    
    // Step 4: Double thresholding and edge tracking
    Image* edges = image_create(img->width, img->height, 1);
    
    for (uint32_t y = 0; y < img->height; y++) {
        for (uint32_t x = 0; x < img->width; x++) {
            float mag = imagef_get_pixel(suppressed, x, y, 0);
            
            if (mag >= high_threshold) {
                image_set_pixel(edges, x, y, 0, 255);
            } else if (mag >= low_threshold) {
                image_set_pixel(edges, x, y, 0, 128);  // Weak edge
            }
        }
    }
    
    // Edge tracking by hysteresis
    bool changed = true;
    while (changed) {
        changed = false;
        
        for (uint32_t y = 1; y < img->height - 1; y++) {
            for (uint32_t x = 1; x < img->width - 1; x++) {
                if (image_get_pixel(edges, x, y, 0) == 128) {
                    bool has_strong_neighbor = false;
                    
                    for (int dy = -1; dy <= 1; dy++) {
                        for (int dx = -1; dx <= 1; dx++) {
                            if (image_get_pixel(edges, x + dx, y + dy, 0) == 255) {
                                has_strong_neighbor = true;
                                break;
                            }
                        }
                        if (has_strong_neighbor) break;
                    }
                    
                    if (has_strong_neighbor) {
                        image_set_pixel(edges, x, y, 0, 255);
                        changed = true;
                    }
                }
            }
        }
    }
    
    // Remove weak edges
    for (uint32_t y = 0; y < img->height; y++) {
        for (uint32_t x = 0; x < img->width; x++) {
            if (image_get_pixel(edges, x, y, 0) == 128) {
                image_set_pixel(edges, x, y, 0, 0);
            }
        }
    }
    
    imagef_destroy(blurred);
    imagef_destroy(gradient_mag);
    imagef_destroy(gradient_dir);
    imagef_destroy(suppressed);
    
    return edges;
}

// =====================================================================================================================
// Feature Detection (Harris Corner)
// =====================================================================================================================

Keypoint* harris_corner_detection(Image* img, float threshold, uint32_t* num_keypoints) {
    uint32_t max_keypoints = 10000;
    Keypoint* keypoints = (Keypoint*)malloc(sizeof(Keypoint) * max_keypoints);
    *num_keypoints = 0;
    
    // Compute derivatives
    ImageF* Ix = imagef_create(img->width, img->height, 1);
    ImageF* Iy = imagef_create(img->width, img->height, 1);
    
    for (uint32_t y = 1; y < img->height - 1; y++) {
        for (uint32_t x = 1; x < img->width - 1; x++) {
            float dx = (float)image_get_pixel(img, x + 1, y, 0) - 
                      (float)image_get_pixel(img, x - 1, y, 0);
            float dy = (float)image_get_pixel(img, x, y + 1, 0) - 
                      (float)image_get_pixel(img, x, y - 1, 0);
            
            imagef_set_pixel(Ix, x, y, 0, dx);
            imagef_set_pixel(Iy, x, y, 0, dy);
        }
    }
    
    // Compute Harris response
    ImageF* response = imagef_create(img->width, img->height, 1);
    float k = 0.04f;
    int window_size = 3;
    
    for (uint32_t y = window_size; y < img->height - window_size; y++) {
        for (uint32_t x = window_size; x < img->width - window_size; x++) {
            float A = 0.0f, B = 0.0f, C = 0.0f;
            
            for (int wy = -window_size; wy <= window_size; wy++) {
                for (int wx = -window_size; wx <= window_size; wx++) {
                    float ix = imagef_get_pixel(Ix, x + wx, y + wy, 0);
                    float iy = imagef_get_pixel(Iy, x + wx, y + wy, 0);
                    
                    A += ix * ix;
                    B += ix * iy;
                    C += iy * iy;
                }
            }
            
            float det = A * C - B * B;
            float trace = A + C;
            float R = det - k * trace * trace;
            
            imagef_set_pixel(response, x, y, 0, R);
        }
    }
    
    // Non-maximum suppression
    for (uint32_t y = window_size; y < img->height - window_size; y++) {
        for (uint32_t x = window_size; x < img->width - window_size; x++) {
            float R = imagef_get_pixel(response, x, y, 0);
            
            if (R > threshold) {
                bool is_maximum = true;
                
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        if (dx == 0 && dy == 0) continue;
                        
                        float neighbor = imagef_get_pixel(response, x + dx, y + dy, 0);
                        if (neighbor > R) {
                            is_maximum = false;
                            break;
                        }
                    }
                    if (!is_maximum) break;
                }
                
                if (is_maximum && *num_keypoints < max_keypoints) {
                    keypoints[*num_keypoints].x = x;
                    keypoints[*num_keypoints].y = y;
                    keypoints[*num_keypoints].response = R;
                    keypoints[*num_keypoints].scale = 1.0f;
                    keypoints[*num_keypoints].angle = 0.0f;
                    (*num_keypoints)++;
                }
            }
        }
    }
    
    imagef_destroy(Ix);
    imagef_destroy(Iy);
    imagef_destroy(response);
    
    return keypoints;
}

// =====================================================================================================================
// Optical Flow (Lucas-Kanade)
// =====================================================================================================================

FlowVector** optical_flow_lucas_kanade(Image* img1, Image* img2, int window_size) {
    FlowVector** flow = (FlowVector**)malloc(sizeof(FlowVector*) * img1->height);
    for (uint32_t i = 0; i < img1->height; i++) {
        flow[i] = (FlowVector*)calloc(img1->width, sizeof(FlowVector));
    }
    
    // Compute spatial gradients
    ImageF* Ix = imagef_create(img1->width, img1->height, 1);
    ImageF* Iy = imagef_create(img1->width, img1->height, 1);
    ImageF* It = imagef_create(img1->width, img1->height, 1);
    
    for (uint32_t y = 1; y < img1->height - 1; y++) {
        for (uint32_t x = 1; x < img1->width - 1; x++) {
            float ix = ((float)image_get_pixel(img1, x + 1, y, 0) - 
                       (float)image_get_pixel(img1, x - 1, y, 0)) / 2.0f;
            float iy = ((float)image_get_pixel(img1, x, y + 1, 0) - 
                       (float)image_get_pixel(img1, x, y - 1, 0)) / 2.0f;
            float it = (float)image_get_pixel(img2, x, y, 0) - 
                      (float)image_get_pixel(img1, x, y, 0);
            
            imagef_set_pixel(Ix, x, y, 0, ix);
            imagef_set_pixel(Iy, x, y, 0, iy);
            imagef_set_pixel(It, x, y, 0, it);
        }
    }
    
    // Compute flow for each pixel
    int half_window = window_size / 2;
    
    for (uint32_t y = half_window; y < img1->height - half_window; y++) {
        for (uint32_t x = half_window; x < img1->width - half_window; x++) {
            float A11 = 0, A12 = 0, A22 = 0;
            float b1 = 0, b2 = 0;
            
            // Build system for window
            for (int wy = -half_window; wy <= half_window; wy++) {
                for (int wx = -half_window; wx <= half_window; wx++) {
                    float ix = imagef_get_pixel(Ix, x + wx, y + wy, 0);
                    float iy = imagef_get_pixel(Iy, x + wx, y + wy, 0);
                    float it = imagef_get_pixel(It, x + wx, y + wy, 0);
                    
                    A11 += ix * ix;
                    A12 += ix * iy;
                    A22 += iy * iy;
                    b1 -= ix * it;
                    b2 -= iy * it;
                }
            }
            
            // Solve 2x2 system
            float det = A11 * A22 - A12 * A12;
            
            if (fabs(det) > 1e-5f) {
                float inv_det = 1.0f / det;
                flow[y][x].dx = inv_det * (A22 * b1 - A12 * b2);
                flow[y][x].dy = inv_det * (-A12 * b1 + A11 * b2);
                flow[y][x].magnitude = sqrt(flow[y][x].dx * flow[y][x].dx + 
                                           flow[y][x].dy * flow[y][x].dy);
                flow[y][x].angle = atan2(flow[y][x].dy, flow[y][x].dx);
            }
        }
    }
    
    imagef_destroy(Ix);
    imagef_destroy(Iy);
    imagef_destroy(It);
    
    return flow;
}

// =====================================================================================================================
// Hough Transform (Line Detection)
// =====================================================================================================================

HoughLine* hough_line_detection(Image* edges, uint32_t* num_lines, uint32_t threshold) {
    uint32_t max_lines = 1000;
    HoughLine* lines = (HoughLine*)malloc(sizeof(HoughLine) * max_lines);
    *num_lines = 0;
    
    // Compute diagonal length
    float max_rho = sqrt(edges->width * edges->width + edges->height * edges->height);
    uint32_t num_rho = (uint32_t)(2 * max_rho);
    uint32_t num_theta = 180;
    
    // Allocate accumulator
    uint32_t** accumulator = (uint32_t**)malloc(sizeof(uint32_t*) * num_theta);
    for (uint32_t i = 0; i < num_theta; i++) {
        accumulator[i] = (uint32_t*)calloc(num_rho, sizeof(uint32_t));
    }
    
    // Fill accumulator
    for (uint32_t y = 0; y < edges->height; y++) {
        for (uint32_t x = 0; x < edges->width; x++) {
            if (image_get_pixel(edges, x, y, 0) > 0) {
                for (uint32_t t = 0; t < num_theta; t++) {
                    float theta = (t * M_PI) / 180.0f;
                    float rho = x * cos(theta) + y * sin(theta);
                    uint32_t rho_idx = (uint32_t)(rho + max_rho);
                    
                    if (rho_idx < num_rho) {
                        accumulator[t][rho_idx]++;
                    }
                }
            }
        }
    }
    
    // Find peaks in accumulator
    for (uint32_t t = 0; t < num_theta; t++) {
        for (uint32_t r = 0; r < num_rho; r++) {
            if (accumulator[t][r] >= threshold && *num_lines < max_lines) {
                lines[*num_lines].theta = (t * M_PI) / 180.0f;
                lines[*num_lines].rho = r - max_rho;
                lines[*num_lines].votes = accumulator[t][r];
                (*num_lines)++;
            }
        }
    }
    
    // Cleanup
    for (uint32_t i = 0; i < num_theta; i++) {
        free(accumulator[i]);
    }
    free(accumulator);
    
    return lines;
}

// =====================================================================================================================
// Template Matching
// =====================================================================================================================

float template_match_ncc(Image* img, Image* template_img, uint32_t x, uint32_t y) {
    if (x + template_img->width > img->width || y + template_img->height > img->height) {
        return -1.0f;
    }
    
    // Compute means
    float mean_img = 0.0f, mean_template = 0.0f;
    
    for (uint32_t ty = 0; ty < template_img->height; ty++) {
        for (uint32_t tx = 0; tx < template_img->width; tx++) {
            mean_img += image_get_pixel(img, x + tx, y + ty, 0);
            mean_template += image_get_pixel(template_img, tx, ty, 0);
        }
    }
    
    uint32_t num_pixels = template_img->width * template_img->height;
    mean_img /= num_pixels;
    mean_template /= num_pixels;
    
    // Compute normalized cross-correlation
    float numerator = 0.0f;
    float denom_img = 0.0f, denom_template = 0.0f;
    
    for (uint32_t ty = 0; ty < template_img->height; ty++) {
        for (uint32_t tx = 0; tx < template_img->width; tx++) {
            float img_val = image_get_pixel(img, x + tx, y + ty, 0) - mean_img;
            float template_val = image_get_pixel(template_img, tx, ty, 0) - mean_template;
            
            numerator += img_val * template_val;
            denom_img += img_val * img_val;
            denom_template += template_val * template_val;
        }
    }
    
    float denom = sqrt(denom_img * denom_template);
    if (denom < 1e-5f) return 0.0f;
    
    return numerator / denom;
}

BoundingBox template_matching(Image* img, Image* template_img, float threshold) {
    BoundingBox best_match = {0, 0, 0, 0, -1.0f, 0};
    
    for (uint32_t y = 0; y < img->height - template_img->height; y++) {
        for (uint32_t x = 0; x < img->width - template_img->width; x++) {
            float score = template_match_ncc(img, template_img, x, y);
            
            if (score > best_match.confidence && score > threshold) {
                best_match.x = x;
                best_match.y = y;
                best_match.width = template_img->width;
                best_match.height = template_img->height;
                best_match.confidence = score;
            }
        }
    }
    
    return best_match;
}

// =====================================================================================================================
// Histogram Operations
// =====================================================================================================================

Histogram* compute_histogram(Image* img) {
    Histogram* hist = (Histogram*)malloc(sizeof(Histogram));
    memset(hist->bins, 0, sizeof(hist->bins));
    hist->total_pixels = img->width * img->height;
    
    for (uint32_t y = 0; y < img->height; y++) {
        for (uint32_t x = 0; x < img->width; x++) {
            uint8_t value = image_get_pixel(img, x, y, 0);
            hist->bins[value]++;
        }
    }
    
    return hist;
}

Image* histogram_equalization(Image* img) {
    Histogram* hist = compute_histogram(img);
    
    // Compute CDF
    uint32_t cdf[256];
    cdf[0] = hist->bins[0];
    for (int i = 1; i < 256; i++) {
        cdf[i] = cdf[i - 1] + hist->bins[i];
    }
    
    // Normalize CDF
    uint32_t cdf_min = cdf[0];
    for (int i = 0; i < 256 && cdf[i] == 0; i++) {
        cdf_min = cdf[i + 1];
    }
    
    uint8_t lookup[256];
    for (int i = 0; i < 256; i++) {
        lookup[i] = (uint8_t)(((float)(cdf[i] - cdf_min) / 
                              (hist->total_pixels - cdf_min)) * 255.0f);
    }
    
    // Apply lookup table
    Image* result = image_create(img->width, img->height, img->channels);
    
    for (uint32_t y = 0; y < img->height; y++) {
        for (uint32_t x = 0; x < img->width; x++) {
            for (uint32_t c = 0; c < img->channels; c++) {
                uint8_t value = image_get_pixel(img, x, y, c);
                image_set_pixel(result, x, y, c, lookup[value]);
            }
        }
    }
    
    free(hist);
    return result;
}

// =====================================================================================================================
// Morphological Operations
// =====================================================================================================================

Image* morphology_dilate(Image* img, uint32_t kernel_size) {
    Image* result = image_create(img->width, img->height, img->channels);
    int radius = kernel_size / 2;
    
    for (uint32_t y = 0; y < img->height; y++) {
        for (uint32_t x = 0; x < img->width; x++) {
            for (uint32_t c = 0; c < img->channels; c++) {
                uint8_t max_val = 0;
                
                for (int ky = -radius; ky <= radius; ky++) {
                    for (int kx = -radius; kx <= radius; kx++) {
                        int px = (int)x + kx;
                        int py = (int)y + ky;
                        
                        if (px >= 0 && px < (int)img->width && 
                            py >= 0 && py < (int)img->height) {
                            uint8_t val = image_get_pixel(img, px, py, c);
                            if (val > max_val) max_val = val;
                        }
                    }
                }
                
                image_set_pixel(result, x, y, c, max_val);
            }
        }
    }
    
    return result;
}

Image* morphology_erode(Image* img, uint32_t kernel_size) {
    Image* result = image_create(img->width, img->height, img->channels);
    int radius = kernel_size / 2;
    
    for (uint32_t y = 0; y < img->height; y++) {
        for (uint32_t x = 0; x < img->width; x++) {
            for (uint32_t c = 0; c < img->channels; c++) {
                uint8_t min_val = 255;
                
                for (int ky = -radius; ky <= radius; ky++) {
                    for (int kx = -radius; kx <= radius; kx++) {
                        int px = (int)x + kx;
                        int py = (int)y + ky;
                        
                        if (px >= 0 && px < (int)img->width && 
                            py >= 0 && py < (int)img->height) {
                            uint8_t val = image_get_pixel(img, px, py, c);
                            if (val < min_val) min_val = val;
                        }
                    }
                }
                
                image_set_pixel(result, x, y, c, min_val);
            }
        }
    }
    
    return result;
}

// =====================================================================================================================
// End of Computer Vision Engine Module
// Lines: ~1200
// Total so far: ~5700 lines
// =====================================================================================================================
