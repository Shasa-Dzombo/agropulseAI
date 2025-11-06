// =====================================================================================================================
// AgroPulse Firmware - Quantum Computing Engine (C++)
// Quantum simulation, qubit operations, quantum gates, entanglement, quantum algorithms
// =====================================================================================================================

#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>
#include <complex>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Complex number operations for quantum states
typedef struct ComplexNumber {
    double real;
    double imag;
} ComplexNumber;

// Quantum state representation
typedef struct QuantumState {
    ComplexNumber* amplitudes;
    uint32_t num_qubits;
    uint32_t dimension; // 2^num_qubits
} QuantumState;

// Quantum gate matrix
typedef struct QuantumGate {
    ComplexNumber** matrix;
    uint32_t size;
    char name[32];
} QuantumGate;

// Quantum circuit
typedef struct QuantumCircuit {
    QuantumGate** gates;
    uint32_t* target_qubits;
    uint32_t* control_qubits;
    uint32_t gate_count;
    uint32_t capacity;
    uint32_t num_qubits;
} QuantumCircuit;

// Quantum register
typedef struct QuantumRegister {
    QuantumState* state;
    uint32_t num_qubits;
    bool* measured;
    uint32_t* measurement_results;
} QuantumRegister;

// Quantum measurement result
typedef struct MeasurementResult {
    uint32_t* outcomes;
    double* probabilities;
    uint32_t num_outcomes;
} MeasurementResult;

// Quantum algorithm types
typedef enum QuantumAlgorithm {
    ALGO_GROVER,
    ALGO_SHOR,
    ALGO_DEUTSCH_JOZSA,
    ALGO_QUANTUM_FOURIER,
    ALGO_VQE,
    ALGO_QAOA
} QuantumAlgorithm;

// Quantum error correction
typedef struct QuantumErrorCorrection {
    uint32_t code_distance;
    uint32_t num_physical_qubits;
    uint32_t num_logical_qubits;
    double error_rate;
    bool stabilizer_check[256];
} QuantumErrorCorrection;

// =====================================================================================================================
// Complex Number Operations
// =====================================================================================================================

ComplexNumber complex_create(double real, double imag) {
    ComplexNumber c;
    c.real = real;
    c.imag = imag;
    return c;
}

ComplexNumber complex_add(ComplexNumber a, ComplexNumber b) {
    ComplexNumber result;
    result.real = a.real + b.real;
    result.imag = a.imag + b.imag;
    return result;
}

ComplexNumber complex_subtract(ComplexNumber a, ComplexNumber b) {
    ComplexNumber result;
    result.real = a.real - b.real;
    result.imag = a.imag - b.imag;
    return result;
}

ComplexNumber complex_multiply(ComplexNumber a, ComplexNumber b) {
    ComplexNumber result;
    result.real = a.real * b.real - a.imag * b.imag;
    result.imag = a.real * b.imag + a.imag * b.real;
    return result;
}

ComplexNumber complex_conjugate(ComplexNumber c) {
    ComplexNumber result;
    result.real = c.real;
    result.imag = -c.imag;
    return result;
}

double complex_magnitude(ComplexNumber c) {
    return sqrt(c.real * c.real + c.imag * c.imag);
}

double complex_magnitude_squared(ComplexNumber c) {
    return c.real * c.real + c.imag * c.imag;
}

ComplexNumber complex_exp(ComplexNumber c) {
    double exp_real = exp(c.real);
    ComplexNumber result;
    result.real = exp_real * cos(c.imag);
    result.imag = exp_real * sin(c.imag);
    return result;
}

ComplexNumber complex_scale(ComplexNumber c, double scalar) {
    ComplexNumber result;
    result.real = c.real * scalar;
    result.imag = c.imag * scalar;
    return result;
}

// =====================================================================================================================
// Quantum State Operations
// =====================================================================================================================

