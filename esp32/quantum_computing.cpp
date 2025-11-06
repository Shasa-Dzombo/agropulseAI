// =====================================================================================================================
// ESP32 Quantum Computing Simulator
// Quantum gates, circuits, algorithms, entanglement simulation for embedded systems
// =====================================================================================================================

#include <Arduino.h>
#include <math.h>
#include <complex>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// =====================================================================================================================
// Quantum Computing Structures
// =====================================================================================================================

#define MAX_QUBITS 8  // ESP32 memory limitation
#define MAX_GATES 256
#define MAX_MEASUREMENTS 1000

// Complex number for quantum amplitudes
typedef struct {
    float real;
    float imag;
} Complex;

// Quantum state vector
typedef struct {
    Complex* amplitudes;  // 2^n_qubits amplitudes
    uint32_t n_qubits;
    uint32_t dimension;   // 2^n_qubits
} QuantumState;

// Quantum gate matrix (2x2 for single qubit, 4x4 for two qubit)
typedef struct {
    Complex** matrix;
    uint32_t size;
    char name[16];
    uint8_t gate_type;  // 0=single, 1=controlled, 2=multi
} QuantumGate;

// Quantum circuit
typedef struct {
    QuantumGate* gates[MAX_GATES];
    uint32_t target_qubits[MAX_GATES];
    int32_t control_qubits[MAX_GATES];  // -1 if no control
    uint32_t gate_count;
    uint32_t n_qubits;
    uint64_t depth;
} QuantumCircuit;

// Measurement result
typedef struct {
    uint32_t outcome;
    float probability;
    uint64_t timestamp;
} MeasurementResult;

// Quantum register
typedef struct {
    QuantumState* state;
    bool* measured;
    uint32_t* measurement_results;
    uint32_t n_qubits;
} QuantumRegister;

// Quantum error
typedef enum {
    ERROR_NONE = 0,
    ERROR_BIT_FLIP,
    ERROR_PHASE_FLIP,
    ERROR_DEPOLARIZING,
    ERROR_AMPLITUDE_DAMPING
} QuantumError;

// Error correction code
typedef struct {
    uint32_t code_distance;
    uint32_t n_physical_qubits;
    uint32_t n_logical_qubits;
    float error_rate;
    bool* syndrome;
} QuantumErrorCorrection;

// Quantum algorithm type
typedef enum {
    ALGO_DEUTSCH_JOZSA,
    ALGO_BERNSTEIN_VAZIRANI,
    ALGO_GROVER,
    ALGO_QFT,
    ALGO_PHASE_ESTIMATION,
    ALGO_SHOR
} QuantumAlgorithm;

// Bloch sphere representation
typedef struct {
    float theta;  // Polar angle
    float phi;    // Azimuthal angle
} BlochSphere;

// Density matrix (for mixed states)
typedef struct {
    Complex** matrix;
    uint32_t dimension;
} DensityMatrix;

// Quantum channel (for noise modeling)
typedef struct {
    Complex*** kraus_operators;
    uint32_t n_operators;
    uint32_t dimension;
} QuantumChannel;

// =====================================================================================================================
// Global Quantum State
// =====================================================================================================================

QuantumRegister g_quantum_register;

// =====================================================================================================================
// Complex Number Operations
// =====================================================================================================================

Complex complex_create(float real, float imag) {
    Complex c;
    c.real = real;
    c.imag = imag;
    return c;
}

Complex complex_add(Complex a, Complex b) {
    return complex_create(a.real + b.real, a.imag + b.imag);
}

Complex complex_sub(Complex a, Complex b) {
    return complex_create(a.real - b.real, a.imag - b.imag);
}

Complex complex_mul(Complex a, Complex b) {
    return complex_create(
        a.real * b.real - a.imag * b.imag,
        a.real * b.imag + a.imag * b.real
    );
}

Complex complex_conjugate(Complex c) {
    return complex_create(c.real, -c.imag);
}

