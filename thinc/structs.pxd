from libc.stdint cimport int16_t, int32_t, uint64_t
from preshed.maps cimport MapStruct
from .typedefs cimport weight_t, atom_t


include "compile_time_constants.pxi"

# Alias this, so that it matches our naming scheme
ctypedef MapStruct MapC

ctypedef void (*update_f_t)(OptimizerC* opt, weight_t* mtm, weight_t* gradient,
        weight_t* weights, weight_t scale, int nr) except *


cdef struct OptimizerC:
    update_f_t update
    weight_t* params
    
    EmbeddingC* embed_params
    void* ext

    int nr
    weight_t mu
    weight_t eta
    weight_t eps
    weight_t rho


cdef struct EmbeddingC:
    MapC** tables
    weight_t** defaults
    int* offsets
    int* lengths
    int nr


cdef struct NeuralNetC:
    int* widths
    weight_t* weights
    weight_t* gradient
    
    weight_t** fwd_norms
    weight_t** bwd_norms
    
    OptimizerC* opt

    EmbeddingC* embeds

    int32_t nr_layer
    int32_t nr_weight
    int32_t nr_embed

    weight_t alpha
    weight_t eta
    weight_t rho
    weight_t eps


cdef struct ExampleC:
    int* is_valid
    weight_t* costs
    atom_t* atoms
    FeatureC* features
    weight_t* scores

    weight_t* fine_tune
    
    weight_t** fwd_state
    weight_t** bwd_state

    int nr_class
    int nr_atom
    int nr_feat
    
    int guess
    int best
    int cost


cdef struct BatchC:
    ExampleC* egs
    weight_t* gradient
    int nr_eg
    int nr_weight


# Iteration controller
cdef struct IteratorC:
    int nr_out
    int nr_in
    int i
    int W
    int bias
    int gamma
    int beta
    int below
    int here
    int above
    int Ex
    int Vx
    int E_dXh
    int E_dXh_Xh


cdef struct SparseArrayC:
    int32_t key
    weight_t val


cdef struct FeatureC:
    int32_t i
    uint64_t key
    weight_t val


cdef struct SparseAverageC:
    SparseArrayC* curr
    SparseArrayC* avgs
    SparseArrayC* times


cdef struct TemplateC:
    int[MAX_TEMPLATE_LEN] indices
    int length
    atom_t[MAX_TEMPLATE_LEN] atoms
