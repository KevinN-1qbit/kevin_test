include("utils.jl")
include("gate_sequence.jl")

struct SKInst
    index::Int64
    unitary::SArray
    qargs::Vector{Any}
    error_budget::Float64
end

mutable struct SKResult
    index::Int64
    gate_seq::GateSeq
    qargs::Vector{Any}
    error::Float64
end

"""
Solovay-Kitaev Algorithm using either Linear or KD Tree approach.
"""
function sk_algo(u, seq_length, recursion, basis, dist_func, error_budget, kdtree=nothing, basic_approx_treshold=0.50)
    if recursion == 0
        if isnothing(kdtree)
            basic_seq = linear_search(seq_length, u, basis, dist_func)
        else
            basic_seq = kdtree_search(kdtree, basis, u)
        end

        distance = dist_func(u, eval_seq(basic_seq, basis))
        if distance > basic_approx_treshold
            # Terminate if the approximate exceeds the upperbound
            @warn "poor basic approximation found" distance
        end

        return basic_seq
    else
        u_next_seq = sk_algo(u, seq_length, recursion - 1, basis, dist_func, error_budget, kdtree, basic_approx_treshold)
        u_next_gate = eval_seq(u_next_seq, basis)
        if norm_dist(u_next_gate, u) < error_budget
            return u_next_seq
        end
        delta = u * inv(u_next_gate)

        v, w = gc_decomp(delta)

        v_next_seq = sk_algo(v, seq_length, recursion - 1, basis, dist_func, error_budget, kdtree, basic_approx_treshold)
        w_next_seq = sk_algo(w, seq_length, recursion - 1, basis, dist_func, error_budget, kdtree, basic_approx_treshold)

        # Perform delta_approx = v * w * v' * w'
        adjoint!(w_next_seq)
        adjoint!(v_next_seq)
        left_multiply!(w_next_seq, u_next_seq)
        left_multiply!(v_next_seq, u_next_seq)
        adjoint!(w_next_seq)
        adjoint!(v_next_seq)
        left_multiply!(w_next_seq, u_next_seq)
        left_multiply!(v_next_seq, u_next_seq)

        return u_next_seq
    end
end

"""
Wrapper function around the recursive function sk_algo
Takes as input the struct SKInst and outputs an SKResult
"""
function run_sk(inst::SKInst, seq_length, rec, basis, dist, error_budget, tree)
    seq = sk_algo(inst.unitary, seq_length, rec, basis, dist, error_budget, tree)
    error = norm_dist(eval_seq(seq, basis), inst.unitary)
    result = SKResult(inst.index,
                      seq,
                      inst.qargs,
                      error)
    return result
end