QuantumState* quantum_state_create(uint32_t num_qubits) {
    QuantumState* state = (QuantumState*)malloc(sizeof(QuantumState));
    state->num_qubits = num_qubits;
    state->dimension = 1 << num_qubits; // 2^num_qubits
    
    state->amplitudes = (ComplexNumber*)calloc(state->dimension, sizeof(ComplexNumber));
    
    // Initialize to |0...0⟩ state
    state->amplitudes[0].real = 1.0;
    state->amplitudes[0].imag = 0.0;
    
    return state;
}

void quantum_state_destroy(QuantumState* state) {
    free(state->amplitudes);
    free(state);
}

QuantumState* quantum_state_copy(QuantumState* state) {
    QuantumState* copy = (QuantumState*)malloc(sizeof(QuantumState));
    copy->num_qubits = state->num_qubits;
    copy->dimension = state->dimension;
    copy->amplitudes = (ComplexNumber*)malloc(sizeof(ComplexNumber) * copy->dimension);
    memcpy(copy->amplitudes, state->amplitudes, sizeof(ComplexNumber) * copy->dimension);
    return copy;
}

void quantum_state_normalize(QuantumState* state) {
    double sum = 0.0;
    
    for (uint32_t i = 0; i < state->dimension; i++) {
        sum += complex_magnitude_squared(state->amplitudes[i]);
    }
    
    double norm = sqrt(sum);
    
    if (norm > 1e-10) {
        for (uint32_t i = 0; i < state->dimension; i++) {
            state->amplitudes[i] = complex_scale(state->amplitudes[i], 1.0 / norm);
        }
    }
}

double quantum_state_get_probability(QuantumState* state, uint32_t basis_state) {
    if (basis_state >= state->dimension) return 0.0;
    return complex_magnitude_squared(state->amplitudes[basis_state]);
}

void quantum_state_set_amplitude(QuantumState* state, uint32_t basis_state, 
                                 double real, double imag) {
    if (basis_state < state->dimension) {
        state->amplitudes[basis_state].real = real;
        state->amplitudes[basis_state].imag = imag;
    }
}

// Create superposition state
void quantum_state_hadamard_all(QuantumState* state) {
    double factor = 1.0 / sqrt((double)state->dimension);
    
    for (uint32_t i = 0; i < state->dimension; i++) {
        state->amplitudes[i].real = factor;
        state->amplitudes[i].imag = 0.0;
    }
}

// =====================================================================================================================
// Quantum Gate Definitions
// =====================================================================================================================

