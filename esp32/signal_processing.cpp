// =====================================================================================================================
// ESP32 Digital Signal Processing Engine
// FFT, filters, spectral analysis, audio processing, sensor fusion, wavelet transforms
// =====================================================================================================================

#include <Arduino.h>
#include <math.h>

// =====================================================================================================================
// DSP Structures
// =====================================================================================================================

#define MAX_FFT_SIZE 2048
#define MAX_FILTER_ORDER 128
#define MAX_CHANNELS 8
#define MAX_SPECTROGRAM_BINS 256

// Complex number
typedef struct {
    float real;
    float imag;
} Complex;

// FFT result
typedef struct {
    Complex* data;
    uint32_t size;
    float sample_rate;
    float* magnitude;
    float* phase;
    float* power_spectrum;
} FFTResult;

// Filter types
typedef enum {
    FILTER_LOWPASS,
    FILTER_HIGHPASS,
    FILTER_BANDPASS,
    FILTER_BANDSTOP,
    FILTER_ALLPASS
} FilterType;

// Filter design methods
typedef enum {
    FILTER_BUTTERWORTH,
    FILTER_CHEBYSHEV1,
    FILTER_CHEBYSHEV2,
    FILTER_ELLIPTIC,
    FILTER_BESSEL
} FilterDesign;

// IIR filter (Infinite Impulse Response)
typedef struct {
    FilterType type;
    FilterDesign design;
    uint32_t order;
    float* b_coeffs;  // Numerator coefficients
    float* a_coeffs;  // Denominator coefficients
    float* x_history; // Input history
    float* y_history; // Output history
    float cutoff_freq;
    float sample_rate;
    float q_factor;
} IIRFilter;

// FIR filter (Finite Impulse Response)
typedef struct {
    FilterType type;
    uint32_t order;
    float* coefficients;
    float* delay_line;
    uint32_t delay_index;
    float cutoff_freq;
    float sample_rate;
} FIRFilter;

// Window functions
typedef enum {
    WINDOW_RECTANGULAR,
    WINDOW_HAMMING,
    WINDOW_HANNING,
    WINDOW_BLACKMAN,
    WINDOW_KAISER,
    WINDOW_GAUSSIAN
} WindowType;

// Spectrogram
typedef struct {
    float** data;  // [time][frequency]
    uint32_t time_bins;
    uint32_t freq_bins;
    float min_freq;
    float max_freq;
    float hop_size;
    uint32_t window_size;
} Spectrogram;

// Mel-frequency spectrogram
typedef struct {
    float** data;
    uint32_t time_bins;
    uint32_t mel_bins;
    float min_freq;
    float max_freq;
    float sample_rate;
} MelSpectrogram;

// MFCC (Mel-Frequency Cepstral Coefficients)
typedef struct {
    float** coefficients;
    uint32_t num_frames;
    uint32_t num_coeffs;
    float frame_length;
    float frame_shift;
} MFCC;

// Wavelet types
typedef enum {
    WAVELET_HAAR,
    WAVELET_DAUBECHIES,
    WAVELET_SYMLET,
    WAVELET_COIFLET,
    WAVELET_BIORTHOGONAL,
    WAVELET_MORLET,
    WAVELET_MEXICAN_HAT
} WaveletType;

// Wavelet transform
typedef struct {
    WaveletType type;
    float** coefficients;
    uint32_t levels;
    uint32_t* level_sizes;
    float* scaling_coeffs;
    float* wavelet_coeffs;
} WaveletTransform;

// Adaptive filter
typedef struct {
    float* weights;
    uint32_t num_taps;
    float step_size;
    float* input_buffer;
    float error_signal;
    float convergence_rate;
} AdaptiveFilter;

// Kalman filter for signal processing
typedef struct {
    float state;
    float covariance;
    float process_noise;
    float measurement_noise;
    float kalman_gain;
} KalmanFilter1D;

// Envelope detector
typedef struct {
    float attack_time;
    float release_time;
    float current_value;
    float sample_rate;
    float attack_coeff;
    float release_coeff;
} EnvelopeDetector;

// Peak detector
typedef struct {
    float* peaks;
    uint32_t* peak_indices;
    uint32_t peak_count;
    float threshold;
    uint32_t min_distance;
} PeakDetector;

