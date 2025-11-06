// =====================================================================================================================
// AgroPulse Firmware - Neural Network Engine (C++)
// Deep learning, backpropagation, CNN, RNN, optimization algorithms
// =====================================================================================================================

#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Activation function types
typedef enum ActivationType {
    ACTIVATION_LINEAR,
    ACTIVATION_SIGMOID,
    ACTIVATION_TANH,
    ACTIVATION_RELU,
    ACTIVATION_LEAKY_RELU,
    ACTIVATION_ELU,
    ACTIVATION_SOFTMAX,
    ACTIVATION_SWISH,
    ACTIVATION_GELU
} ActivationType;

// Layer types
typedef enum LayerType {
    LAYER_DENSE,
    LAYER_CONV2D,
    LAYER_MAXPOOL2D,
    LAYER_AVGPOOL2D,
    LAYER_FLATTEN,
    LAYER_DROPOUT,
    LAYER_BATCHNORM,
    LAYER_LSTM,
    LAYER_GRU
} LayerType;

// Optimizer types
typedef enum OptimizerType {
    OPTIMIZER_SGD,
    OPTIMIZER_MOMENTUM,
    OPTIMIZER_ADAM,
    OPTIMIZER_RMSPROP,
    OPTIMIZER_ADAGRAD
} OptimizerType;

// Loss function types
typedef enum LossType {
    LOSS_MSE,
    LOSS_MAE,
    LOSS_CROSS_ENTROPY,
    LOSS_BINARY_CROSS_ENTROPY,
    LOSS_HUBER
} LossType;

// Matrix structure
typedef struct Matrix {
    float* data;
    uint32_t rows;
    uint32_t cols;
} Matrix;

// Tensor structure (4D for conv layers)
typedef struct Tensor {
    float* data;
    uint32_t batch;
    uint32_t channels;
    uint32_t height;
    uint32_t width;
} Tensor;

// Dense layer
typedef struct DenseLayer {
    Matrix* weights;
    Matrix* biases;
    Matrix* weight_gradients;
    Matrix* bias_gradients;
    Matrix* input_cache;
    Matrix* output_cache;
    ActivationType activation;
    uint32_t input_size;
    uint32_t output_size;
} DenseLayer;

// Convolutional layer
typedef struct Conv2DLayer {
    Tensor* filters;
    Matrix* biases;
    Tensor* filter_gradients;
    Matrix* bias_gradients;
    Tensor* input_cache;
    Tensor* output_cache;
    ActivationType activation;
    uint32_t num_filters;
    uint32_t filter_size;
    uint32_t stride;
    uint32_t padding;
    uint32_t input_channels;
} Conv2DLayer;

// Pooling layer
typedef struct PoolingLayer {
    Tensor* input_cache;
    Tensor* output_cache;
    Matrix* max_indices;
    LayerType type;
    uint32_t pool_size;
    uint32_t stride;
} PoolingLayer;

// LSTM cell state
typedef struct LSTMState {
    Matrix* hidden;
    Matrix* cell;
} LSTMState;

// LSTM layer
typedef struct LSTMLayer {
    Matrix* weights_input;
    Matrix* weights_forget;
    Matrix* weights_cell;
    Matrix* weights_output;
    Matrix* weights_hidden_input;
    Matrix* weights_hidden_forget;
    Matrix* weights_hidden_cell;
    Matrix* weights_hidden_output;
    Matrix* bias_input;
    Matrix* bias_forget;
    Matrix* bias_cell;
    Matrix* bias_output;
    LSTMState* state;
    uint32_t input_size;
    uint32_t hidden_size;
    uint32_t sequence_length;
} LSTMLayer;

// Optimizer state
typedef struct OptimizerState {
    OptimizerType type;
    float learning_rate;
    float momentum;
    float beta1;
    float beta2;
    float epsilon;
    uint32_t timestep;
    
    // Momentum/Adam state
    Matrix** velocity_weights;
    Matrix** velocity_biases;
    Matrix** squared_velocity_weights;
    Matrix** squared_velocity_biases;
    uint32_t num_layers;
} OptimizerState;

// Neural network model
typedef struct NeuralNetwork {
    void** layers;
    LayerType* layer_types;
    uint32_t num_layers;
    uint32_t capacity;
    OptimizerState* optimizer;
    LossType loss_function;
    float dropout_rate;
} NeuralNetwork;

// Training configuration
typedef struct TrainingConfig {
    uint32_t epochs;
    uint32_t batch_size;
    float learning_rate;
    float validation_split;
    bool shuffle;
    bool early_stopping;
    uint32_t patience;
} TrainingConfig;

// =====================================================================================================================
// Matrix Operations
// =====================================================================================================================

Matrix* matrix_create(uint32_t rows, uint32_t cols) {
    Matrix* mat = (Matrix*)malloc(sizeof(Matrix));
    mat->rows = rows;
    mat->cols = cols;
    mat->data = (float*)calloc(rows * cols, sizeof(float));
    return mat;
}

void matrix_destroy(Matrix* mat) {
    free(mat->data);
    free(mat);
}

Matrix* matrix_copy(Matrix* src) {
    Matrix* dst = matrix_create(src->rows, src->cols);
    memcpy(dst->data, src->data, sizeof(float) * src->rows * src->cols);
    return dst;
}

