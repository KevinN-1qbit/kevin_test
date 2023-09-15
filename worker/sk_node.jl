include("../skalg/main.jl")

using Redis
using JSON
using ConfParser
using Logging

# Configure the global logger to include debug messages
global_logger(Logging.SimpleLogger(stdout, Logging.Debug))

function handle_message(message)
    @info "handle_message() - $(message)"

    circuit_path = message["circuit_path"]
    error_budget = message["error_budget"]
    request_id = message["request_id"]
    output_path = retrieve(config, "SKNode", "output_path")

    sk_output_path = output_path * request_id * "_post_sk.qasm"
    accumulated_error = 0
    topic = request_id
    report_message = Dict()

    # Update the status to executing in get request topic
    try
        lpop(redis, topic)
        status_message = Dict("status" => "executing")
        rpush(redis, topic, JSON.json(status_message))
    catch e
        err_msg = "Failed to update status in get request topic : $(request_id) to executing: $(e)"
        @error err_msg
        throw(Exception(err_msg))
    end

    try
        accumulated_error = run_pipeline(circuit_path, sk_output_path, error_budget)
        report_message = Dict(
            "status" => "done",
            "sk_circuit_path" => sk_output_path,
            "accumulated_error" => accumulated_error
        )
        @debug "SK circuit input path: $(circuit_path)"
        @debug "SK circuit output path: $(sk_output_path)"
        @debug "error_budget: $(error_budget)"
        @debug "num_threads: $(Threads.nthreads())"
    catch e
        @error "error_message: $(e)"
        # Hardcode the error message for now
        e = "Something went wrong during the run."
        report_message = Dict(
            "status" => "failed",
            "message" => e
        )
    end

    @debug "report_message: $(report_message)"

    try
        # Serialize report content into a JSON string
        serialized_report_string = JSON.json(report_message)
        # Update the result and status in get request topic
        lpop(redis, topic)
        rpush(redis, topic, serialized_report_string)
    catch e
        err_msg = "Failed to update result in get request topic : $(request_id): $(e)"
        @error err_msg
        throw(Exception(err_msg))
    end

    @info "handle_message() - SK finished"

    # invoke GC here, before next job comes in
    GC.gc()
    GC.gc()
    GC.gc()
    GC.gc()
end


if abspath(PROGRAM_FILE) == @__FILE__
    @info "Starting julia SK node"
    config = ConfParse("config/server.conf")
    parse_conf!(config)

    redis_host = retrieve(config, "Redis", "host")
    redis_port = retrieve(config, "Redis", "port")
    timeout_interval = retrieve(config, "SKNode", "timeout_interval")
    request_topic = retrieve(config, "Redis", "sk_req")

    redis = RedisConnection(host=redis_host, port=parse(Int64, redis_port))

    while true
        try
            msg = lpop(redis, request_topic)
            if msg != nothing 
                @info "Redis message received"
                handle_message(JSON.parse(msg))
            else
                sleep(parse(Int64, timeout_interval))
            end
        catch e
            @error e
            rethrow(e)
        end
    end
end