// Correlation result
typedef struct {
    float* values;
    int32_t* lags;
    uint32_t size;
    float max_correlation;
    int32_t max_lag;
} CorrelationResult;

// Resampler
typedef struct {
    float input_rate;
    float output_rate;
    float ratio;
    float* buffer;
    uint32_t buffer_size;
    uint32_t buffer_pos;
    float phase;
} Resampler;

// Equalizer band
typedef struct {
    float center_freq;
    float gain_db;
    float q_factor;
    IIRFilter filter;
} EqualizerBand;

// Parametric equalizer
typedef struct {
    EqualizerBand* bands;
    uint32_t num_bands;
    float sample_rate;
} ParametricEQ;

// Compressor/Limiter
typedef struct {
    float threshold_db;
    float ratio;
    float attack_time;
    float release_time;
    float makeup_gain_db;
    EnvelopeDetector envelope;
    float gain_reduction;
} Compressor;

// Noise gate
typedef struct {
    float threshold_db;
    float attack_time;
    float release_time;
    float hold_time;
    EnvelopeDetector envelope;
    bool gate_open;
    uint64_t hold_start;
} NoiseGate;

// Pitch detector
typedef enum {
    PITCH_AUTOCORRELATION,
    PITCH_CEPSTRUM,
    PITCH_HPS,  // Harmonic Product Spectrum
    PITCH_YIN
} PitchDetectionMethod;

typedef struct {
    PitchDetectionMethod method;
    float detected_pitch;
    float confidence;
    float min_freq;
    float max_freq;
} PitchDetector;

// Audio effect - Reverb
typedef struct {
    float* delay_buffer;
    uint32_t buffer_size;
    uint32_t write_pos;
    float* comb_delays;
    float* allpass_delays;
    uint32_t num_combs;
    uint32_t num_allpass;
    float room_size;
    float damping;
    float wet_level;
    float dry_level;
} Reverb;

// Audio effect - Delay
typedef struct {
    float* buffer;
    uint32_t buffer_size;
    uint32_t write_pos;
    float delay_time;
    float feedback;
    float wet_level;
    float dry_level;
} Delay;

// Audio effect - Chorus
typedef struct {
    float* buffer;
    uint32_t buffer_size;
    float* lfo_phase;
    uint32_t num_voices;
    float depth;
    float rate;
    float wet_level;
} Chorus;

// =====================================================================================================================
// Global DSP State
// =====================================================================================================================

FFTResult g_fft_result;
IIRFilter g_iir_filters[MAX_CHANNELS];
FIRFilter g_fir_filters[MAX_CHANNELS];
Spectrogram g_spectrogram;
WaveletTransform g_wavelet_transform;

// =====================================================================================================================
// Complex Number Operations
// =====================================================================================================================

Complex complex_add(Complex a, Complex b) {
    Complex result;
    result.real = a.real + b.real;
    result.imag = a.imag + b.imag;
    return result;
}

Complex complex_sub(Complex a, Complex b) {
    Complex result;
    result.real = a.real - b.real;
    result.imag = a.imag - b.imag;
    return result;
}

Complex complex_mul(Complex a, Complex b) {
    Complex result;
    result.real = a.real * b.real - a.imag * b.imag;
    result.imag = a.real * b.imag + a.imag * b.real;
    return result;
}

float complex_magnitude(Complex c) {
    return sqrt(c.real * c.real + c.imag * c.imag);
}

float complex_phase(Complex c) {
    return atan2(c.imag, c.real);
}

Complex complex_exp(float theta) {
    Complex result;
    result.real = cos(theta);
    result.imag = sin(theta);
    return result;
}

// =====================================================================================================================
// FFT Implementation (Cooley-Tukey Radix-2)
// =====================================================================================================================

void fft_bit_reverse(Complex* data, uint32_t n) {
    uint32_t j = 0;
    
    for (uint32_t i = 0; i < n - 1; i++) {
        if (i < j) {
            Complex temp = data[i];
            data[i] = data[j];
            data[j] = temp;
        }
        
        uint32_t k = n / 2;
        while (k <= j) {
            j -= k;
            k /= 2;
        }
        j += k;
    }
}