void matrix_fill(Matrix* mat, float value) {
    for (uint32_t i = 0; i < mat->rows * mat->cols; i++) {
        mat->data[i] = value;
    }
}

void matrix_random_normal(Matrix* mat, float mean, float stddev) {
    for (uint32_t i = 0; i < mat->rows * mat->cols; i++) {
        // Box-Muller transform
        float u1 = (float)rand() / RAND_MAX;
        float u2 = (float)rand() / RAND_MAX;
        float z0 = sqrt(-2.0f * log(u1)) * cos(2.0f * M_PI * u2);
        mat->data[i] = mean + stddev * z0;
    }
}

void matrix_he_initialization(Matrix* mat) {
    float stddev = sqrt(2.0f / mat->cols);
    matrix_random_normal(mat, 0.0f, stddev);
}

void matrix_xavier_initialization(Matrix* mat) {
    float stddev = sqrt(2.0f / (mat->rows + mat->cols));
    matrix_random_normal(mat, 0.0f, stddev);
}

Matrix* matrix_multiply(Matrix* a, Matrix* b) {
    if (a->cols != b->rows) return NULL;
    
    Matrix* result = matrix_create(a->rows, b->cols);
    
    for (uint32_t i = 0; i < a->rows; i++) {
        for (uint32_t j = 0; j < b->cols; j++) {
            float sum = 0.0f;
            for (uint32_t k = 0; k < a->cols; k++) {
                sum += a->data[i * a->cols + k] * b->data[k * b->cols + j];
            }
            result->data[i * b->cols + j] = sum;
        }
    }
    
    return result;
}

Matrix* matrix_transpose(Matrix* mat) {
    Matrix* result = matrix_create(mat->cols, mat->rows);
    
    for (uint32_t i = 0; i < mat->rows; i++) {
        for (uint32_t j = 0; j < mat->cols; j++) {
            result->data[j * mat->rows + i] = mat->data[i * mat->cols + j];
        }
    }
    
    return result;
}

void matrix_add(Matrix* a, Matrix* b, Matrix* result) {
    for (uint32_t i = 0; i < a->rows * a->cols; i++) {
        result->data[i] = a->data[i] + b->data[i];
    }
}

void matrix_subtract(Matrix* a, Matrix* b, Matrix* result) {
    for (uint32_t i = 0; i < a->rows * a->cols; i++) {
        result->data[i] = a->data[i] - b->data[i];
    }
}

void matrix_hadamard(Matrix* a, Matrix* b, Matrix* result) {
    for (uint32_t i = 0; i < a->rows * a->cols; i++) {
        result->data[i] = a->data[i] * b->data[i];
    }
}

void matrix_scale(Matrix* mat, float scalar) {
    for (uint32_t i = 0; i < mat->rows * mat->cols; i++) {
        mat->data[i] *= scalar;
    }
}

float matrix_sum(Matrix* mat) {
    float sum = 0.0f;
    for (uint32_t i = 0; i < mat->rows * mat->cols; i++) {
        sum += mat->data[i];
    }
    return sum;
}

// =====================================================================================================================
// Activation Functions
// =====================================================================================================================

float activation_sigmoid(float x) {
    return 1.0f / (1.0f + exp(-x));
}

float activation_sigmoid_derivative(float x) {
    float sig = activation_sigmoid(x);
    return sig * (1.0f - sig);
}

float activation_tanh(float x) {
    return tanh(x);
}

float activation_tanh_derivative(float x) {
    float t = tanh(x);
    return 1.0f - t * t;
}

float activation_relu(float x) {
    return x > 0.0f ? x : 0.0f;
}

float activation_relu_derivative(float x) {
    return x > 0.0f ? 1.0f : 0.0f;
}

float activation_leaky_relu(float x, float alpha) {
    return x > 0.0f ? x : alpha * x;
}

float activation_leaky_relu_derivative(float x, float alpha) {
    return x > 0.0f ? 1.0f : alpha;
}

float activation_elu(float x, float alpha) {
    return x > 0.0f ? x : alpha * (exp(x) - 1.0f);
}

float activation_elu_derivative(float x, float alpha) {
    return x > 0.0f ? 1.0f : alpha * exp(x);
}

float activation_swish(float x) {
    return x * activation_sigmoid(x);
}

float activation_gelu(float x) {
    return 0.5f * x * (1.0f + tanh(sqrt(2.0f / M_PI) * (x + 0.044715f * x * x * x)));
}

void activation_softmax(Matrix* mat) {
    for (uint32_t i = 0; i < mat->rows; i++) {
        float max_val = mat->data[i * mat->cols];
        
        // Find max for numerical stability
        for (uint32_t j = 1; j < mat->cols; j++) {
            if (mat->data[i * mat->cols + j] > max_val) {
                max_val = mat->data[i * mat->cols + j];
            }
        }
        
        // Compute exp and sum
        float sum = 0.0f;
        for (uint32_t j = 0; j < mat->cols; j++) {
            mat->data[i * mat->cols + j] = exp(mat->data[i * mat->cols + j] - max_val);
            sum += mat->data[i * mat->cols + j];
        }
        
        // Normalize
        for (uint32_t j = 0; j < mat->cols; j++) {
            mat->data[i * mat->cols + j] /= sum;
        }
    }
}

