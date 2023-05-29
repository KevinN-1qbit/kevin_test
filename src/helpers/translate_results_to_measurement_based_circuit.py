def translate_to_measurement_based(result, original_circuit, num_qubits, output_path):
    result_circuit = []
    for tick, rotation in result.items():
        if rotation:
            for rotation_id in rotation:
                rotation_obj = original_circuit[rotation_id]

                if rotation_obj.operation_type != 3:
                    # If measurement
                    if rotation_obj.operation_type == -1:
                        rotation_string = "Measure "
                        rotation_string += rotation_obj.operation_sign

                    # If rotation
                    else:
                        rotation_string = "Rotate "
                        rotation_string += rotation_obj.operation_sign + str(
                            rotation_obj.operation_type
                        )

                    rotation_string += ": "

                    for i in range(num_qubits):
                        if i in rotation_obj.x:
                            rotation_string += "X"
                        elif i in rotation_obj.z:
                            rotation_string += "Z"
                        else:
                            rotation_string += "I"

                    result_circuit.append(rotation_string)

    write_to_txt_file(result_circuit, output_path)


def write_to_txt_file(result_circuit, path):
    with open(path, "w") as f:
        for line in result_circuit:
            f.write(line + "\n")