void fft_compute(Complex* data, uint32_t n, bool inverse) {
    if (n <= 1) return;
    
    // Bit reversal
    fft_bit_reverse(data, n);
    
    // Cooley-Tukey FFT
    for (uint32_t s = 1; s <= log2(n); s++) {
        uint32_t m = 1 << s;
        float theta = (inverse ? 2.0f : -2.0f) * PI / m;
        Complex wm = complex_exp(theta);
        
        for (uint32_t k = 0; k < n; k += m) {
            Complex w = {1.0f, 0.0f};
            
            for (uint32_t j = 0; j < m / 2; j++) {
                Complex t = complex_mul(w, data[k + j + m / 2]);
                Complex u = data[k + j];
                
                data[k + j] = complex_add(u, t);
                data[k + j + m / 2] = complex_sub(u, t);
                
                w = complex_mul(w, wm);
            }
        }
        
        if (s % 4 == 0) yield();
    }
    
    // Normalize for inverse FFT
    if (inverse) {
        for (uint32_t i = 0; i < n; i++) {
            data[i].real /= n;
            data[i].imag /= n;
        }
    }
}

void fft_real(const float* input, uint32_t n, FFTResult* result) {
    // Convert real input to complex
    result->data = (Complex*)malloc(sizeof(Complex) * n);
    result->size = n;
    
    for (uint32_t i = 0; i < n; i++) {
        result->data[i].real = input[i];
        result->data[i].imag = 0.0f;
    }
    
    // Perform FFT
    fft_compute(result->data, n, false);
    
    // Compute magnitude and phase
    result->magnitude = (float*)malloc(sizeof(float) * n);
    result->phase = (float*)malloc(sizeof(float) * n);
    result->power_spectrum = (float*)malloc(sizeof(float) * n);
    
    for (uint32_t i = 0; i < n; i++) {
        result->magnitude[i] = complex_magnitude(result->data[i]);
        result->phase[i] = complex_phase(result->data[i]);
        result->power_spectrum[i] = result->magnitude[i] * result->magnitude[i];
    }
    
    Serial.printf("[DSP] FFT computed, size=%d\n", n);
}

void fft_inverse(FFTResult* result, float* output) {
    fft_compute(result->data, result->size, true);
    
    for (uint32_t i = 0; i < result->size; i++) {
        output[i] = result->data[i].real;
    }
}

// =====================================================================================================================
// Window Functions
// =====================================================================================================================

void window_apply(float* data, uint32_t n, WindowType type) {
    for (uint32_t i = 0; i < n; i++) {
        float window_value = 1.0f;
        
        switch (type) {
            case WINDOW_HAMMING:
                window_value = 0.54f - 0.46f * cos(2.0f * PI * i / (n - 1));
                break;
                
            case WINDOW_HANNING:
                window_value = 0.5f * (1.0f - cos(2.0f * PI * i / (n - 1)));
                break;
                
            case WINDOW_BLACKMAN:
                window_value = 0.42f - 0.5f * cos(2.0f * PI * i / (n - 1)) +
                              0.08f * cos(4.0f * PI * i / (n - 1));
                break;
                
            case WINDOW_KAISER: {
                float alpha = 3.0f;
                float beta = PI * alpha;
                float x = 2.0f * i / (n - 1) - 1.0f;
                // Simplified Kaiser window (approximation)
                window_value = 1.0f - x * x;
                break;
            }
                
            case WINDOW_GAUSSIAN: {
                float sigma = 0.4f;
                float x = (i - (n - 1) / 2.0f) / (sigma * (n - 1) / 2.0f);
                window_value = exp(-0.5f * x * x);
                break;
            }
                
            default:  // WINDOW_RECTANGULAR
                window_value = 1.0f;
                break;
        }
        
        data[i] *= window_value;
    }
}

// =====================================================================================================================
// FIR Filter Design and Processing
// =====================================================================================================================

void fir_design_lowpass(FIRFilter* filter, float cutoff, float sample_rate, uint32_t order) {
    filter->type = FILTER_LOWPASS;
    filter->order = order;
    filter->cutoff_freq = cutoff;
    filter->sample_rate = sample_rate;
    filter->delay_index = 0;
    
    filter->coefficients = (float*)malloc(sizeof(float) * order);
    filter->delay_line = (float*)malloc(sizeof(float) * order);
    memset(filter->delay_line, 0, sizeof(float) * order);
    
    // Window method (Hamming)
    float wc = 2.0f * PI * cutoff / sample_rate;
    
    for (uint32_t n = 0; n < order; n++) {
        int32_t m = n - (int32_t)(order / 2);
        
        if (m == 0) {
            filter->coefficients[n] = wc / PI;
        } else {
            filter->coefficients[n] = sin(wc * m) / (PI * m);
        }
        
        // Apply Hamming window
        filter->coefficients[n] *= 0.54f - 0.46f * cos(2.0f * PI * n / (order - 1));
    }
    
    // Normalize
    float sum = 0.0f;
    for (uint32_t n = 0; n < order; n++) {
        sum += filter->coefficients[n];
    }
    for (uint32_t n = 0; n < order; n++) {
        filter->coefficients[n] /= sum;
    }
}