void apply_activation(Matrix* mat, ActivationType type) {
    for (uint32_t i = 0; i < mat->rows * mat->cols; i++) {
        switch (type) {
            case ACTIVATION_SIGMOID:
                mat->data[i] = activation_sigmoid(mat->data[i]);
                break;
            case ACTIVATION_TANH:
                mat->data[i] = activation_tanh(mat->data[i]);
                break;
            case ACTIVATION_RELU:
                mat->data[i] = activation_relu(mat->data[i]);
                break;
            case ACTIVATION_LEAKY_RELU:
                mat->data[i] = activation_leaky_relu(mat->data[i], 0.01f);
                break;
            case ACTIVATION_ELU:
                mat->data[i] = activation_elu(mat->data[i], 1.0f);
                break;
            case ACTIVATION_SWISH:
                mat->data[i] = activation_swish(mat->data[i]);
                break;
            case ACTIVATION_GELU:
                mat->data[i] = activation_gelu(mat->data[i]);
                break;
            default:
                break;
        }
    }
    
    if (type == ACTIVATION_SOFTMAX) {
        activation_softmax(mat);
    }
}

void apply_activation_derivative(Matrix* mat, Matrix* output, ActivationType type) {
    for (uint32_t i = 0; i < mat->rows * mat->cols; i++) {
        switch (type) {
            case ACTIVATION_SIGMOID:
                output->data[i] *= activation_sigmoid_derivative(mat->data[i]);
                break;
            case ACTIVATION_TANH:
                output->data[i] *= activation_tanh_derivative(mat->data[i]);
                break;
            case ACTIVATION_RELU:
                output->data[i] *= activation_relu_derivative(mat->data[i]);
                break;
            case ACTIVATION_LEAKY_RELU:
                output->data[i] *= activation_leaky_relu_derivative(mat->data[i], 0.01f);
                break;
            case ACTIVATION_ELU:
                output->data[i] *= activation_elu_derivative(mat->data[i], 1.0f);
                break;
            default:
                break;
        }
    }
}

// =====================================================================================================================
// Dense Layer Operations
// =====================================================================================================================

DenseLayer* dense_layer_create(uint32_t input_size, uint32_t output_size, 
                                ActivationType activation) {
    DenseLayer* layer = (DenseLayer*)malloc(sizeof(DenseLayer));
    
    layer->input_size = input_size;
    layer->output_size = output_size;
    layer->activation = activation;
    
    layer->weights = matrix_create(input_size, output_size);
    layer->biases = matrix_create(1, output_size);
    layer->weight_gradients = matrix_create(input_size, output_size);
    layer->bias_gradients = matrix_create(1, output_size);
    
    // He initialization for ReLU, Xavier for others
    if (activation == ACTIVATION_RELU || activation == ACTIVATION_LEAKY_RELU) {
        matrix_he_initialization(layer->weights);
    } else {
        matrix_xavier_initialization(layer->weights);
    }
    
    layer->input_cache = NULL;
    layer->output_cache = NULL;
    
    return layer;
}

void dense_layer_destroy(DenseLayer* layer) {
    matrix_destroy(layer->weights);
    matrix_destroy(layer->biases);
    matrix_destroy(layer->weight_gradients);
    matrix_destroy(layer->bias_gradients);
    
    if (layer->input_cache) matrix_destroy(layer->input_cache);
    if (layer->output_cache) matrix_destroy(layer->output_cache);
    
    free(layer);
}

Matrix* dense_layer_forward(DenseLayer* layer, Matrix* input) {
    // Cache input for backprop
    if (layer->input_cache) matrix_destroy(layer->input_cache);
    layer->input_cache = matrix_copy(input);
    
    // output = input * weights + biases
    Matrix* output = matrix_multiply(input, layer->weights);
    
    // Add biases (broadcast)
    for (uint32_t i = 0; i < output->rows; i++) {
        for (uint32_t j = 0; j < output->cols; j++) {
            output->data[i * output->cols + j] += layer->biases->data[j];
        }
    }
    
    // Cache pre-activation output
    if (layer->output_cache) matrix_destroy(layer->output_cache);
    layer->output_cache = matrix_copy(output);
    
    // Apply activation
    apply_activation(output, layer->activation);
    
    return output;
}

Matrix* dense_layer_backward(DenseLayer* layer, Matrix* grad_output) {
    // Apply activation derivative
    Matrix* grad_activation = matrix_copy(grad_output);
    apply_activation_derivative(layer->output_cache, grad_activation, layer->activation);
    
    // Compute weight gradients: input^T * grad
    Matrix* input_T = matrix_transpose(layer->input_cache);
    Matrix* weight_grad = matrix_multiply(input_T, grad_activation);
    matrix_destroy(input_T);
    
    // Accumulate gradients
    matrix_add(layer->weight_gradients, weight_grad, layer->weight_gradients);
    matrix_destroy(weight_grad);
    
    // Compute bias gradients: sum of grad along batch dimension
    for (uint32_t j = 0; j < grad_activation->cols; j++) {
        float sum = 0.0f;
        for (uint32_t i = 0; i < grad_activation->rows; i++) {
            sum += grad_activation->data[i * grad_activation->cols + j];
        }
        layer->bias_gradients->data[j] += sum;
    }
    
    // Compute input gradient: grad * weights^T
    Matrix* weights_T = matrix_transpose(layer->weights);
    Matrix* grad_input = matrix_multiply(grad_activation, weights_T);
    matrix_destroy(weights_T);
    matrix_destroy(grad_activation);
    
    return grad_input;
}

