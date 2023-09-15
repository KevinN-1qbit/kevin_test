using OpenQASM
using OpenQASM.Types: Instruction, MainProgram, VersionNumber
using StaticArrays
using LinearAlgebra

include("utils.jl")
include("skalg.jl")
include("gate_sequence.jl")

mutable struct NestedAST
    version::VersionNumber
    prog::Vector{Vector{Any}}

    NestedAST(version) = new(version, Vector{Any}[])
end

flatten(nast::NestedAST) = MainProgram(nast.version, reduce(vcat, nast.prog))

"""
Parses cargs from OpenQASM into a single float.
cargs expressions follow the grammar
<expr> : <token> | <expr> <binop> <expr>
where <token> is a OpenQASM.Types.Token, and
binop is one of + - / *
"""
function parse_cargs(cargs)
    function parse_carg(carg)
        if typeof(carg) <: OpenQASM.Types.Token
            if carg.str == "pi"
                return pi
            end
            return parse(Float64, carg.str)
        else
            if typeof(carg) <: OpenQASM.Types.Neg
                return -parse_carg(carg.val)
            elseif typeof(carg) <: Tuple
                val1, binop, val2 = carg
                parsed1 = parse_carg(val1)
                parsed2 = parse_carg(val2)
                if binop.str == "+"
                    return parsed1 + parsed2
                elseif binop.str == "-"
                    return parsed1 - parsed2
                elseif binop.str == "*"
                    return parsed1 * parsed2
                elseif binop.str == "/"
                    return parsed1 / parsed2
                end
            else
                @warn "Unknown value for carg $carg"
            end
        end
    end

    return map(x->parse_carg(x), cargs)
end

"""
Produces an SU(2) unitary from a instruction containing
a standard qelib1 gate.
"""
function inst_to_unitary(inst)
    cargs = parse_cargs(inst.cargs)

    if inst.name == "u1" || inst.name == "p" || inst.name == "rz"
        u = rotate_around_z(cargs[1])
    elseif inst.name == "u2"
        u = rotate_around_z(cargs[1] + pi/2) * rotate_around_x(pi/2) * rotate_around_z(cargs[2] - pi/2)
    elseif inst.name == "u3" || inst.name == "U"
        u = rotate_around_z(cargs[2]+3*pi) * rotate_around_x(pi/2) * rotate_around_z(cargs[1]+pi) * rotate_around_x(pi/2) * rotate_around_z(cargs[3])
    elseif inst.name == "rx"
        u = rotate_around_x(cargs[1])
    elseif inst.name == "ry"
        u = rotate_around_y(cargs[1])
    elseif inst.name == "sx"
        u = rotate_around_x(pi/2)
    end
    u = to_su2(u)
    return u
end

"""
Parses a qasm file into a sequence of SKInst structs containing
gates that require SK decomposition, and a nested tree containing marked
locations for replacements.

The format of the nested is as follows:
The body of the main program is a vector of vectors of instructions.
Each vector contains a single element that requires decomposition, or 
it contains only element(s) which are part of the basis gate set.
"""
function parse_into_unitaries(qasm::String, error_budget::Float64)
    ast = OpenQASM.parse(qasm)
    insts = SKInst[]
    new_ast = NestedAST(ast.version)
    curr = 1
    for (line, expr) in enumerate(ast.prog)
        if typeof(expr) <: OpenQASM.Types.Instruction
            if expr.name in ["u1", "u2", "u3", "rx", "ry", "rz", "U", "p"]
                u = inst_to_unitary(expr)
                if line != curr
                    push!(new_ast.prog, ast.prog[curr:line-1])
                end
                push!(new_ast.prog, [expr])
                push!(insts, SKInst(length(new_ast.prog), u, expr.qargs, error_budget))
                curr = line + 1
            elseif expr.name in ["cz", "ch", "ccx", "crz", "cu1", "cu3"]
                @warn "unsupported gate $(expr.name), circuit must be transpiled before SK"
            elseif expr.name in ["cx", "x", "y", "z", "h", "s", "sdg", "t", "tdg", "sx"]
                continue # SK not needed
            else
                @warn "unrecognized gate $(expr.name)"
            end
        end

        if typeof(line) <: OpenQASM.Types.Gate
            @warn "notimpl"
            continue
        end
    end

    if curr != length(ast.prog)
        push!(new_ast.prog, ast.prog[curr:length(ast.prog)])
    end

    return new_ast, insts
end

"""
Produces an Instruction from a GateSeq sequence.
"""
function to_qasm(seq::Vector{Int64}, basis::Vector{String}, qargs)
    get_inv(x) = getindex([1, 3, 2], x) 
    insts = []
    for i in seq
        if i == 0
            continue
        end
        if i < 0
            i = get_inv(abs(i)) # nb: does not mutate
        end
        push!(insts, Instruction(basis[i], [], qargs))
    end
    return insts
end

"""
Takes a list of SKResults, and replaces the nested_ast elements with 
a vector of instructions representing the SK decomposition of the 
original gate
"""
function replace_marked(nested_ast::NestedAST, diff::Vector{SKResult})
    Threads.@threads for i in diff
        new_insts = to_qasm(i.gate_seq.seq, ["h", "t", "tdg"], i.qargs) # TODO: impl arbitrary bases
        nested_ast.prog[i.index] = new_insts
    end
    return nested_ast
end

function to_string(ast)
    iobuf = IOBuffer(append=true)
    for i in ast.prog
        write(iobuf, string(i))
    end
    return String(take!(iobuf))
end