float fir_process_sample(FIRFilter* filter, float input) {
    // Add input to delay line
    filter->delay_line[filter->delay_index] = input;
    
    // Compute output
    float output = 0.0f;
    uint32_t idx = filter->delay_index;
    
    for (uint32_t n = 0; n < filter->order; n++) {
        output += filter->coefficients[n] * filter->delay_line[idx];
        idx = (idx == 0) ? filter->order - 1 : idx - 1;
    }
    
    // Update delay index
    filter->delay_index = (filter->delay_index + 1) % filter->order;
    
    return output;
}

void fir_process_buffer(FIRFilter* filter, const float* input, float* output, uint32_t length) {
    for (uint32_t i = 0; i < length; i++) {
        output[i] = fir_process_sample(filter, input[i]);
        if (i % 100 == 0) yield();
    }
}

// =====================================================================================================================
// IIR Filter Design and Processing (Butterworth)
// =====================================================================================================================

void iir_design_butterworth_lowpass(IIRFilter* filter, float cutoff, float sample_rate,
                                   uint32_t order) {
    filter->type = FILTER_LOWPASS;
    filter->design = FILTER_BUTTERWORTH;
    filter->order = order;
    filter->cutoff_freq = cutoff;
    filter->sample_rate = sample_rate;
    
    // Allocate coefficients and history
    filter->b_coeffs = (float*)malloc(sizeof(float) * (order + 1));
    filter->a_coeffs = (float*)malloc(sizeof(float) * (order + 1));
    filter->x_history = (float*)malloc(sizeof(float) * (order + 1));
    filter->y_history = (float*)malloc(sizeof(float) * (order + 1));
    
    memset(filter->x_history, 0, sizeof(float) * (order + 1));
    memset(filter->y_history, 0, sizeof(float) * (order + 1));
    
    // Bilinear transform
    float wc = 2.0f * PI * cutoff;
    float T = 1.0f / sample_rate;
    float K = tan(wc * T / 2.0f);
    
    // Second-order Butterworth (simplified)
    if (order == 2) {
        float norm = 1.0f / (1.0f + K / 0.7071f + K * K);
        
        filter->b_coeffs[0] = K * K * norm;
        filter->b_coeffs[1] = 2.0f * filter->b_coeffs[0];
        filter->b_coeffs[2] = filter->b_coeffs[0];
        
        filter->a_coeffs[0] = 1.0f;
        filter->a_coeffs[1] = 2.0f * (K * K - 1.0f) * norm;
        filter->a_coeffs[2] = (1.0f - K / 0.7071f + K * K) * norm;
    }
}

float iir_process_sample(IIRFilter* filter, float input) {
    // Shift history
    for (int32_t i = filter->order; i > 0; i--) {
        filter->x_history[i] = filter->x_history[i - 1];
        filter->y_history[i] = filter->y_history[i - 1];
    }
    
    filter->x_history[0] = input;
    
    // Compute output (Direct Form II)
    float output = 0.0f;
    
    for (uint32_t i = 0; i <= filter->order; i++) {
        output += filter->b_coeffs[i] * filter->x_history[i];
    }
    
    for (uint32_t i = 1; i <= filter->order; i++) {
        output -= filter->a_coeffs[i] * filter->y_history[i];
    }
    
    filter->y_history[0] = output;
    
    return output;
}

// =====================================================================================================================
// Spectrogram Generation
// =====================================================================================================================