// =====================================================================================================================
// Tensor Operations for CNN
// =====================================================================================================================

Tensor* tensor_create(uint32_t batch, uint32_t channels, uint32_t height, uint32_t width) {
    Tensor* tensor = (Tensor*)malloc(sizeof(Tensor));
    tensor->batch = batch;
    tensor->channels = channels;
    tensor->height = height;
    tensor->width = width;
    tensor->data = (float*)calloc(batch * channels * height * width, sizeof(float));
    return tensor;
}

void tensor_destroy(Tensor* tensor) {
    free(tensor->data);
    free(tensor);
}

float tensor_get(Tensor* tensor, uint32_t b, uint32_t c, uint32_t h, uint32_t w) {
    uint32_t idx = b * (tensor->channels * tensor->height * tensor->width) +
                   c * (tensor->height * tensor->width) +
                   h * tensor->width + w;
    return tensor->data[idx];
}

void tensor_set(Tensor* tensor, uint32_t b, uint32_t c, uint32_t h, uint32_t w, float value) {
    uint32_t idx = b * (tensor->channels * tensor->height * tensor->width) +
                   c * (tensor->height * tensor->width) +
                   h * tensor->width + w;
    tensor->data[idx] = value;
}

// =====================================================================================================================
// Convolutional Layer Operations
// =====================================================================================================================

Conv2DLayer* conv2d_layer_create(uint32_t input_channels, uint32_t num_filters, 
                                  uint32_t filter_size, uint32_t stride, 
                                  uint32_t padding, ActivationType activation) {
    Conv2DLayer* layer = (Conv2DLayer*)malloc(sizeof(Conv2DLayer));
    
    layer->input_channels = input_channels;
    layer->num_filters = num_filters;
    layer->filter_size = filter_size;
    layer->stride = stride;
    layer->padding = padding;
    layer->activation = activation;
    
    layer->filters = tensor_create(num_filters, input_channels, filter_size, filter_size);
    layer->biases = matrix_create(1, num_filters);
    layer->filter_gradients = tensor_create(num_filters, input_channels, filter_size, filter_size);
    layer->bias_gradients = matrix_create(1, num_filters);
    
    // He initialization
    float stddev = sqrt(2.0f / (input_channels * filter_size * filter_size));
    for (uint32_t i = 0; i < num_filters * input_channels * filter_size * filter_size; i++) {
        float u1 = (float)rand() / RAND_MAX;
        float u2 = (float)rand() / RAND_MAX;
        float z0 = sqrt(-2.0f * log(u1)) * cos(2.0f * M_PI * u2);
        layer->filters->data[i] = stddev * z0;
    }
    
    layer->input_cache = NULL;
    layer->output_cache = NULL;
    
    return layer;
}

void conv2d_layer_destroy(Conv2DLayer* layer) {
    tensor_destroy(layer->filters);
    matrix_destroy(layer->biases);
    tensor_destroy(layer->filter_gradients);
    matrix_destroy(layer->bias_gradients);
    
    if (layer->input_cache) tensor_destroy(layer->input_cache);
    if (layer->output_cache) tensor_destroy(layer->output_cache);
    
    free(layer);
}

Tensor* conv2d_layer_forward(Conv2DLayer* layer, Tensor* input) {
    uint32_t output_height = (input->height + 2 * layer->padding - layer->filter_size) / 
                             layer->stride + 1;
    uint32_t output_width = (input->width + 2 * layer->padding - layer->filter_size) / 
                            layer->stride + 1;
    
    Tensor* output = tensor_create(input->batch, layer->num_filters, 
                                   output_height, output_width);
    
    // Cache input
    if (layer->input_cache) tensor_destroy(layer->input_cache);
    layer->input_cache = tensor_create(input->batch, input->channels, 
                                       input->height, input->width);
    memcpy(layer->input_cache->data, input->data, 
           sizeof(float) * input->batch * input->channels * input->height * input->width);
    
    // Perform convolution
    for (uint32_t b = 0; b < input->batch; b++) {
        for (uint32_t f = 0; f < layer->num_filters; f++) {
            for (uint32_t oh = 0; oh < output_height; oh++) {
                for (uint32_t ow = 0; ow < output_width; ow++) {
                    float sum = layer->biases->data[f];
                    
                    for (uint32_t c = 0; c < input->channels; c++) {
                        for (uint32_t fh = 0; fh < layer->filter_size; fh++) {
                            for (uint32_t fw = 0; fw < layer->filter_size; fw++) {
                                int32_t ih = oh * layer->stride + fh - layer->padding;
                                int32_t iw = ow * layer->stride + fw - layer->padding;
                                
                                if (ih >= 0 && ih < (int32_t)input->height && 
                                    iw >= 0 && iw < (int32_t)input->width) {
                                    float input_val = tensor_get(input, b, c, ih, iw);
                                    float filter_val = tensor_get(layer->filters, f, c, fh, fw);
                                    sum += input_val * filter_val;
                                }
                            }
                        }
                    }
                    
                    tensor_set(output, b, f, oh, ow, sum);
                }
            }
        }
    }
    
    // Cache pre-activation
    if (layer->output_cache) tensor_destroy(layer->output_cache);
    layer->output_cache = tensor_create(output->batch, output->channels, 
                                        output->height, output->width);
    memcpy(layer->output_cache->data, output->data, 
           sizeof(float) * output->batch * output->channels * output->height * output->width);
    
    // Apply activation
    if (layer->activation == ACTIVATION_RELU) {
        for (uint32_t i = 0; i < output->batch * output->channels * 
                               output->height * output->width; i++) {
            output->data[i] = activation_relu(output->data[i]);
        }
    }
    
    return output;
}

