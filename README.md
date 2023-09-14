# qarrot-ftqc
The input parameters for the FTQC emulator are as follows:

| Parameter                   | Description                                                      |
|---------------------------- | --------------------------------------------------------------   |
| number_of_cores (optional)  | Number of cores for the Monte Carlo sampling. Defaults to 8.     |
| code                        | ... Default is [rotated_surface_code]                            |
| protocol                    | ... Default is [memory_z]                                        |
| decoder                     | ... Default is [MWPM]                                            |
| qubit_technology            | Physical qubit technology... Default is [transmon]               |
| noise_model                 | ... Default is [circuit_noise_with_idling]                       |