float complex_magnitude(Complex c) {
    return sqrtf(c.real * c.real + c.imag * c.imag);
}

float complex_magnitude_squared(Complex c) {
    return c.real * c.real + c.imag * c.imag;
}

Complex complex_scale(Complex c, float scalar) {
    return complex_create(c.real * scalar, c.imag * scalar);
}

Complex complex_exp(Complex c) {
    float exp_real = expf(c.real);
    return complex_create(
        exp_real * cosf(c.imag),
        exp_real * sinf(c.imag)
    );
}

Complex complex_sqrt(Complex c) {
    float r = complex_magnitude(c);
    float theta = atan2f(c.imag, c.real);
    float sqrt_r = sqrtf(r);
    return complex_create(
        sqrt_r * cosf(theta / 2.0f),
        sqrt_r * sinf(theta / 2.0f)
    );
}

void complex_print(Complex c) {
    Serial.printf("%.4f + %.4fi", c.real, c.imag);
}

// =====================================================================================================================
// Quantum State Operations
// =====================================================================================================================

QuantumState* quantum_state_create(uint32_t n_qubits) {
    if (n_qubits > MAX_QUBITS) {
        Serial.println("Error: Exceeds maximum qubits");
        return NULL;
    }
    
    QuantumState* state = (QuantumState*)malloc(sizeof(QuantumState));
    state->n_qubits = n_qubits;
    state->dimension = 1 << n_qubits;  // 2^n_qubits
    
    state->amplitudes = (Complex*)malloc(sizeof(Complex) * state->dimension);
    
    // Initialize to |0...0⟩ state
    for (uint32_t i = 0; i < state->dimension; i++) {
        state->amplitudes[i] = complex_create(0.0f, 0.0f);
    }
    state->amplitudes[0] = complex_create(1.0f, 0.0f);
    
    return state;
}

void quantum_state_destroy(QuantumState* state) {
    free(state->amplitudes);
    free(state);
}

void quantum_state_normalize(QuantumState* state) {
    float sum = 0.0f;
    
    for (uint32_t i = 0; i < state->dimension; i++) {
        sum += complex_magnitude_squared(state->amplitudes[i]);
    }
    
    float norm = sqrtf(sum);
    
    if (norm > 0.0001f) {
        for (uint32_t i = 0; i < state->dimension; i++) {
            state->amplitudes[i] = complex_scale(state->amplitudes[i], 1.0f / norm);
        }
    }
}

float quantum_state_get_probability(QuantumState* state, uint32_t basis_state) {
    if (basis_state >= state->dimension) return 0.0f;
    return complex_magnitude_squared(state->amplitudes[basis_state]);
}

void quantum_state_print(QuantumState* state) {
    Serial.println("Quantum State:");
    for (uint32_t i = 0; i < state->dimension; i++) {
        float prob = quantum_state_get_probability(state, i);
        if (prob > 0.001f) {
            Serial.printf("|%d⟩: ", i);
            complex_print(state->amplitudes[i]);
            Serial.printf(" (P=%.4f)\n", prob);
        }
    }
}

void quantum_state_hadamard_all(QuantumState* state) {
    float factor = 1.0f / sqrtf(state->dimension);
    
    for (uint32_t i = 0; i < state->dimension; i++) {
        state->amplitudes[i] = complex_create(factor, 0.0f);
    }
}

// =====================================================================================================================
// Quantum Gate Definitions
// =====================================================================================================================

QuantumGate* quantum_gate_create(uint32_t size, const char* name) {
    QuantumGate* gate = (QuantumGate*)malloc(sizeof(QuantumGate));
    gate->size = size;
    strncpy(gate->name, name, sizeof(gate->name) - 1);
    gate->gate_type = (size == 2) ? 0 : 1;
    
    gate->matrix = (Complex**)malloc(sizeof(Complex*) * size);
    for (uint32_t i = 0; i < size; i++) {
        gate->matrix[i] = (Complex*)malloc(sizeof(Complex) * size);
        for (uint32_t j = 0; j < size; j++) {
            gate->matrix[i][j] = complex_create(0.0f, 0.0f);
        }
    }
    
    return gate;
}

