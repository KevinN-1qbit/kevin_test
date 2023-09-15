using StaticArrays
include("gates.jl")
include("utils.jl")

#= This file defines the GateSeq struct and related operations. The key idea is to represent a sequence of gates as integers.
For example, suppose our basis is [H T S].
Let U = H*T*H*S.
We represent U as a sequence of integers which enumerate the basis [H, T, S].
So, U is given by a sequence [1 2 1 3].
If U = H*S', then the sequence is [1 -3]. The minus sign tells us that the first factor in the product is an adjoint.
For example, U'= SH' is equivalent to [3, -1].

We can also perform multiplication on sequences.
Let U = HT and V = S. Then U*V' is equivalent to [1 2 -3]. So multiplication is equivalent to appending sequences.
All these operations are coded below.

Example:
# Define a gate sequences `a_seq` and `b_seq`
basis = [H, T, S]
a_seq = GateSeq([1 2]) # equiv to H*T
b_seq = GateSeq([3]) # equiv to S
# Multiply `a_seq`` and `b_seq`
c_seq = left_multiply(a_seq, b_seq) # produces [1 2 3] or equiv H*T*S
# Display the sequence attribute
display(c_seq.seq)
# Check H*T*S
print("\n Compute the product H*T*S: \n")
display(H * T * S)
# Check if we get the same result by evaluating the sequences in the basis
print("\n Evaluate the `c_seq`: \n")
display(eval_seq(c_seq, basis))
=#

mutable struct GateSeq
    #= This stuct will be extended to contain more attributes in the future.
    So far, it implements a sequence of integers which enumerata the basis gates.
    =#
    phase::Int8
    seq::Vector{Int64}
end

"""
Perform sequence multiplication by appending gate sequence on the left.
"""
function left_multiply!(multiplier_seq::GateSeq, gate_seq::GateSeq)
    gate_seq.phase = multiplier_seq.phase * gate_seq.phase
    prepend!(gate_seq.seq, multiplier_seq.seq)
    return
end

"""
Perform sequence multiplication by appending gate sequence on the left.
"""
function left_multiply(multiplier_seq::GateSeq, gate_seq::GateSeq)
    return GateSeq(multiplier_seq.phasee * gate_seq.phase, vcat(multiplier_seq.seq, gate_seq.seq))
end

"""
Perform sequence multiplication by appending integer on the left.
"""
function left_multiply!(multiplier::Int64, gate_seq::GateSeq)
    insert!(gate_seq.seq, 0, multiplier)
    return
end

"""
Perform sequence multiplication by appending integer on the left.
"""
function left_multiply(multiplier::Int64, gate_seq::GateSeq)
    return GateSeq(gate_seq.phase, vcat([multiplier], gate_seq.seq))
end

"""
Perform conjugation, this is equivalent to reverting the sequence and multiplying by -1.
"""
function adjoint!(gate_seq::GateSeq)
    gate_seq.seq = -reverse(gate_seq.seq)
    return
end

"""
Perform conjugation, this is equivalent to reverting the sequence and multiplying by -1.
"""
function adjoint(gate_seq::GateSeq)
    return GateSeq(gate_seq.phase, -reverse(gate_seq.seq))
end

function eval_seq(gate_seq::GateSeq, basis)
    gate_seq.phase * reduce((a,b) -> 
                            if b > 0
                                a*basis[b]
                            elseif b < 0
                                a*inv(basis[-b])
                            else
                                a
                            end,
                            gate_seq.seq; init=I)
end

