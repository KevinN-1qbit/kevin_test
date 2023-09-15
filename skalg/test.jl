using JLD
using NearestNeighbors
include("skalg.jl")
include("gates.jl")
include("utils.jl")
include("gate_library.jl")
include("gate_sequence.jl")
"""
This file is for testing some of the core functions of the SK algorithm.
"""

# Create a gate we would like to approximate with SK and convert it to SU(2)
theta = pi / 5
phi = pi / 3 # pi / 3 default
lam = 0.1 * pi / 6
test_u = to_su2(create_u(theta, phi, lam))

# Define a basis, all unitaries should be SU(2)
test_basis = [to_su2(H), to_su2(T), to_su2(inv(T))]

seq_length = 10

# Create Library
test_library = create_library_generator(test_basis, seq_length)

# Create KD Tree
@time begin
    test_kdtree = create_kd_tree(test_basis, test_library)
    println("Time to create KD Tree")
end

function test(u, seq_length, basis, max_rec, kdtree=nothing)
    @time begin
        # Let's call SK multiple times with difference level of reccurence depth
        for rec in 0:max_rec
            # Call SK. SK will output a struct GateSeq
            if isnothing(kdtree)
                println("Linear search:")
                approx_u_seq = sk_algo(u, seq_length, rec, basis, norm_dist)
            else
                println("KD-Tree search:")
                approx_u_seq = sk_algo(u, seq_length, rec, basis, norm_dist, kdtree)
            end
            # Evaluate a sequence into a matrix
            u_approx = eval_seq(approx_u_seq, basis)
            # Print the trace distance
            println("\n rec: $rec, ", norm_dist(u_approx, u))
        end
    end
end

max_rec = 10
test(test_u, seq_length, test_basis, max_rec, test_kdtree)