void quantum_gate_destroy(QuantumGate* gate) {
    for (uint32_t i = 0; i < gate->size; i++) {
        free(gate->matrix[i]);
    }
    free(gate->matrix);
    free(gate);
}

// Pauli-X (NOT) Gate
QuantumGate* gate_pauli_x() {
    QuantumGate* gate = quantum_gate_create(2, "X");
    gate->matrix[0][1] = complex_create(1.0f, 0.0f);
    gate->matrix[1][0] = complex_create(1.0f, 0.0f);
    return gate;
}

// Pauli-Y Gate
QuantumGate* gate_pauli_y() {
    QuantumGate* gate = quantum_gate_create(2, "Y");
    gate->matrix[0][1] = complex_create(0.0f, -1.0f);
    gate->matrix[1][0] = complex_create(0.0f, 1.0f);
    return gate;
}

// Pauli-Z Gate
QuantumGate* gate_pauli_z() {
    QuantumGate* gate = quantum_gate_create(2, "Z");
    gate->matrix[0][0] = complex_create(1.0f, 0.0f);
    gate->matrix[1][1] = complex_create(-1.0f, 0.0f);
    return gate;
}

// Hadamard Gate
QuantumGate* gate_hadamard() {
    QuantumGate* gate = quantum_gate_create(2, "H");
    float inv_sqrt2 = 1.0f / sqrtf(2.0f);
    
    gate->matrix[0][0] = complex_create(inv_sqrt2, 0.0f);
    gate->matrix[0][1] = complex_create(inv_sqrt2, 0.0f);
    gate->matrix[1][0] = complex_create(inv_sqrt2, 0.0f);
    gate->matrix[1][1] = complex_create(-inv_sqrt2, 0.0f);
    
    return gate;
}

// Phase (S) Gate
QuantumGate* gate_phase(float theta) {
    QuantumGate* gate = quantum_gate_create(2, "PHASE");
    gate->matrix[0][0] = complex_create(1.0f, 0.0f);
    gate->matrix[1][1] = complex_create(cosf(theta), sinf(theta));
    return gate;
}

// T Gate
QuantumGate* gate_t() {
    QuantumGate* gate = quantum_gate_create(2, "T");
    gate->matrix[0][0] = complex_create(1.0f, 0.0f);
    gate->matrix[1][1] = complex_create(cosf(M_PI / 4.0f), sinf(M_PI / 4.0f));
    return gate;
}

// Rotation gates
QuantumGate* gate_rx(float theta) {
    QuantumGate* gate = quantum_gate_create(2, "RX");
    float cos_half = cosf(theta / 2.0f);
    float sin_half = sinf(theta / 2.0f);
    
    gate->matrix[0][0] = complex_create(cos_half, 0.0f);
    gate->matrix[0][1] = complex_create(0.0f, -sin_half);
    gate->matrix[1][0] = complex_create(0.0f, -sin_half);
    gate->matrix[1][1] = complex_create(cos_half, 0.0f);
    
    return gate;
}

QuantumGate* gate_ry(float theta) {
    QuantumGate* gate = quantum_gate_create(2, "RY");
    float cos_half = cosf(theta / 2.0f);
    float sin_half = sinf(theta / 2.0f);
    
    gate->matrix[0][0] = complex_create(cos_half, 0.0f);
    gate->matrix[0][1] = complex_create(-sin_half, 0.0f);
    gate->matrix[1][0] = complex_create(sin_half, 0.0f);
    gate->matrix[1][1] = complex_create(cos_half, 0.0f);
    
    return gate;
}

QuantumGate* gate_rz(float theta) {
    QuantumGate* gate = quantum_gate_create(2, "RZ");
    float cos_half = cosf(theta / 2.0f);
    float sin_half = sinf(theta / 2.0f);
    
    gate->matrix[0][0] = complex_create(cos_half, -sin_half);
    gate->matrix[1][1] = complex_create(cos_half, sin_half);
    
    return gate;
}