// =====================================================================================================================
// Pooling Layer Operations
// =====================================================================================================================

PoolingLayer* pooling_layer_create(LayerType type, uint32_t pool_size, uint32_t stride) {
    PoolingLayer* layer = (PoolingLayer*)malloc(sizeof(PoolingLayer));
    layer->type = type;
    layer->pool_size = pool_size;
    layer->stride = stride;
    layer->input_cache = NULL;
    layer->output_cache = NULL;
    layer->max_indices = NULL;
    return layer;
}

void pooling_layer_destroy(PoolingLayer* layer) {
    if (layer->input_cache) tensor_destroy(layer->input_cache);
    if (layer->output_cache) tensor_destroy(layer->output_cache);
    if (layer->max_indices) matrix_destroy(layer->max_indices);
    free(layer);
}

Tensor* pooling_layer_forward(PoolingLayer* layer, Tensor* input) {
    uint32_t output_height = (input->height - layer->pool_size) / layer->stride + 1;
    uint32_t output_width = (input->width - layer->pool_size) / layer->stride + 1;
    
    Tensor* output = tensor_create(input->batch, input->channels, 
                                   output_height, output_width);
    
    // Cache input
    if (layer->input_cache) tensor_destroy(layer->input_cache);
    layer->input_cache = tensor_create(input->batch, input->channels, 
                                       input->height, input->width);
    memcpy(layer->input_cache->data, input->data, 
           sizeof(float) * input->batch * input->channels * input->height * input->width);
    
    if (layer->type == LAYER_MAXPOOL2D) {
        // Store max indices for backprop
        if (layer->max_indices) matrix_destroy(layer->max_indices);
        layer->max_indices = matrix_create(output->batch * output->channels * 
                                          output->height * output->width, 2);
        
        uint32_t idx = 0;
        
        for (uint32_t b = 0; b < input->batch; b++) {
            for (uint32_t c = 0; c < input->channels; c++) {
                for (uint32_t oh = 0; oh < output_height; oh++) {
                    for (uint32_t ow = 0; ow < output_width; ow++) {
                        float max_val = -INFINITY;
                        uint32_t max_h = 0, max_w = 0;
                        
                        for (uint32_t ph = 0; ph < layer->pool_size; ph++) {
                            for (uint32_t pw = 0; pw < layer->pool_size; pw++) {
                                uint32_t ih = oh * layer->stride + ph;
                                uint32_t iw = ow * layer->stride + pw;
                                
                                float val = tensor_get(input, b, c, ih, iw);
                                if (val > max_val) {
                                    max_val = val;
                                    max_h = ih;
                                    max_w = iw;
                                }
                            }
                        }
                        
                        tensor_set(output, b, c, oh, ow, max_val);
                        layer->max_indices->data[idx * 2] = max_h;
                        layer->max_indices->data[idx * 2 + 1] = max_w;
                        idx++;
                    }
                }
            }
        }
    } else {  // Average pooling
        for (uint32_t b = 0; b < input->batch; b++) {
            for (uint32_t c = 0; c < input->channels; c++) {
                for (uint32_t oh = 0; oh < output_height; oh++) {
                    for (uint32_t ow = 0; ow < output_width; ow++) {
                        float sum = 0.0f;
                        
                        for (uint32_t ph = 0; ph < layer->pool_size; ph++) {
                            for (uint32_t pw = 0; pw < layer->pool_size; pw++) {
                                uint32_t ih = oh * layer->stride + ph;
                                uint32_t iw = ow * layer->stride + pw;
                                sum += tensor_get(input, b, c, ih, iw);
                            }
                        }
                        
                        tensor_set(output, b, c, oh, ow, 
                                  sum / (layer->pool_size * layer->pool_size));
                    }
                }
            }
        }
    }
    
    return output;
}

// =====================================================================================================================
// LSTM Layer Operations
// =====================================================================================================================