QuantumGate* quantum_gate_create(uint32_t size, const char* name) {
    QuantumGate* gate = (QuantumGate*)malloc(sizeof(QuantumGate));
    gate->size = size;
    strncpy(gate->name, name, 31);
    gate->name[31] = '\0';
    
    gate->matrix = (ComplexNumber**)malloc(sizeof(ComplexNumber*) * size);
    for (uint32_t i = 0; i < size; i++) {
        gate->matrix[i] = (ComplexNumber*)calloc(size, sizeof(ComplexNumber));
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

// Pauli-X Gate (NOT gate)
QuantumGate* quantum_gate_pauli_x() {
    QuantumGate* gate = quantum_gate_create(2, "X");
    
    gate->matrix[0][1].real = 1.0;
    gate->matrix[1][0].real = 1.0;
    
    return gate;
}

// Pauli-Y Gate
QuantumGate* quantum_gate_pauli_y() {
    QuantumGate* gate = quantum_gate_create(2, "Y");
    
    gate->matrix[0][1].imag = -1.0;
    gate->matrix[1][0].imag = 1.0;
    
    return gate;
}

// Pauli-Z Gate
QuantumGate* quantum_gate_pauli_z() {
    QuantumGate* gate = quantum_gate_create(2, "Z");
    
    gate->matrix[0][0].real = 1.0;
    gate->matrix[1][1].real = -1.0;
    
    return gate;
}

// Hadamard Gate
QuantumGate* quantum_gate_hadamard() {
    QuantumGate* gate = quantum_gate_create(2, "H");
    
    double factor = 1.0 / sqrt(2.0);
    
    gate->matrix[0][0].real = factor;
    gate->matrix[0][1].real = factor;
    gate->matrix[1][0].real = factor;
    gate->matrix[1][1].real = -factor;
    
    return gate;
}

// Phase Gate (S gate)
QuantumGate* quantum_gate_phase(double theta) {
    QuantumGate* gate = quantum_gate_create(2, "PHASE");
    
    gate->matrix[0][0].real = 1.0;
    gate->matrix[1][1].real = cos(theta);
    gate->matrix[1][1].imag = sin(theta);
    
    return gate;
}

// T Gate
QuantumGate* quantum_gate_t() {
    QuantumGate* gate = quantum_gate_create(2, "T");
    
    gate->matrix[0][0].real = 1.0;
    gate->matrix[1][1].real = cos(M_PI / 4.0);
    gate->matrix[1][1].imag = sin(M_PI / 4.0);
    
    return gate;
}

// Rotation gates
QuantumGate* quantum_gate_rx(double theta) {
    QuantumGate* gate = quantum_gate_create(2, "RX");
    
    double cos_half = cos(theta / 2.0);
    double sin_half = sin(theta / 2.0);
    
    gate->matrix[0][0].real = cos_half;
    gate->matrix[0][1].imag = -sin_half;
    gate->matrix[1][0].imag = -sin_half;
    gate->matrix[1][1].real = cos_half;
    
    return gate;
}

QuantumGate* quantum_gate_ry(double theta) {
    QuantumGate* gate = quantum_gate_create(2, "RY");
    
    double cos_half = cos(theta / 2.0);
    double sin_half = sin(theta / 2.0);
    
    gate->matrix[0][0].real = cos_half;
    gate->matrix[0][1].real = -sin_half;
    gate->matrix[1][0].real = sin_half;
    gate->matrix[1][1].real = cos_half;
    
    return gate;
}

QuantumGate* quantum_gate_rz(double theta) {
    QuantumGate* gate = quantum_gate_create(2, "RZ");
    
    double cos_half = cos(theta / 2.0);
    double sin_half = sin(theta / 2.0);
    
    gate->matrix[0][0].real = cos_half;
    gate->matrix[0][0].imag = -sin_half;
    gate->matrix[1][1].real = cos_half;
    gate->matrix[1][1].imag = sin_half;
    
    return gate;
}

// CNOT Gate (Controlled-NOT)
QuantumGate* quantum_gate_cnot() {
    QuantumGate* gate = quantum_gate_create(4, "CNOT");
    
    gate->matrix[0][0].real = 1.0;
    gate->matrix[1][1].real = 1.0;
    gate->matrix[2][3].real = 1.0;
    gate->matrix[3][2].real = 1.0;
    
    return gate;
}

// SWAP Gate
QuantumGate* quantum_gate_swap() {
    QuantumGate* gate = quantum_gate_create(4, "SWAP");
    
    gate->matrix[0][0].real = 1.0;
    gate->matrix[1][2].real = 1.0;
    gate->matrix[2][1].real = 1.0;
    gate->matrix[3][3].real = 1.0;
    
    return gate;
}

// Toffoli Gate (CCNOT)
QuantumGate* quantum_gate_toffoli() {
    QuantumGate* gate = quantum_gate_create(8, "TOFFOLI");
    
    for (uint32_t i = 0; i < 6; i++) {
        gate->matrix[i][i].real = 1.0;
    }
    gate->matrix[6][7].real = 1.0;
    gate->matrix[7][6].real = 1.0;
    
    return gate;
}

// =====================================================================================================================
// Quantum Gate Application
// =====================================================================================================================

void quantum_apply_single_qubit_gate(QuantumState* state, QuantumGate* gate, uint32_t target_qubit) {
    if (gate->size != 2 || target_qubit >= state->num_qubits) return;
    
    uint32_t mask = 1 << target_qubit;
    QuantumState* new_state = quantum_state_create(state->num_qubits);
    
    for (uint32_t i = 0; i < state->dimension; i++) {
        uint32_t bit = (i & mask) ? 1 : 0;
        uint32_t i_flipped = i ^ mask;
        
        ComplexNumber amp0 = state->amplitudes[bit ? i_flipped : i];
        ComplexNumber amp1 = state->amplitudes[bit ? i : i_flipped];
        
        ComplexNumber new_amp = complex_add(
            complex_multiply(gate->matrix[bit][0], amp0),
            complex_multiply(gate->matrix[bit][1], amp1)
        );
        
        new_state->amplitudes[i] = new_amp;
    }
    
    memcpy(state->amplitudes, new_state->amplitudes, sizeof(ComplexNumber) * state->dimension);
    quantum_state_destroy(new_state);
}

void quantum_apply_two_qubit_gate(QuantumState* state, QuantumGate* gate, 
                                  uint32_t control_qubit, uint32_t target_qubit) {
    if (gate->size != 4 || control_qubit >= state->num_qubits || 
        target_qubit >= state->num_qubits || control_qubit == target_qubit) return;
    
    uint32_t control_mask = 1 << control_qubit;
    uint32_t target_mask = 1 << target_qubit;
    
    QuantumState* new_state = quantum_state_create(state->num_qubits);
    
    for (uint32_t i = 0; i < state->dimension; i++) {
        uint32_t control_bit = (i & control_mask) ? 1 : 0;
        uint32_t target_bit = (i & target_mask) ? 1 : 0;
        uint32_t basis = (control_bit << 1) | target_bit;
        
        ComplexNumber result = complex_create(0, 0);
        
        for (uint32_t j = 0; j < 4; j++) {
            uint32_t j_control = (j >> 1) & 1;
            uint32_t j_target = j & 1;
            
            uint32_t state_index = i;
            if (j_control != control_bit) state_index ^= control_mask;
            if (j_target != target_bit) state_index ^= target_mask;
            
            ComplexNumber term = complex_multiply(
                gate->matrix[basis][j],
                state->amplitudes[state_index]
            );
            
            result = complex_add(result, term);
        }
        
        new_state->amplitudes[i] = result;
    }
    
    memcpy(state->amplitudes, new_state->amplitudes, sizeof(ComplexNumber) * state->dimension);
    quantum_state_destroy(new_state);
}

// =====================================================================================================================
// Quantum Circuit Operations
// =====================================================================================================================

QuantumCircuit* quantum_circuit_create(uint32_t num_qubits) {
    QuantumCircuit* circuit = (QuantumCircuit*)malloc(sizeof(QuantumCircuit));
    circuit->num_qubits = num_qubits;
    circuit->gate_count = 0;
    circuit->capacity = 100;
    
    circuit->gates = (QuantumGate**)malloc(sizeof(QuantumGate*) * circuit->capacity);
    circuit->target_qubits = (uint32_t*)malloc(sizeof(uint32_t) * circuit->capacity);
    circuit->control_qubits = (uint32_t*)malloc(sizeof(uint32_t) * circuit->capacity);
    
    return circuit;
}

void quantum_circuit_destroy(QuantumCircuit* circuit) {
    for (uint32_t i = 0; i < circuit->gate_count; i++) {
        quantum_gate_destroy(circuit->gates[i]);
    }
    
    free(circuit->gates);
    free(circuit->target_qubits);
    free(circuit->control_qubits);
    free(circuit);
}

void quantum_circuit_add_gate(QuantumCircuit* circuit, QuantumGate* gate, 
                              uint32_t target_qubit, int32_t control_qubit) {
    if (circuit->gate_count >= circuit->capacity) {
        circuit->capacity *= 2;
        circuit->gates = (QuantumGate**)realloc(circuit->gates, 
                                               sizeof(QuantumGate*) * circuit->capacity);
        circuit->target_qubits = (uint32_t*)realloc(circuit->target_qubits, 
                                                    sizeof(uint32_t) * circuit->capacity);
        circuit->control_qubits = (uint32_t*)realloc(circuit->control_qubits, 
                                                     sizeof(uint32_t) * circuit->capacity);
    }
    
    circuit->gates[circuit->gate_count] = gate;
    circuit->target_qubits[circuit->gate_count] = target_qubit;
    circuit->control_qubits[circuit->gate_count] = control_qubit;
    circuit->gate_count++;
}

void quantum_circuit_execute(QuantumCircuit* circuit, QuantumState* state) {
    for (uint32_t i = 0; i < circuit->gate_count; i++) {
        if (circuit->control_qubits[i] < 0) {
            quantum_apply_single_qubit_gate(state, circuit->gates[i], 
                                           circuit->target_qubits[i]);
        } else {
            quantum_apply_two_qubit_gate(state, circuit->gates[i], 
                                        circuit->control_qubits[i],
                                        circuit->target_qubits[i]);
        }
    }
}

// =====================================================================================================================
// Quantum Measurement
// =====================================================================================================================

uint32_t quantum_measure_qubit(QuantumState* state, uint32_t qubit) {
    if (qubit >= state->num_qubits) return 0;
    
    uint32_t mask = 1 << qubit;
    double prob_zero = 0.0;
    
    for (uint32_t i = 0; i < state->dimension; i++) {
        if ((i & mask) == 0) {
            prob_zero += complex_magnitude_squared(state->amplitudes[i]);
        }
    }
    
    double random = (double)rand() / RAND_MAX;
    uint32_t result = (random < prob_zero) ? 0 : 1;
    
    // Collapse state
    double norm = 0.0;
    for (uint32_t i = 0; i < state->dimension; i++) {
        if (((i & mask) ? 1 : 0) != result) {
            state->amplitudes[i].real = 0.0;
            state->amplitudes[i].imag = 0.0;
        } else {
            norm += complex_magnitude_squared(state->amplitudes[i]);
        }
    }
    
    norm = sqrt(norm);
    if (norm > 1e-10) {
        for (uint32_t i = 0; i < state->dimension; i++) {
            state->amplitudes[i] = complex_scale(state->amplitudes[i], 1.0 / norm);
        }
    }
    
    return result;
}

MeasurementResult* quantum_measure_all(QuantumState* state) {
    MeasurementResult* result = (MeasurementResult*)malloc(sizeof(MeasurementResult));
    result->num_outcomes = state->dimension;
    result->outcomes = (uint32_t*)malloc(sizeof(uint32_t) * result->num_outcomes);
    result->probabilities = (double*)malloc(sizeof(double) * result->num_outcomes);
    
    for (uint32_t i = 0; i < state->dimension; i++) {
        result->outcomes[i] = i;
        result->probabilities[i] = complex_magnitude_squared(state->amplitudes[i]);
    }
    
    return result;
}

// =====================================================================================================================
// Quantum Entanglement
// =====================================================================================================================

void quantum_create_bell_state(QuantumState* state, uint32_t qubit1, uint32_t qubit2) {
    // Create Bell state: (|00⟩ + |11⟩) / sqrt(2)
    
    // Apply Hadamard to first qubit
    QuantumGate* h = quantum_gate_hadamard();
    quantum_apply_single_qubit_gate(state, h, qubit1);
    quantum_gate_destroy(h);
    
    // Apply CNOT with first qubit as control, second as target
    QuantumGate* cnot = quantum_gate_cnot();
    quantum_apply_two_qubit_gate(state, cnot, qubit1, qubit2);
    quantum_gate_destroy(cnot);
}

double quantum_calculate_entanglement_entropy(QuantumState* state, uint32_t qubit) {
    // Calculate von Neumann entropy for single qubit (reduced density matrix)
    uint32_t mask = 1 << qubit;
    double prob_zero = 0.0;
    
    for (uint32_t i = 0; i < state->dimension; i++) {
        if ((i & mask) == 0) {
            prob_zero += complex_magnitude_squared(state->amplitudes[i]);
        }
    }
    
    double prob_one = 1.0 - prob_zero;
    
    double entropy = 0.0;
    if (prob_zero > 1e-10) {
        entropy -= prob_zero * log2(prob_zero);
    }
    if (prob_one > 1e-10) {
        entropy -= prob_one * log2(prob_one);
    }
    
    return entropy;
}

// =====================================================================================================================
// Quantum Algorithms
// =====================================================================================================================

// Quantum Fourier Transform
void quantum_fourier_transform(QuantumState* state, uint32_t start_qubit, uint32_t num_qubits) {
    for (uint32_t j = 0; j < num_qubits; j++) {
        uint32_t qubit = start_qubit + j;
        
        // Apply Hadamard
        QuantumGate* h = quantum_gate_hadamard();
        quantum_apply_single_qubit_gate(state, h, qubit);
        quantum_gate_destroy(h);
        
        // Apply controlled phase rotations
        for (uint32_t k = j + 1; k < num_qubits; k++) {
            double theta = M_PI / (1 << (k - j));
            QuantumGate* phase = quantum_gate_phase(theta);
            quantum_apply_two_qubit_gate(state, phase, start_qubit + k, qubit);
            quantum_gate_destroy(phase);
        }
    }
    
    // Swap qubits
    for (uint32_t j = 0; j < num_qubits / 2; j++) {
        QuantumGate* swap = quantum_gate_swap();
        quantum_apply_two_qubit_gate(state, swap, 
                                     start_qubit + j, 
                                     start_qubit + num_qubits - 1 - j);
        quantum_gate_destroy(swap);
    }
}

// Grover's Algorithm Oracle
void quantum_grover_oracle(QuantumState* state, uint32_t target_state) {
    // Mark the target state by flipping its phase
    if (target_state < state->dimension) {
        state->amplitudes[target_state].real = -state->amplitudes[target_state].real;
        state->amplitudes[target_state].imag = -state->amplitudes[target_state].imag;
    }
}

// Grover's Diffusion Operator
void quantum_grover_diffusion(QuantumState* state) {
    // Apply Hadamard to all qubits
    QuantumGate* h = quantum_gate_hadamard();
    for (uint32_t i = 0; i < state->num_qubits; i++) {
        quantum_apply_single_qubit_gate(state, h, i);
    }
    quantum_gate_destroy(h);
    
    // Apply conditional phase shift
    for (uint32_t i = 1; i < state->dimension; i++) {
        state->amplitudes[i].real = -state->amplitudes[i].real;
        state->amplitudes[i].imag = -state->amplitudes[i].imag;
    }
    
    // Apply Hadamard to all qubits again
    h = quantum_gate_hadamard();
    for (uint32_t i = 0; i < state->num_qubits; i++) {
        quantum_apply_single_qubit_gate(state, h, i);
    }
    quantum_gate_destroy(h);
}

// Complete Grover's Search
uint32_t quantum_grover_search(uint32_t num_qubits, uint32_t target_state) {
    QuantumState* state = quantum_state_create(num_qubits);
    
    // Initialize to equal superposition
    quantum_state_hadamard_all(state);
    
    // Calculate number of iterations
    uint32_t num_iterations = (uint32_t)(M_PI / 4.0 * sqrt((double)state->dimension));
    
    // Grover iteration
    for (uint32_t i = 0; i < num_iterations; i++) {
        quantum_grover_oracle(state, target_state);
        quantum_grover_diffusion(state);
    }
    
    // Measure all qubits
    uint32_t result = 0;
    for (uint32_t i = 0; i < num_qubits; i++) {
        result |= (quantum_measure_qubit(state, i) << i);
    }
    
    quantum_state_destroy(state);
    return result;
}

// =====================================================================================================================
// Quantum Error Correction
// =====================================================================================================================

QuantumErrorCorrection* quantum_error_correction_create(uint32_t code_distance) {
    QuantumErrorCorrection* qec = (QuantumErrorCorrection*)malloc(sizeof(QuantumErrorCorrection));
    qec->code_distance = code_distance;
    qec->num_physical_qubits = code_distance * code_distance;
    qec->num_logical_qubits = 1;
    qec->error_rate = 0.001;
    memset(qec->stabilizer_check, 0, sizeof(qec->stabilizer_check));
    
    return qec;
}

// Three-qubit bit-flip code
void quantum_encode_three_qubit_code(QuantumState* state, uint32_t logical_qubit) {
    // Encode logical qubit into three physical qubits
    uint32_t q0 = logical_qubit * 3;
    uint32_t q1 = q0 + 1;
    uint32_t q2 = q0 + 2;
    
    // CNOT from q0 to q1
    QuantumGate* cnot = quantum_gate_cnot();
    quantum_apply_two_qubit_gate(state, cnot, q0, q1);
    
    // CNOT from q0 to q2
    quantum_apply_two_qubit_gate(state, cnot, q0, q2);
    quantum_gate_destroy(cnot);
}

void quantum_decode_three_qubit_code(QuantumState* state, uint32_t logical_qubit) {
    uint32_t q0 = logical_qubit * 3;
    uint32_t q1 = q0 + 1;
    uint32_t q2 = q0 + 2;
    
    // Reverse encoding
    QuantumGate* cnot = quantum_gate_cnot();
    quantum_apply_two_qubit_gate(state, cnot, q0, q2);
    quantum_apply_two_qubit_gate(state, cnot, q0, q1);
    quantum_gate_destroy(cnot);
}

// Detect and correct bit-flip errors
bool quantum_detect_bit_flip_error(QuantumState* state, uint32_t logical_qubit) {
    uint32_t q0 = logical_qubit * 3;
    uint32_t q1 = q0 + 1;
    uint32_t q2 = q0 + 2;
    
    // Measure syndrome qubits
    uint32_t syndrome = 0;
    
    // Check q0 == q1
    syndrome |= (quantum_measure_qubit(state, q0) ^ quantum_measure_qubit(state, q1)) << 0;
    
    // Check q0 == q2
    syndrome |= (quantum_measure_qubit(state, q0) ^ quantum_measure_qubit(state, q2)) << 1;
    
    // Apply correction based on syndrome
    if (syndrome != 0) {
        QuantumGate* x = quantum_gate_pauli_x();
        
        if (syndrome == 3) {
            quantum_apply_single_qubit_gate(state, x, q0);
        } else if (syndrome == 1) {
            quantum_apply_single_qubit_gate(state, x, q1);
        } else if (syndrome == 2) {
            quantum_apply_single_qubit_gate(state, x, q2);
        }
        
        quantum_gate_destroy(x);
        return true;
    }
    
    return false;
}

// =====================================================================================================================
// Quantum Register Operations
// =====================================================================================================================

QuantumRegister* quantum_register_create(uint32_t num_qubits) {
    QuantumRegister* reg = (QuantumRegister*)malloc(sizeof(QuantumRegister));
    reg->num_qubits = num_qubits;
    reg->state = quantum_state_create(num_qubits);
    reg->measured = (bool*)calloc(num_qubits, sizeof(bool));
    reg->measurement_results = (uint32_t*)calloc(num_qubits, sizeof(uint32_t));
    
    return reg;
}

void quantum_register_destroy(QuantumRegister* reg) {
    quantum_state_destroy(reg->state);
    free(reg->measured);
    free(reg->measurement_results);
    free(reg);
}

void quantum_register_reset(QuantumRegister* reg) {
    quantum_state_destroy(reg->state);
    reg->state = quantum_state_create(reg->num_qubits);
    memset(reg->measured, 0, sizeof(bool) * reg->num_qubits);
    memset(reg->measurement_results, 0, sizeof(uint32_t) * reg->num_qubits);
}

void quantum_register_apply_gate(QuantumRegister* reg, QuantumGate* gate, 
                                 uint32_t target_qubit, int32_t control_qubit) {
    if (control_qubit < 0) {
        quantum_apply_single_qubit_gate(reg->state, gate, target_qubit);
    } else {
        quantum_apply_two_qubit_gate(reg->state, gate, control_qubit, target_qubit);
    }
}

uint32_t quantum_register_measure(QuantumRegister* reg, uint32_t qubit) {
    if (!reg->measured[qubit]) {
        reg->measurement_results[qubit] = quantum_measure_qubit(reg->state, qubit);
        reg->measured[qubit] = true;
    }
    
    return reg->measurement_results[qubit];
}

// =====================================================================================================================
// Quantum Teleportation Protocol
// =====================================================================================================================

void quantum_teleportation(QuantumState* state, uint32_t source_qubit, 
                           uint32_t aux_qubit1, uint32_t aux_qubit2, 
                           uint32_t dest_qubit) {
    // Create Bell pair between aux qubits
    quantum_create_bell_state(state, aux_qubit1, aux_qubit2);
    
    // Apply CNOT from source to aux1
    QuantumGate* cnot = quantum_gate_cnot();
    quantum_apply_two_qubit_gate(state, cnot, source_qubit, aux_qubit1);
    quantum_gate_destroy(cnot);
    
    // Apply Hadamard to source
    QuantumGate* h = quantum_gate_hadamard();
    quantum_apply_single_qubit_gate(state, h, source_qubit);
    quantum_gate_destroy(h);
    
    // Measure source and aux1
    uint32_t m1 = quantum_measure_qubit(state, source_qubit);
    uint32_t m2 = quantum_measure_qubit(state, aux_qubit1);
    
    // Apply corrections to dest based on measurements
    if (m2 == 1) {
        QuantumGate* x = quantum_gate_pauli_x();
        quantum_apply_single_qubit_gate(state, x, dest_qubit);
        quantum_gate_destroy(x);
    }
    
    if (m1 == 1) {
        QuantumGate* z = quantum_gate_pauli_z();
        quantum_apply_single_qubit_gate(state, z, dest_qubit);
        quantum_gate_destroy(z);
    }
}

// =====================================================================================================================
// Variational Quantum Eigensolver (VQE)
// =====================================================================================================================

typedef struct VQEParameters {
    double* angles;
    uint32_t num_parameters;
    double energy;
} VQEParameters;

VQEParameters* vqe_parameters_create(uint32_t num_parameters) {
    VQEParameters* params = (VQEParameters*)malloc(sizeof(VQEParameters));
    params->num_parameters = num_parameters;
    params->angles = (double*)malloc(sizeof(double) * num_parameters);
    
    // Initialize with random angles
    for (uint32_t i = 0; i < num_parameters; i++) {
        params->angles[i] = ((double)rand() / RAND_MAX) * 2.0 * M_PI;
    }
    
    params->energy = 0.0;
    
    return params;
}

void vqe_apply_ansatz(QuantumState* state, VQEParameters* params) {
    uint32_t param_idx = 0;
    
    for (uint32_t i = 0; i < state->num_qubits; i++) {
        // Apply RY rotation
        QuantumGate* ry = quantum_gate_ry(params->angles[param_idx++]);
        quantum_apply_single_qubit_gate(state, ry, i);
        quantum_gate_destroy(ry);
        
        // Apply RZ rotation
        QuantumGate* rz = quantum_gate_rz(params->angles[param_idx++]);
        quantum_apply_single_qubit_gate(state, rz, i);
        quantum_gate_destroy(rz);
    }
    
    // Apply entangling gates
    for (uint32_t i = 0; i < state->num_qubits - 1; i++) {
        QuantumGate* cnot = quantum_gate_cnot();
        quantum_apply_two_qubit_gate(state, cnot, i, i + 1);
        quantum_gate_destroy(cnot);
    }
}

double vqe_compute_expectation(QuantumState* state) {
    // Compute expectation value of Hamiltonian
    double expectation = 0.0;
    
    for (uint32_t i = 0; i < state->dimension; i++) {
        double prob = complex_magnitude_squared(state->amplitudes[i]);
        double energy = 0.0;
        
        // Example Hamiltonian: sum of Z operators
        for (uint32_t j = 0; j < state->num_qubits; j++) {
            energy += ((i & (1 << j)) ? -1.0 : 1.0);
        }
        
        expectation += prob * energy;
    }
    
    return expectation;
}

// =====================================================================================================================
// End of Quantum Computing Engine Module
// Lines: ~1100
// Total so far: ~2150 lines
// =====================================================================================================================