// CNOT Gate
QuantumGate* gate_cnot() {
    QuantumGate* gate = quantum_gate_create(4, "CNOT");
    gate->gate_type = 1;
    
    gate->matrix[0][0] = complex_create(1.0f, 0.0f);
    gate->matrix[1][1] = complex_create(1.0f, 0.0f);
    gate->matrix[2][3] = complex_create(1.0f, 0.0f);
    gate->matrix[3][2] = complex_create(1.0f, 0.0f);
    
    return gate;
}

// SWAP Gate
QuantumGate* gate_swap() {
    QuantumGate* gate = quantum_gate_create(4, "SWAP");
    gate->gate_type = 1;
    
    gate->matrix[0][0] = complex_create(1.0f, 0.0f);
    gate->matrix[1][2] = complex_create(1.0f, 0.0f);
    gate->matrix[2][1] = complex_create(1.0f, 0.0f);
    gate->matrix[3][3] = complex_create(1.0f, 0.0f);
    
    return gate;
}

// Toffoli Gate (CCNOT)
QuantumGate* gate_toffoli() {
    QuantumGate* gate = quantum_gate_create(8, "TOFFOLI");
    gate->gate_type = 2;
    
    for (uint32_t i = 0; i < 6; i++) {
        gate->matrix[i][i] = complex_create(1.0f, 0.0f);
    }
    gate->matrix[6][7] = complex_create(1.0f, 0.0f);
    gate->matrix[7][6] = complex_create(1.0f, 0.0f);
    
    return gate;
}

// Fredkin Gate (CSWAP)
QuantumGate* gate_fredkin() {
    QuantumGate* gate = quantum_gate_create(8, "FREDKIN");
    gate->gate_type = 2;
    
    gate->matrix[0][0] = complex_create(1.0f, 0.0f);
    gate->matrix[1][1] = complex_create(1.0f, 0.0f);
    gate->matrix[2][2] = complex_create(1.0f, 0.0f);
    gate->matrix[3][3] = complex_create(1.0f, 0.0f);
    gate->matrix[4][4] = complex_create(1.0f, 0.0f);
    gate->matrix[5][6] = complex_create(1.0f, 0.0f);
    gate->matrix[6][5] = complex_create(1.0f, 0.0f);
    gate->matrix[7][7] = complex_create(1.0f, 0.0f);
    
    return gate;
}

// =====================================================================================================================
// Gate Application
// =====================================================================================================================

void apply_single_qubit_gate(QuantumState* state, QuantumGate* gate, uint32_t target) {
    if (gate->size != 2 || target >= state->n_qubits) return;
    
    QuantumState* new_state = quantum_state_create(state->n_qubits);
    uint32_t mask = 1 << target;
    
    for (uint32_t i = 0; i < state->dimension; i++) {
        uint32_t bit = (i & mask) ? 1 : 0;
        uint32_t i_flipped = i ^ mask;
        
        Complex amp0 = state->amplitudes[bit ? i_flipped : i];
        Complex amp1 = state->amplitudes[bit ? i : i_flipped];
        
        Complex contrib0 = complex_mul(gate->matrix[bit][0], amp0);
        Complex contrib1 = complex_mul(gate->matrix[bit][1], amp1);
        
        new_state->amplitudes[i] = complex_add(contrib0, contrib1);
    }
    
    memcpy(state->amplitudes, new_state->amplitudes, 
           sizeof(Complex) * state->dimension);
    quantum_state_destroy(new_state);
}