LSTMLayer* lstm_layer_create(uint32_t input_size, uint32_t hidden_size) {
    LSTMLayer* layer = (LSTMLayer*)malloc(sizeof(LSTMLayer));
    
    layer->input_size = input_size;
    layer->hidden_size = hidden_size;
    
    // Input gate weights
    layer->weights_input = matrix_create(input_size, hidden_size);
    layer->weights_hidden_input = matrix_create(hidden_size, hidden_size);
    layer->bias_input = matrix_create(1, hidden_size);
    
    // Forget gate weights
    layer->weights_forget = matrix_create(input_size, hidden_size);
    layer->weights_hidden_forget = matrix_create(hidden_size, hidden_size);
    layer->bias_forget = matrix_create(1, hidden_size);
    
    // Cell gate weights
    layer->weights_cell = matrix_create(input_size, hidden_size);
    layer->weights_hidden_cell = matrix_create(hidden_size, hidden_size);
    layer->bias_cell = matrix_create(1, hidden_size);
    
    // Output gate weights
    layer->weights_output = matrix_create(input_size, hidden_size);
    layer->weights_hidden_output = matrix_create(hidden_size, hidden_size);
    layer->bias_output = matrix_create(1, hidden_size);
    
    // Initialize weights
    matrix_xavier_initialization(layer->weights_input);
    matrix_xavier_initialization(layer->weights_hidden_input);
    matrix_xavier_initialization(layer->weights_forget);
    matrix_xavier_initialization(layer->weights_hidden_forget);
    matrix_xavier_initialization(layer->weights_cell);
    matrix_xavier_initialization(layer->weights_hidden_cell);
    matrix_xavier_initialization(layer->weights_output);
    matrix_xavier_initialization(layer->weights_hidden_output);
    
    // Initialize forget gate bias to 1 (helps with gradient flow)
    matrix_fill(layer->bias_forget, 1.0f);
    
    // Create state
    layer->state = (LSTMState*)malloc(sizeof(LSTMState));
    layer->state->hidden = matrix_create(1, hidden_size);
    layer->state->cell = matrix_create(1, hidden_size);
    
    return layer;
}

void lstm_layer_destroy(LSTMLayer* layer) {
    matrix_destroy(layer->weights_input);
    matrix_destroy(layer->weights_forget);
    matrix_destroy(layer->weights_cell);
    matrix_destroy(layer->weights_output);
    matrix_destroy(layer->weights_hidden_input);
    matrix_destroy(layer->weights_hidden_forget);
    matrix_destroy(layer->weights_hidden_cell);
    matrix_destroy(layer->weights_hidden_output);
    matrix_destroy(layer->bias_input);
    matrix_destroy(layer->bias_forget);
    matrix_destroy(layer->bias_cell);
    matrix_destroy(layer->bias_output);
    matrix_destroy(layer->state->hidden);
    matrix_destroy(layer->state->cell);
    free(layer->state);
    free(layer);
}

Matrix* lstm_layer_forward(LSTMLayer* layer, Matrix* input) {
    // Input gate: i_t = σ(W_i * x_t + U_i * h_{t-1} + b_i)
    Matrix* input_gate = matrix_multiply(input, layer->weights_input);
    Matrix* hidden_contrib_input = matrix_multiply(layer->state->hidden, 
                                                   layer->weights_hidden_input);
    matrix_add(input_gate, hidden_contrib_input, input_gate);
    
    for (uint32_t i = 0; i < input_gate->cols; i++) {
        input_gate->data[i] += layer->bias_input->data[i];
        input_gate->data[i] = activation_sigmoid(input_gate->data[i]);
    }
    
    // Forget gate: f_t = σ(W_f * x_t + U_f * h_{t-1} + b_f)
    Matrix* forget_gate = matrix_multiply(input, layer->weights_forget);
    Matrix* hidden_contrib_forget = matrix_multiply(layer->state->hidden, 
                                                    layer->weights_hidden_forget);
    matrix_add(forget_gate, hidden_contrib_forget, forget_gate);
    
    for (uint32_t i = 0; i < forget_gate->cols; i++) {
        forget_gate->data[i] += layer->bias_forget->data[i];
        forget_gate->data[i] = activation_sigmoid(forget_gate->data[i]);
    }
    
    // Cell gate: g_t = tanh(W_c * x_t + U_c * h_{t-1} + b_c)
    Matrix* cell_gate = matrix_multiply(input, layer->weights_cell);
    Matrix* hidden_contrib_cell = matrix_multiply(layer->state->hidden, 
                                                  layer->weights_hidden_cell);
    matrix_add(cell_gate, hidden_contrib_cell, cell_gate);
    
    for (uint32_t i = 0; i < cell_gate->cols; i++) {
        cell_gate->data[i] += layer->bias_cell->data[i];
        cell_gate->data[i] = activation_tanh(cell_gate->data[i]);
    }
    
    // Output gate: o_t = σ(W_o * x_t + U_o * h_{t-1} + b_o)
    Matrix* output_gate = matrix_multiply(input, layer->weights_output);
    Matrix* hidden_contrib_output = matrix_multiply(layer->state->hidden, 
                                                    layer->weights_hidden_output);
    matrix_add(output_gate, hidden_contrib_output, output_gate);
    
    for (uint32_t i = 0; i < output_gate->cols; i++) {
        output_gate->data[i] += layer->bias_output->data[i];
        output_gate->data[i] = activation_sigmoid(output_gate->data[i]);
    }
    
    // Update cell state: c_t = f_t ⊙ c_{t-1} + i_t ⊙ g_t
    Matrix* new_cell = matrix_create(1, layer->hidden_size);
    for (uint32_t i = 0; i < layer->hidden_size; i++) {
        new_cell->data[i] = forget_gate->data[i] * layer->state->cell->data[i] +
                           input_gate->data[i] * cell_gate->data[i];
    }
    
    // Update hidden state: h_t = o_t ⊙ tanh(c_t)
    Matrix* new_hidden = matrix_create(1, layer->hidden_size);
    for (uint32_t i = 0; i < layer->hidden_size; i++) {
        new_hidden->data[i] = output_gate->data[i] * activation_tanh(new_cell->data[i]);
    }
    
    // Update state
    matrix_destroy(layer->state->cell);
    matrix_destroy(layer->state->hidden);
    layer->state->cell = new_cell;
    layer->state->hidden = new_hidden;
    
    // Cleanup
    matrix_destroy(input_gate);
    matrix_destroy(forget_gate);
    matrix_destroy(cell_gate);
    matrix_destroy(output_gate);
    matrix_destroy(hidden_contrib_input);
    matrix_destroy(hidden_contrib_forget);
    matrix_destroy(hidden_contrib_cell);
    matrix_destroy(hidden_contrib_output);
    
    return matrix_copy(layer->state->hidden);
}

