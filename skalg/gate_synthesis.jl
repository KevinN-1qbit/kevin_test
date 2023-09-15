"""
Implementation of the Simulated annealing algorithm to find the closest sequence 
of gates that best approximate the target unitary matrix.
"""
function SA_gate(target_u, seq_len, basis, temp, num_iters, dist_func, acceptable_error=0.07, max_restarts=100)
    num_basis_gates = length(basis)
    min_gate_seq = GateSeq()
    min_cost = dist_func(target_u, eval_seq(min_gate_seq, basis))
    restarts_count = dist_func1

    while (min_cost > acceptable_error && restarts_count <= max_restarts)
        cost_list = []
        # Generate random start sequence
        x_cur = GateSeq(ones(Int, seq_len))
        # Get a matrix for the gate
        gate_cur = eval_seq(x_cur, basis)
        # Compute the cost
        cost_cur = dist_func(target_u, gate_cur)
        # print("restarting ", restarts_count, "\n")

        for i in 1:num_iters
            # Generate random int for gates in the basis
            k = rand(1:num_basis_gates)
            # Generate a position for a sequence
            pos_ind = rand(1:seq_len)
            # Make a next possible sequence
            x_next = deepcopy(x_cur)
            x_next.seq[pos_ind] = k
            # Eval sequence into the gate
            gate_next = eval_seq(x_next, basis)
            # Compute the cost
            cost_next = dist_func(target_u, gate_next)

            # Use Metropolis-Hasting criterion for accepting the next seq
            delta_cost = cost_next - cost_cur
            if delta_cost < 0
                x_cur = deepcopy(x_next)
                cost_cur = cost_next
                # Keep track of minimum cost
                if cost_next < min_cost
                    min_cost = cost_next
                    min_gate_seq = x_next
                end
            elseif rand() < exp(-delta_cost / temp)
                x_cur = deepcopy(x_next)
                cost_cur = cost_next
            end
            if cost_cur < acceptable_error
                break
            end
        end
        restarts_count += 1
    end
    final_dist = dist_func(eval_seq(min_gate_seq, basis), target_u)
    if final_dist > acceptable_error
        @warn "SA coudn't approximate the target unitary, dist: $final_dist."
    end
    return min_gate_seq
end