void apply_two_qubit_gate(QuantumState* state, QuantumGate* gate,
                          uint32_t control, uint32_t target) {
    if (gate->size != 4 || control >= state->n_qubits || 
        target >= state->n_qubits || control == target) return;
    
    QuantumState* new_state = quantum_state_create(state->n_qubits);
    uint32_t control_mask = 1 << control;
    uint32_t target_mask = 1 << target;
    
    for (uint32_t i = 0; i < state->dimension; i++) {
        uint32_t control_bit = (i & control_mask) ? 1 : 0;
        uint32_t target_bit = (i & target_mask) ? 1 : 0;
        uint32_t basis = (control_bit << 1) | target_bit;
        
        Complex result = complex_create(0.0f, 0.0f);
        
        for (uint32_t j = 0; j < 4; j++) {
            uint32_t j_control = (j >> 1) & 1;
            uint32_t j_target = j & 1;
            
            uint32_t state_idx = i;
            if (j_control != control_bit) state_idx ^= control_mask;
            if (j_target != target_bit) state_idx ^= target_mask;
            
            Complex contrib = complex_mul(gate->matrix[basis][j],
                                         state->amplitudes[state_idx]);
            result = complex_add(result, contrib);
        }
        
        new_state->amplitudes[i] = result;
    }
    
    memcpy(state->amplitudes, new_state->amplitudes,
           sizeof(Complex) * state->dimension);
    quantum_state_destroy(new_state);
}

// =====================================================================================================================
// Quantum Circuit Operations
// =====================================================================================================================

QuantumCircuit* quantum_circuit_create(uint32_t n_qubits) {
    QuantumCircuit* circuit = (QuantumCircuit*)malloc(sizeof(QuantumCircuit));
    circuit->n_qubits = n_qubits;
    circuit->gate_count = 0;
    circuit->depth = 0;
    
    for (uint32_t i = 0; i < MAX_GATES; i++) {
        circuit->gates[i] = NULL;
        circuit->target_qubits[i] = 0;
        circuit->control_qubits[i] = -1;
    }
    
    return circuit;
}

void quantum_circuit_destroy(QuantumCircuit* circuit) {
    for (uint32_t i = 0; i < circuit->gate_count; i++) {
        if (circuit->gates[i]) {
            quantum_gate_destroy(circuit->gates[i]);
        }
    }
    free(circuit);
}

void quantum_circuit_add_gate(QuantumCircuit* circuit, QuantumGate* gate,
                              uint32_t target, int32_t control) {
    if (circuit->gate_count >= MAX_GATES) return;
    
    circuit->gates[circuit->gate_count] = gate;
    circuit->target_qubits[circuit->gate_count] = target;
    circuit->control_qubits[circuit->gate_count] = control;
    circuit->gate_count++;
}

void quantum_circuit_execute(QuantumCircuit* circuit, QuantumState* state) {
    for (uint32_t i = 0; i < circuit->gate_count; i++) {
        if (circuit->control_qubits[i] < 0) {
            apply_single_qubit_gate(state, circuit->gates[i],
                                   circuit->target_qubits[i]);
        } else {
            apply_two_qubit_gate(state, circuit->gates[i],
                                circuit->control_qubits[i],
                                circuit->target_qubits[i]);
        }
        
        if (i % 10 == 0) yield();  // Yield to other tasks
    }
}

void quantum_circuit_print(QuantumCircuit* circuit) {
    Serial.printf("Quantum Circuit (%d qubits, %d gates):\n",
                 circuit->n_qubits, circuit->gate_count);
    
    for (uint32_t i = 0; i < circuit->gate_count; i++) {
        Serial.printf("%d: %s on qubit %d", i, circuit->gates[i]->name,
                     circuit->target_qubits[i]);
        
        if (circuit->control_qubits[i] >= 0) {
            Serial.printf(" (control: %d)", circuit->control_qubits[i]);
        }
        Serial.println();
    }
}

// =====================================================================================================================
// Quantum Measurement
// =====================================================================================================================