void spectrogram_compute(const float* signal, uint32_t signal_length, float sample_rate,
                        uint32_t window_size, uint32_t hop_size, Spectrogram* spec) {
    spec->window_size = window_size;
    spec->hop_size = hop_size;
    spec->time_bins = (signal_length - window_size) / hop_size + 1;
    spec->freq_bins = window_size / 2 + 1;
    spec->min_freq = 0.0f;
    spec->max_freq = sample_rate / 2.0f;
    
    // Allocate spectrogram data
    spec->data = (float**)malloc(sizeof(float*) * spec->time_bins);
    for (uint32_t i = 0; i < spec->time_bins; i++) {
        spec->data[i] = (float*)malloc(sizeof(float) * spec->freq_bins);
    }
    
    // Compute STFT
    float* window_buffer = (float*)malloc(sizeof(float) * window_size);
    FFTResult fft_result;
    
    for (uint32_t t = 0; t < spec->time_bins; t++) {
        uint32_t start = t * hop_size;
        
        // Extract window
        for (uint32_t i = 0; i < window_size; i++) {
            window_buffer[i] = signal[start + i];
        }
        
        // Apply window function
        window_apply(window_buffer, window_size, WINDOW_HANNING);
        
        // Compute FFT
        fft_real(window_buffer, window_size, &fft_result);
        
        // Store magnitude spectrum
        for (uint32_t f = 0; f < spec->freq_bins; f++) {
            spec->data[t][f] = fft_result.magnitude[f];
        }
        
        // Cleanup
        free(fft_result.data);
        free(fft_result.magnitude);
        free(fft_result.phase);
        free(fft_result.power_spectrum);
        
        if (t % 10 == 0) yield();
    }
    
    free(window_buffer);
    
    Serial.printf("[DSP] Spectrogram computed: %dx%d\n", spec->time_bins, spec->freq_bins);
}

// =====================================================================================================================
// MFCC Computation
// =====================================================================================================================

float hz_to_mel(float hz) {
    return 2595.0f * log10(1.0f + hz / 700.0f);
}

float mel_to_hz(float mel) {
    return 700.0f * (pow(10.0f, mel / 2595.0f) - 1.0f);
}

void mfcc_compute(const float* signal, uint32_t signal_length, float sample_rate,
                 uint32_t num_coeffs, MFCC* mfcc) {
    // Compute mel-spectrogram first
    uint32_t window_size = 512;
    uint32_t hop_size = 256;
    uint32_t num_mel_bins = 40;
    
    Spectrogram spec;
    spectrogram_compute(signal, signal_length, sample_rate, window_size, hop_size, &spec);
    
    mfcc->num_frames = spec.time_bins;
    mfcc->num_coeffs = num_coeffs;
    
    // Allocate MFCC matrix
    mfcc->coefficients = (float**)malloc(sizeof(float*) * mfcc->num_frames);
    for (uint32_t i = 0; i < mfcc->num_frames; i++) {
        mfcc->coefficients[i] = (float*)malloc(sizeof(float) * num_coeffs);
    }
    
    // Mel filter banks
    float** mel_filters = (float**)malloc(sizeof(float*) * num_mel_bins);
    for (uint32_t i = 0; i < num_mel_bins; i++) {
        mel_filters[i] = (float*)malloc(sizeof(float) * spec.freq_bins);
        memset(mel_filters[i], 0, sizeof(float) * spec.freq_bins);
    }
    
    // Create triangular mel filters
    float min_mel = hz_to_mel(0);
    float max_mel = hz_to_mel(sample_rate / 2.0f);
    
    for (uint32_t m = 0; m < num_mel_bins; m++) {
        float center_mel = min_mel + (max_mel - min_mel) * (m + 1) / (num_mel_bins + 1);
        float center_hz = mel_to_hz(center_mel);
        
        // Triangular filter (simplified)
        for (uint32_t k = 0; k < spec.freq_bins; k++) {
            float freq = k * sample_rate / window_size;
            float mel_freq = hz_to_mel(freq);
            
            if (fabs(mel_freq - center_mel) < 100.0f) {
                mel_filters[m][k] = 1.0f - fabs(mel_freq - center_mel) / 100.0f;
            }
        }
    }
    
    // Apply mel filters and compute DCT
    for (uint32_t t = 0; t < mfcc->num_frames; t++) {
        float* mel_spectrum = (float*)malloc(sizeof(float) * num_mel_bins);
        
        // Apply mel filters
        for (uint32_t m = 0; m < num_mel_bins; m++) {
            mel_spectrum[m] = 0.0f;
            for (uint32_t k = 0; k < spec.freq_bins; k++) {
                mel_spectrum[m] += spec.data[t][k] * mel_filters[m][k];
            }
            mel_spectrum[m] = log(mel_spectrum[m] + 1e-10f);
        }
        
        // Discrete Cosine Transform
        for (uint32_t i = 0; i < num_coeffs; i++) {
            mfcc->coefficients[t][i] = 0.0f;
            for (uint32_t m = 0; m < num_mel_bins; m++) {
                mfcc->coefficients[t][i] += mel_spectrum[m] *
                    cos(PI * i * (m + 0.5f) / num_mel_bins);
            }
        }
        
        free(mel_spectrum);
        if (t % 10 == 0) yield();
    }
    
    // Cleanup
    for (uint32_t i = 0; i < num_mel_bins; i++) {
        free(mel_filters[i]);
    }
    free(mel_filters);
    
    Serial.printf("[DSP] MFCC computed: %d frames x %d coeffs\n",
                  mfcc->num_frames, mfcc->num_coeffs);
}

