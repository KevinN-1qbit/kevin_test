using LinearAlgebra
using StaticArrays
using NearestNeighbors
using JLD
using Distances
using IterTools
import Base: size, length, eltype, getindex
include("gates.jl")
include("utils.jl")
include("gate_sequence.jl")

"""
Create sequences of combinations of all base gates.
"""
function create_library(basis, seq_length)
    values = Int8(0):Int8(length(basis))
    combinations = collect(product(fill(values, seq_length)...))
    return hcat([collect(c) for c in combinations]...)
end


"""
Create iterative sequences of combinations of all base gates.
The Library will contain sequences of variable lengths.
"""
function create_library_generator(basis, seq_length)
    combinations = []
    values = Int8(1):Int8(length(basis))
    for x in 1:seq_length
        sequences = Iterators.Stateful(product(fill(values, x)...))
        push!(combinations, sequences)
    end
    return combinations
end


"""
Search kd tree for gate that is closest to u using a k-d tree
"""
function kdtree_search(kdtree, basis, u)
    u_vec = complex_mat_to_vec(u)
    u_vec_negative = complex_mat_to_vec(-u)
    lib_linked_index, dists = nn(kdtree, u_vec)
    lib_linked_index_negative, dists_negative = nn(kdtree, u_vec_negative)

    if dists[1] < dists_negative[1]
        col_index = lib_linked_index[1]
        phase = 1
    else
        col_index = lib_linked_index_negative[1]
        phase = -1
    end

    # explicitly construct the sequence from col_index
    seq = 1
    while col_index > 3^seq
        col_index -= 3^seq
        seq += 1
    end
    col_index -= 1
    vector = Vector{Int8}(undef, seq)
    for i in 1:length(vector)
        vector[i] = (col_index % length(basis)) + 1
        col_index = col_index ÷ length(basis)
    end

    return GateSeq(phase,collect(vector))
end


"""
Find a gate in the list closest to u by searching every element
"""
function linear_search(seq_length, u, basis, dist_func)
    min_seq = GateSeq(1, [])
    min_dist = dist_func(I, u)
    library = create_library_generator(basis, seq_length)
    for sequences in library
        for seq in sequences
            filled_vector = fill_out_zeros(seq_length,collect(seq))
            gate_seq = GateSeq(1,collect(filled_vector))
            complex_matrix = eval_seq(gate_seq, basis)

            dist_1 = dist_func(complex_matrix, u)
            dist_2 = dist_func(complex_matrix, -u)
            if dist_1 < min_dist || dist_2 < min_dist
                if dist_1 < dist_2
                    min_dist = dist_1
                    min_seq = gate_seq
                    min_seq.phase = 1
                else
                    min_dist = dist_2
                    min_seq = gate_seq
                    min_seq.phase = -1
                end
            end
        end
    end
    return min_seq
end


"""
Pad the vector with zeros to length seq_length
"""
function fill_out_zeros(seq_length, vector)
    while length(vector) < seq_length
        push!(vector, 0.0)
    end
    return vector
end


"""
Convert complex matric to vector.
"""
function complex_mat_to_vec(matrix)
    if size(matrix) != (2, 2)
        throw(ArgumentError("Input must be a 2x2 matrix"))
    end
    
    vector = zeros(Float64, 8, 1)
    
    # Extract real and imaginary parts
    for i in 1:2
        for j in 1:2
            vector[i + 2*(j-1)] = real(matrix[i, j]) # First 4 elements: Real parts
            vector[i + 2*(j-1) + 4] = imag(matrix[i, j]) # Next 4 elements: Imaginary parts
        end
    end
    
    return vector
end

"""
Create a KD Tree from a given library of sequences.
"""
function create_kd_tree(basis, library)
    tree_vector = Vector{Vector{Float64}}()
    for sequences in library
        for seq in sequences
            gate_seq = GateSeq(1,collect(seq))
            complex_matrix = eval_seq(gate_seq, basis)
            vector = complex_mat_to_vec(complex_matrix)
            push!(tree_vector, vec(vector))
        end
    end

    tree_data = reshape(collect(Iterators.flatten(tree_vector)), (length(tree_vector[1]),length(tree_vector)))
    kdtree = KDTree(tree_data)

    return kdtree
end