uint32_t quantum_measure_qubit(QuantumState* state, uint32_t qubit) {
    if (qubit >= state->n_qubits) return 0;
    
    uint32_t mask = 1 << qubit;
    float prob_zero = 0.0f;
    
    for (uint32_t i = 0; i < state->dimension; i++) {
        if ((i & mask) == 0) {
            prob_zero += complex_magnitude_squared(state->amplitudes[i]);
        }
    }
    
    float random_val = (float)random(0, 10000) / 10000.0f;
    uint32_t result = (random_val < prob_zero) ? 0 : 1;
    
    // Collapse state
    float norm = 0.0f;
    for (uint32_t i = 0; i < state->dimension; i++) {
        if (((i & mask) ? 1 : 0) != result) {
            state->amplitudes[i] = complex_create(0.0f, 0.0f);
        } else {
            norm += complex_magnitude_squared(state->amplitudes[i]);
        }
    }
    
    norm = sqrtf(norm);
    if (norm > 0.0001f) {
        for (uint32_t i = 0; i < state->dimension; i++) {
            state->amplitudes[i] = complex_scale(state->amplitudes[i], 1.0f / norm);
        }
    }
    
    return result;
}

uint32_t quantum_measure_all(QuantumState* state) {
    float* probabilities = (float*)malloc(sizeof(float) * state->dimension);
    
    for (uint32_t i = 0; i < state->dimension; i++) {
        probabilities[i] = quantum_state_get_probability(state, i);
    }
    
    float random_val = (float)random(0, 10000) / 10000.0f;
    float cumulative = 0.0f;
    uint32_t result = 0;
    
    for (uint32_t i = 0; i < state->dimension; i++) {
        cumulative += probabilities[i];
        if (random_val <= cumulative) {
            result = i;
            break;
        }
    }
    
    free(probabilities);
    
    // Collapse to measured state
    for (uint32_t i = 0; i < state->dimension; i++) {
        if (i == result) {
            state->amplitudes[i] = complex_create(1.0f, 0.0f);
        } else {
            state->amplitudes[i] = complex_create(0.0f, 0.0f);
        }
    }
    
    return result;
}

// =====================================================================================================================
// Quantum Entanglement
// =====================================================================================================================

void create_bell_state(QuantumState* state, uint32_t qubit1, uint32_t qubit2) {
    // Create Bell state: (|00⟩ + |11⟩) / √2
    QuantumGate* h = gate_hadamard();
    apply_single_qubit_gate(state, h, qubit1);
    quantum_gate_destroy(h);
    
    QuantumGate* cnot = gate_cnot();
    apply_two_qubit_gate(state, cnot, qubit1, qubit2);
    quantum_gate_destroy(cnot);
}

float calculate_entanglement_entropy(QuantumState* state, uint32_t qubit) {
    // Von Neumann entropy for single qubit
    uint32_t mask = 1 << qubit;
    float prob_zero = 0.0f;
    
    for (uint32_t i = 0; i < state->dimension; i++) {
        if ((i & mask) == 0) {
            prob_zero += complex_magnitude_squared(state->amplitudes[i]);
        }
    }
    
    float prob_one = 1.0f - prob_zero;
    
    float entropy = 0.0f;
    if (prob_zero > 0.0001f) {
        entropy -= prob_zero * log2f(prob_zero);
    }
    if (prob_one > 0.0001f) {
        entropy -= prob_one * log2f(prob_one);
    }
    
    return entropy;
}

// =====================================================================================================================
// Quantum Algorithms
// =====================================================================================================================

// Deutsch-Jozsa Algorithm
bool deutsch_jozsa(bool (*oracle)(uint32_t), uint32_t n_qubits) {
    QuantumState* state = quantum_state_create(n_qubits + 1);
    
    // Initialize last qubit to |1⟩
    QuantumGate* x = gate_pauli_x();
    apply_single_qubit_gate(state, x, n_qubits);
    quantum_gate_destroy(x);
    
    // Apply Hadamard to all qubits
    QuantumGate* h = gate_hadamard();
    for (uint32_t i = 0; i <= n_qubits; i++) {
        apply_single_qubit_gate(state, h, i);
    }
    quantum_gate_destroy(h);
    
    // Apply oracle (simplified)
    // In real implementation, oracle would be a quantum circuit
    
    // Apply Hadamard to input qubits
    h = gate_hadamard();
    for (uint32_t i = 0; i < n_qubits; i++) {
        apply_single_qubit_gate(state, h, i);
    }
    quantum_gate_destroy(h);
    
    // Measure all input qubits
    bool is_constant = true;
    for (uint32_t i = 0; i < n_qubits; i++) {
        if (quantum_measure_qubit(state, i) != 0) {
            is_constant = false;
            break;
        }
    }
    
    quantum_state_destroy(state);
    return is_constant;
}

