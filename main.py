import stim, sinter, json
import numpy as np
from math import sqrt
from scipy.optimize import curve_fit
from noise import NoiseParams, NoiseModel

if __name__ == "__main__":
    with open("default_input.json", "r") as read_file:
        args = json.load(read_file)

    noise_params = NoiseParams.transmon(args["qubit_technology"][0]["parameters"])
    noise_model = NoiseModel.transmon(noise_params.ps)

    tasks = []
    rounds = 1
    for d in range(3, 13, 2):
        circuit = stim.Circuit.generated(
            "surface_code:rotated_memory_z", rounds=1, distance=d
        )
        circuit = noise_model.noisy_circuit(circuit)
        tasks += [sinter.Task(circuit=circuit, json_metadata={"d": d})]

    task_stats = sinter.collect(
        num_workers=args["number_of_cores"],
        tasks=tasks,
        decoders=["pymatching"],
        max_shots=100_000_000,
        max_errors=1000,
        print_progress=False,
    )

    xs, ys, es = [], [], []
    for stats in task_stats:
        xs += [stats.json_metadata["d"]]
        ys += [stats.errors / stats.shots]
        es += [sqrt(ys[-1] * (1 - ys[-1]) / stats.shots)]

    xs, ys, es = (np.array(_) for _ in [xs, ys, es])
    inds = np.where(es / ys > 0.0001)[0]
    xs, ys, es = (_[inds] for _ in [xs, ys, es])

    p_opt, p_cov = curve_fit(
        lambda d, a, b: a - (d + 1) / 2 * b, xs, np.log(ys), sigma=es / ys
    )
    mean = np.array(p_opt)
    std = np.sqrt(np.diagonal(p_cov))

    t1, t2, tM, tR = (
        noise_params.t1,
        noise_params.t2,
        noise_params.tM,
        noise_params.tR,
    )

    output = {
        "parity_check_time": {
            "value": 1e6 * (tM + rounds * (4 * t2 + 2 * t1 + tM + tR)),
            "unit": "μs",
        },
        "fit": {
            "functional_form": "exp(a - (d+1)/2 * b)",
            "fitting_parameters": {
                "a": {"value": mean[0], "error": std[0]},
                "b": {"value": mean[1], "error": std[1]},
            },
        },
    }

    with open("output.json", "w") as write_file:
        json.dump(output, write_file)
