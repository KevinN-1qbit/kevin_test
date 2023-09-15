include("skalg.jl")
include("parser.jl")
include("utils.jl")
include("gates.jl")
include("gate_library.jl")

function est_rec(error_budget)
    # from https://arxiv.org/pdf/quant-ph/0505030.pdf (7)
    e0 = 0.14
    c_approx = 1.4
    if error_budget > e0
        return 0
    end
    return max(ceil(Int, log(log(error_budget*c_approx^2) / log(e0*c_approx^2)) / log(3/2)), 0)
end

function run_pipeline(input_file, output_file, error_budget)
    qasm = open(io->read(io, String), input_file)
    nast, instances = parse_into_unitaries(qasm, error_budget)
    @info "number of SK gates: $(length(instances))"

    seq_length = 10
    basis = [to_su2(H), to_su2(T), to_su2(T')]
    lib = create_library_generator(basis, seq_length)
    tree = create_kd_tree(basis, lib)
    rec = est_rec(error_budget/length(instances))
    @info "recurrence level: $(rec)"

    results = Vector{SKResult}(undef, length(instances))
    @time begin
        Threads.@threads for i in 1:length(instances)
            results[i] = run_sk(instances[i], seq_length, rec, basis, norm_dist, error_budget/length(instances), tree)
        end
    end

    total_error = sum(map(r -> r.error, results))
    @info "Total error $(total_error)"

    new_nast = replace_marked(nast, results)
    new_ast = flatten(new_nast)
    println("Final gate count: $(length(new_ast.prog))")

    io = open(output_file, "w")
    OpenQASM.print_qasm(io, new_ast)
    close(io)
    
    return total_error
end

if abspath(PROGRAM_FILE) == @__FILE__
    input_file = ARGS[1]
    output_file = ARGS[2]
    error_budget = parse(Float64, ARGS[3])
    run_pipeline(input_file, output_file, error_budget)
end