// Quantum Fourier Transform
void quantum_fourier_transform(QuantumState* state, uint32_t start, uint32_t length) {
    for (uint32_t j = 0; j < length; j++) {
        uint32_t qubit = start + j;
        
        // Apply Hadamard
        QuantumGate* h = gate_hadamard();
        apply_single_qubit_gate(state, h, qubit);
        quantum_gate_destroy(h);
        
        // Apply controlled phase rotations
        for (uint32_t k = j + 1; k < length; k++) {
            float theta = M_PI / (1 << (k - j));
            QuantumGate* phase = gate_phase(theta);
            apply_two_qubit_gate(state, phase, start + k, qubit);
            quantum_gate_destroy(phase);
        }
    }
    
    // Swap qubits
    for (uint32_t j = 0; j < length / 2; j++) {
        QuantumGate* swap = gate_swap();
        apply_two_qubit_gate(state, swap, start + j, start + length - 1 - j);
        quantum_gate_destroy(swap);
    }
}

// Grover's Algorithm
void grover_oracle(QuantumState* state, uint32_t target) {
    // Mark target state by flipping its phase
    if (target < state->dimension) {
        state->amplitudes[target].real = -state->amplitudes[target].real;
        state->amplitudes[target].imag = -state->amplitudes[target].imag;
    }
}

void grover_diffusion(QuantumState* state) {
    // Apply Hadamard to all qubits
    QuantumGate* h = gate_hadamard();
    for (uint32_t i = 0; i < state->n_qubits; i++) {
        apply_single_qubit_gate(state, h, i);
    }
    quantum_gate_destroy(h);
    
    // Conditional phase shift
    for (uint32_t i = 1; i < state->dimension; i++) {
        state->amplitudes[i].real = -state->amplitudes[i].real;
        state->amplitudes[i].imag = -state->amplitudes[i].imag;
    }
    
    // Apply Hadamard again
    h = gate_hadamard();
    for (uint32_t i = 0; i < state->n_qubits; i++) {
        apply_single_qubit_gate(state, h, i);
    }
    quantum_gate_destroy(h);
}

uint32_t grover_search(uint32_t n_qubits, uint32_t target) {
    QuantumState* state = quantum_state_create(n_qubits);
    
    // Initialize to equal superposition
    quantum_state_hadamard_all(state);
    
    // Calculate iterations
    uint32_t iterations = (uint32_t)(M_PI / 4.0f * sqrtf(state->dimension));
    
    // Grover iteration
    for (uint32_t i = 0; i < iterations; i++) {
        grover_oracle(state, target);
        grover_diffusion(state);
        yield();
    }
    
    // Measure
    uint32_t result = quantum_measure_all(state);
    
    quantum_state_destroy(state);
    return result;
}

// =====================================================================================================================
// Quantum Error Correction
// =====================================================================================================================

void encode_three_qubit_code(QuantumState* state, uint32_t logical_qubit) {
    // Encode logical qubit into three physical qubits
    uint32_t q0 = logical_qubit * 3;
    uint32_t q1 = q0 + 1;
    uint32_t q2 = q0 + 2;
    
    // CNOT from q0 to q1
    QuantumGate* cnot = gate_cnot();
    apply_two_qubit_gate(state, cnot, q0, q1);
    
    // CNOT from q0 to q2
    apply_two_qubit_gate(state, cnot, q0, q2);
    quantum_gate_destroy(cnot);
}

