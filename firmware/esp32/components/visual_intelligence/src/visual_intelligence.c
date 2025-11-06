#include "visual_intelligence.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_op_resolver.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "model_manager.h" // To get the model data
#include "image_utils.h"   // For image preprocessing

static const char *TAG = "VISUAL_INTEL";

// TFLite globals
constexpr int kTensorArenaSize = 300 * 1024; // 300KB Arena for the model, adjust as needed
static uint8_t tensor_arena[kTensorArenaSize];
static tflite::MicroInterpreter* interpreter = nullptr;
const tflite::Model* model = nullptr;
TfLiteTensor* input = nullptr;

esp_err_t visual_intelligence_init(void) {
    // 1. Load the model using the model_manager
    const uint8_t* model_data = model_manager_get_model_data(MODEL_TYPE_OBJECT_DETECTION);
    if (!model_data) {
        ESP_LOGE(TAG, "Failed to get object detection model data from model_manager.");
        return ESP_ERR_NOT_FOUND;
    }

    model = tflite::GetModel(model_data);
    if (model->version() != TFLITE_SCHEMA_VERSION) {
        ESP_LOGE(TAG, "Model provided is schema version %lu not equal to supported version %d.",
                 model->version(), TFLITE_SCHEMA_VERSION);
        return ESP_FAIL;
    }

    // 2. Create an OpResolver
    // This needs to be populated with the operations your model uses.
    // For a typical MobileNetV2-based SSD, you'll need at least these.
    static tflite::MicroMutableOpResolver<15> op_resolver;
    op_resolver.AddConv2D();
    op_resolver.AddDepthwiseConv2D();
    op_resolver.AddAdd();
    op_resolver.AddRelu6();
    op_resolver.AddReshape();
    op_resolver.AddResizeNearestNeighbor();
    op_resolver.AddPad();
    op_resolver.AddMean();
    op_resolver.AddConcatenation();
    op_resolver.AddLogistic();
    op_resolver.AddQuantize();
    op_resolver.AddDequantize();

    // 3. Instantiate the interpreter
    static tflite::MicroInterpreter static_interpreter(model, op_resolver, tensor_arena, kTensorArenaSize);
    interpreter = &static_interpreter;

    // 4. Allocate tensors
    if (interpreter->AllocateTensors() != kTfLiteOk) {
        ESP_LOGE(TAG, "Failed to allocate tensors!");
        return ESP_FAIL;
    }

    // 5. Get a pointer to the input tensor
    input = interpreter->input(0);

    ESP_LOGI(TAG, "Visual intelligence module initialized.");
    ESP_LOGI(TAG, "Input tensor -> size: %d, type: %s, dims: [%d, %d, %d, %d]", 
             input->bytes, TfLiteTypeGetName(input->type), 
             input->dims->data[0], input->dims->data[1], input->dims->data[2], input->dims->data[3]);
    ESP_LOGI(TAG, "Model has %d output tensors.", interpreter->outputs_size());

    return ESP_OK;
}

esp_err_t visual_intelligence_deinit(visual_intelligence_handle_t handle) {
    if (handle) {
        // TFLM resources are statically allocated, so we just need to free our handle
        free(handle);
    }
    return ESP_OK;
}

esp_err_t visual_intelligence_analyze_frame(camera_fb_t *fb, visual_analysis_result_t **results, int *result_count) {
    if (!interpreter || !input) {
        ESP_LOGE(TAG, "Visual intelligence not initialized.");
        return ESP_ERR_INVALID_STATE;
    }

    // 1. Decode JPEG to RGB
    // The model expects a certain input size, e.g., 320x320.
    // We need a buffer for the decoded full-size image and one for the resized image.
    int model_input_width = input->dims->data[2];
    int model_input_height = input->dims->data[1];
    int model_input_channels = input->dims->data[3];

    uint8_t *decoded_image = (uint8_t *)malloc(fb->width * fb->height * 3);
    if (!decoded_image) {
        ESP_LOGE(TAG, "Failed to allocate buffer for decoded image.");
        return ESP_ERR_NO_MEM;
    }

    int decoded_width, decoded_height;
    esp_err_t dec_err = image_utils_decode_jpg(fb, decoded_image, &decoded_width, &decoded_height);
    if (dec_err != ESP_OK) {
        ESP_LOGE(TAG, "JPEG decoding failed.");
        free(decoded_image);
        return dec_err;
    }

    // 2. Resize the image to the model's expected input size
    uint8_t *resized_image = (uint8_t *)malloc(model_input_width * model_input_height * model_input_channels);
    if (!resized_image) {
        ESP_LOGE(TAG, "Failed to allocate buffer for resized image.");
        free(decoded_image);
        return ESP_ERR_NO_MEM;
    }

    image_utils_resize_image(decoded_image, decoded_width, decoded_height, resized_image, model_input_width, model_input_height);
    free(decoded_image); // We don't need the full-size decoded image anymore

    // 3. Pre-process and copy data to the input tensor
    // This depends on the model's requirements (e.g., quantization, normalization).
    // For a uint8 quantized model, it might be a direct copy.
    // For a float model, you'd convert to float and normalize (e.g., to [-1, 1]).
    if (input->type == kTfLiteUInt8) {
        memcpy(input->data.uint8, resized_image, input->bytes);
    } else if (input->type == kTfLiteFloat32) {
        // Example for normalization to [-1, 1]
        float *input_float = input->data.f;
        for (int i = 0; i < input->bytes / sizeof(float); i++) {
            input_float[i] = (resized_image[i] - 127.5f) / 127.5f;
        }
    } else {
        ESP_LOGE(TAG, "Unsupported input tensor type: %d", input->type);
        free(resized_image);
        return ESP_FAIL;
    }
    
    free(resized_image);

    // 4. Run inference
    ESP_LOGI(TAG, "Invoking TFLite model...");
    if (interpreter->Invoke() != kTfLiteOk) {
        ESP_LOGE(TAG, "Model invocation failed!");
        return ESP_FAIL;
    }
    ESP_LOGI(TAG, "Inference complete.");

    // 5. Post-process the output
    // The format of the output tensor depends on the model.
    // For an object detection model like SSD MobileNet, it might contain:
    // output[0]: Bounding boxes (e.g., [1, 10, 4]) -> 10 boxes, 4 coords each (y_min, x_min, y_max, x_max)
    // output[1]: Class IDs (e.g., [1, 10])
    // output[2]: Scores (e.g., [1, 10])
    // output[3]: Number of detections (e.g., [1])
    // This is a placeholder and needs to be adapted to your specific model.
    
    // This is a simplified example assuming a single output tensor with flat results.
    // A real implementation requires parsing the specific output tensors of your model.
    *result_count = 0; // Placeholder
    *results = NULL;   // Placeholder

    // Example of how you might parse a hypothetical output:
    // float* output_data = output->data.f;
    // int num_detections = (int)output_data[0];
    // *results = (visual_analysis_result_t*)malloc(sizeof(visual_analysis_result_t) * num_detections);
    // ... loop through detections and fill the results array ...
    // *result_count = num_detections;

    return ESP_OK;
}

void visual_intelligence_free_result(visual_analysis_result_t* result) {
    if (result && result->additional_metadata) {
        cJSON_Delete(result->additional_metadata);
        result->additional_metadata = NULL;
    }
}