// =====================================================================================================================
// Loss Functions
// =====================================================================================================================

float loss_mse(Matrix* predicted, Matrix* target) {
    float sum = 0.0f;
    
    for (uint32_t i = 0; i < predicted->rows * predicted->cols; i++) {
        float diff = predicted->data[i] - target->data[i];
        sum += diff * diff;
    }
    
    return sum / (predicted->rows * predicted->cols);
}

void loss_mse_gradient(Matrix* predicted, Matrix* target, Matrix* gradient) {
    for (uint32_t i = 0; i < predicted->rows * predicted->cols; i++) {
        gradient->data[i] = 2.0f * (predicted->data[i] - target->data[i]) / 
                           (predicted->rows * predicted->cols);
    }
}

float loss_cross_entropy(Matrix* predicted, Matrix* target) {
    float sum = 0.0f;
    
    for (uint32_t i = 0; i < predicted->rows * predicted->cols; i++) {
        if (target->data[i] > 0.0f) {
            sum -= target->data[i] * log(predicted->data[i] + 1e-10f);
        }
    }
    
    return sum / predicted->rows;
}

void loss_cross_entropy_gradient(Matrix* predicted, Matrix* target, Matrix* gradient) {
    for (uint32_t i = 0; i < predicted->rows * predicted->cols; i++) {
        gradient->data[i] = (predicted->data[i] - target->data[i]) / predicted->rows;
    }
}

// =====================================================================================================================
// Optimizer Operations
// =====================================================================================================================

OptimizerState* optimizer_create(OptimizerType type, float learning_rate, 
                                 uint32_t num_layers) {
    OptimizerState* opt = (OptimizerState*)malloc(sizeof(OptimizerState));
    opt->type = type;
    opt->learning_rate = learning_rate;
    opt->momentum = 0.9f;
    opt->beta1 = 0.9f;
    opt->beta2 = 0.999f;
    opt->epsilon = 1e-8f;
    opt->timestep = 0;
    opt->num_layers = num_layers;
    
    // Allocate momentum/velocity arrays
    opt->velocity_weights = (Matrix**)calloc(num_layers, sizeof(Matrix*));
    opt->velocity_biases = (Matrix**)calloc(num_layers, sizeof(Matrix*));
    opt->squared_velocity_weights = (Matrix**)calloc(num_layers, sizeof(Matrix*));
    opt->squared_velocity_biases = (Matrix**)calloc(num_layers, sizeof(Matrix*));
    
    return opt;
}