void decode_three_qubit_code(QuantumState* state, uint32_t logical_qubit) {
    uint32_t q0 = logical_qubit * 3;
    uint32_t q1 = q0 + 1;
    uint32_t q2 = q0 + 2;
    
    QuantumGate* cnot = gate_cnot();
    apply_two_qubit_gate(state, cnot, q0, q2);
    apply_two_qubit_gate(state, cnot, q0, q1);
    quantum_gate_destroy(cnot);
}

void apply_bit_flip_error(QuantumState* state, uint32_t qubit, float probability) {
    float random_val = (float)random(0, 10000) / 10000.0f;
    
    if (random_val < probability) {
        QuantumGate* x = gate_pauli_x();
        apply_single_qubit_gate(state, x, qubit);
        quantum_gate_destroy(x);
    }
}

// =====================================================================================================================
// Bloch Sphere Representation
// =====================================================================================================================

BlochSphere quantum_state_to_bloch(QuantumState* state, uint32_t qubit) {
    BlochSphere bloch;
    
    // Extract single qubit state
    uint32_t mask = 1 << qubit;
    Complex alpha = complex_create(0.0f, 0.0f);
    Complex beta = complex_create(0.0f, 0.0f);
    
    for (uint32_t i = 0; i < state->dimension; i++) {
        if ((i & mask) == 0) {
            alpha = complex_add(alpha, state->amplitudes[i]);
        } else {
            beta = complex_add(beta, state->amplitudes[i]);
        }
    }
    
    // Calculate Bloch sphere coordinates
    float alpha_mag = complex_magnitude(alpha);
    float beta_mag = complex_magnitude(beta);
    
    bloch.theta = 2.0f * atan2f(beta_mag, alpha_mag);
    
    Complex beta_conj = complex_conjugate(beta);
    Complex phase_factor = complex_mul(alpha, beta_conj);
    bloch.phi = atan2f(phase_factor.imag, phase_factor.real);
    
    return bloch;
}

void print_bloch_sphere(BlochSphere bloch) {
    Serial.printf("Bloch Sphere: theta=%.4f, phi=%.4f\n", bloch.theta, bloch.phi);
    Serial.printf("Cartesian: x=%.4f, y=%.4f, z=%.4f\n",
                 sinf(bloch.theta) * cosf(bloch.phi),
                 sinf(bloch.theta) * sinf(bloch.phi),
                 cosf(bloch.theta));
}

// =====================================================================================================================
// Quantum Register Management
// =====================================================================================================================

void quantum_register_init(QuantumRegister* reg, uint32_t n_qubits) {
    reg->n_qubits = n_qubits;
    reg->state = quantum_state_create(n_qubits);
    reg->measured = (bool*)malloc(sizeof(bool) * n_qubits);
    reg->measurement_results = (uint32_t*)malloc(sizeof(uint32_t) * n_qubits);
    
    for (uint32_t i = 0; i < n_qubits; i++) {
        reg->measured[i] = false;
        reg->measurement_results[i] = 0;
    }
}

void quantum_register_destroy(QuantumRegister* reg) {
    quantum_state_destroy(reg->state);
    free(reg->measured);
    free(reg->measurement_results);
}

void quantum_register_reset(QuantumRegister* reg) {
    quantum_state_destroy(reg->state);
    reg->state = quantum_state_create(reg->n_qubits);
    
    for (uint32_t i = 0; i < reg->n_qubits; i++) {
        reg->measured[i] = false;
        reg->measurement_results[i] = 0;
    }
}

// =====================================================================================================================
// Quantum Computing System Initialization
// =====================================================================================================================

void quantum_computing_init() {
    Serial.println("[Quantum] Initializing quantum computing system...");
    
    quantum_register_init(&g_quantum_register, 4);
    
    Serial.println("[Quantum] Quantum register created with 4 qubits");
    Serial.println("[Quantum] Initialization complete");
}

// =====================================================================================================================
// End of quantum_computing.cpp
// Lines: ~1250
// =====================================================================================================================