// =====================================================================================================================
// Wavelet Transform (Haar)
// =====================================================================================================================

void wavelet_dwt_haar(const float* signal, uint32_t length, WaveletTransform* wt) {
    wt->type = WAVELET_HAAR;
    wt->levels = (uint32_t)log2(length);
    wt->level_sizes = (uint32_t*)malloc(sizeof(uint32_t) * wt->levels);
    
    // Allocate coefficient storage
    wt->coefficients = (float**)malloc(sizeof(float*) * wt->levels);
    
    float* temp = (float*)malloc(sizeof(float) * length);
    memcpy(temp, signal, sizeof(float) * length);
    
    uint32_t current_length = length;
    
    for (uint32_t level = 0; level < wt->levels; level++) {
        uint32_t half_length = current_length / 2;
        wt->level_sizes[level] = half_length;
        wt->coefficients[level] = (float*)malloc(sizeof(float) * current_length);
        
        // Compute approximation and detail coefficients
        for (uint32_t i = 0; i < half_length; i++) {
            float a = temp[2 * i];
            float b = temp[2 * i + 1];
            
            wt->coefficients[level][i] = (a + b) / sqrt(2.0f);  // Approximation
            wt->coefficients[level][half_length + i] = (a - b) / sqrt(2.0f);  // Detail
        }
        
        // Update for next level
        memcpy(temp, wt->coefficients[level], sizeof(float) * half_length);
        current_length = half_length;
        
        if (level % 2 == 0) yield();
    }
    
    free(temp);
    Serial.printf("[DSP] Wavelet transform computed, %d levels\n", wt->levels);
}

// =====================================================================================================================
// Adaptive LMS Filter
// =====================================================================================================================

void adaptive_lms_init(AdaptiveFilter* filter, uint32_t num_taps, float step_size) {
    filter->num_taps = num_taps;
    filter->step_size = step_size;
    filter->weights = (float*)malloc(sizeof(float) * num_taps);
    filter->input_buffer = (float*)malloc(sizeof(float) * num_taps);
    
    memset(filter->weights, 0, sizeof(float) * num_taps);
    memset(filter->input_buffer, 0, sizeof(float) * num_taps);
}

float adaptive_lms_process(AdaptiveFilter* filter, float input, float desired) {
    // Shift input buffer
    for (int32_t i = filter->num_taps - 1; i > 0; i--) {
        filter->input_buffer[i] = filter->input_buffer[i - 1];
    }
    filter->input_buffer[0] = input;
    
    // Compute output
    float output = 0.0f;
    for (uint32_t i = 0; i < filter->num_taps; i++) {
        output += filter->weights[i] * filter->input_buffer[i];
    }
    
    // Compute error
    filter->error_signal = desired - output;
    
    // Update weights (LMS algorithm)
    for (uint32_t i = 0; i < filter->num_taps; i++) {
        filter->weights[i] += filter->step_size * filter->error_signal *
                             filter->input_buffer[i];
    }
    
    return output;
}

// =====================================================================================================================
// DSP Initialization
// =====================================================================================================================

void signal_processing_init() {
    Serial.println("[DSP] Initializing signal processing engine...");
    
    // Initialize FFT result
    g_fft_result.data = NULL;
    g_fft_result.size = 0;
    
    Serial.println("[DSP] Signal processing engine initialized");
}

// =====================================================================================================================
// End of signal_processing.cpp
// Lines: ~1100
// =====================================================================================================================