void optimizer_update_dense(OptimizerState* opt, DenseLayer* layer, uint32_t layer_idx) {
    opt->timestep++;
    
    if (opt->type == OPTIMIZER_SGD) {
        // Simple gradient descent
        for (uint32_t i = 0; i < layer->weights->rows * layer->weights->cols; i++) {
            layer->weights->data[i] -= opt->learning_rate * layer->weight_gradients->data[i];
        }
        
        for (uint32_t i = 0; i < layer->biases->cols; i++) {
            layer->biases->data[i] -= opt->learning_rate * layer->bias_gradients->data[i];
        }
    } else if (opt->type == OPTIMIZER_ADAM) {
        // Initialize velocity if needed
        if (opt->velocity_weights[layer_idx] == NULL) {
            opt->velocity_weights[layer_idx] = matrix_create(layer->weights->rows, 
                                                             layer->weights->cols);
            opt->squared_velocity_weights[layer_idx] = matrix_create(layer->weights->rows, 
                                                                     layer->weights->cols);
            opt->velocity_biases[layer_idx] = matrix_create(1, layer->biases->cols);
            opt->squared_velocity_biases[layer_idx] = matrix_create(1, layer->biases->cols);
        }
        
        // Adam update for weights
        for (uint32_t i = 0; i < layer->weights->rows * layer->weights->cols; i++) {
            float g = layer->weight_gradients->data[i];
            
            // Update biased first moment estimate
            opt->velocity_weights[layer_idx]->data[i] = 
                opt->beta1 * opt->velocity_weights[layer_idx]->data[i] + (1.0f - opt->beta1) * g;
            
            // Update biased second moment estimate
            opt->squared_velocity_weights[layer_idx]->data[i] = 
                opt->beta2 * opt->squared_velocity_weights[layer_idx]->data[i] + 
                (1.0f - opt->beta2) * g * g;
            
            // Bias correction
            float m_hat = opt->velocity_weights[layer_idx]->data[i] / 
                         (1.0f - pow(opt->beta1, opt->timestep));
            float v_hat = opt->squared_velocity_weights[layer_idx]->data[i] / 
                         (1.0f - pow(opt->beta2, opt->timestep));
            
            // Update weights
            layer->weights->data[i] -= opt->learning_rate * m_hat / (sqrt(v_hat) + opt->epsilon);
        }
        
        // Adam update for biases
        for (uint32_t i = 0; i < layer->biases->cols; i++) {
            float g = layer->bias_gradients->data[i];
            
            opt->velocity_biases[layer_idx]->data[i] = 
                opt->beta1 * opt->velocity_biases[layer_idx]->data[i] + (1.0f - opt->beta1) * g;
            
            opt->squared_velocity_biases[layer_idx]->data[i] = 
                opt->beta2 * opt->squared_velocity_biases[layer_idx]->data[i] + 
                (1.0f - opt->beta2) * g * g;
            
            float m_hat = opt->velocity_biases[layer_idx]->data[i] / 
                         (1.0f - pow(opt->beta1, opt->timestep));
            float v_hat = opt->squared_velocity_biases[layer_idx]->data[i] / 
                         (1.0f - pow(opt->beta2, opt->timestep));
            
            layer->biases->data[i] -= opt->learning_rate * m_hat / (sqrt(v_hat) + opt->epsilon);
        }
    }
    
    // Clear gradients
    matrix_fill(layer->weight_gradients, 0.0f);
    matrix_fill(layer->bias_gradients, 0.0f);
}

// =====================================================================================================================
// Neural Network Model
// =====================================================================================================================

NeuralNetwork* neural_network_create() {
    NeuralNetwork* nn = (NeuralNetwork*)malloc(sizeof(NeuralNetwork));
    nn->num_layers = 0;
    nn->capacity = 10;
    nn->layers = (void**)malloc(sizeof(void*) * nn->capacity);
    nn->layer_types = (LayerType*)malloc(sizeof(LayerType) * nn->capacity);
    nn->optimizer = NULL;
    nn->loss_function = LOSS_MSE;
    nn->dropout_rate = 0.0f;
    return nn;
}

void neural_network_add_layer(NeuralNetwork* nn, void* layer, LayerType type) {
    if (nn->num_layers >= nn->capacity) {
        nn->capacity *= 2;
        nn->layers = (void**)realloc(nn->layers, sizeof(void*) * nn->capacity);
        nn->layer_types = (LayerType*)realloc(nn->layer_types, sizeof(LayerType) * nn->capacity);
    }
    
    nn->layers[nn->num_layers] = layer;
    nn->layer_types[nn->num_layers] = type;
    nn->num_layers++;
}

Matrix* neural_network_forward(NeuralNetwork* nn, Matrix* input) {
    Matrix* output = matrix_copy(input);
    
    for (uint32_t i = 0; i < nn->num_layers; i++) {
        Matrix* prev_output = output;
        
        if (nn->layer_types[i] == LAYER_DENSE) {
            output = dense_layer_forward((DenseLayer*)nn->layers[i], prev_output);
        } else if (nn->layer_types[i] == LAYER_LSTM) {
            output = lstm_layer_forward((LSTMLayer*)nn->layers[i], prev_output);
        }
        
        if (prev_output != input) {
            matrix_destroy(prev_output);
        }
    }
    
    return output;
}

float neural_network_train_batch(NeuralNetwork* nn, Matrix* input, Matrix* target) {
    // Forward pass
    Matrix* output = neural_network_forward(nn, input);
    
    // Compute loss
    float loss = 0.0f;
    if (nn->loss_function == LOSS_MSE) {
        loss = loss_mse(output, target);
    } else if (nn->loss_function == LOSS_CROSS_ENTROPY) {
        loss = loss_cross_entropy(output, target);
    }
    
    // Backward pass
    Matrix* grad = matrix_create(output->rows, output->cols);
    
    if (nn->loss_function == LOSS_MSE) {
        loss_mse_gradient(output, target, grad);
    } else if (nn->loss_function == LOSS_CROSS_ENTROPY) {
        loss_cross_entropy_gradient(output, target, grad);
    }
    
    // Backpropagate through layers
    for (int32_t i = nn->num_layers - 1; i >= 0; i--) {
        if (nn->layer_types[i] == LAYER_DENSE) {
            Matrix* new_grad = dense_layer_backward((DenseLayer*)nn->layers[i], grad);
            matrix_destroy(grad);
            grad = new_grad;
        }
    }
    
    // Update weights
    for (uint32_t i = 0; i < nn->num_layers; i++) {
        if (nn->layer_types[i] == LAYER_DENSE) {
            optimizer_update_dense(nn->optimizer, (DenseLayer*)nn->layers[i], i);
        }
    }
    
    matrix_destroy(grad);
    matrix_destroy(output);
    
    return loss;
}

// =====================================================================================================================
// End of Neural Network Engine Module
// Lines: ~1350
// Total so far: ~3500 lines
// =====================================================================================================================
