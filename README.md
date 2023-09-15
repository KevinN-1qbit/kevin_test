# qaret-sk
This repo contains the Julia source code of the Solovay-Kitaev (SK) algorithm. The implementation is based on the paper by M.Dawson and A. Nielsen https://arxiv.org/abs/quant-ph/0505030.

### Requirements:
* Julia 1.8.5 (2023-01-08)
### Packages used:
* LinearAlgebra  
* StaticArrays  
* NearestNeighbors  
* JLD  
* Distances  
* IterTools  

### Usage example
A minimal example on how to run the algorithm is given in `test.jl` file.

### Some notes on doing sequence search over KD-Tree
The relevant file is `gate_library.jl`. It contains the following functions:
* `create_library()` - creates a 2D matrix (library of gates) where each column is an integer sequence of the basis gates that need to be multiplied. This library needs to be computed ones and could be stored on a drive for reuse.
* `find_closest_u()` - performs a linear search over the 2D matrix (library of gates). Since the search is linear, it is slow. We would like to implement the search step using KD-Trees from `NearestNeighbors` package.
* `Point` - a struct that attempts to implement a point data structure for a KD-Tree. The idea is to supply a vector of points to a `BallTree` and call relevant search functions on the `BallTree` to search for the closest unitary to the target unitary.

### On the importance of the search step
Pleaser refer to the outline of the SK algorithm in Section 3 of the referenced paper. Note that the algorithm is recursive and at the base case (n==0) it performs a search over a library. This step is denoted as `Return basic approximation to U`. Since, the base case is fairly expensive, it needs to be very fast. Therefore, we aim for a fast search over a KD-Tree.

### Additional usefull libraries for an extra context
SK algorithm is implemented in Qiskit (Python library). Please refer to `solovay_kitaev_synthesis.py` of the Qiskit library.

# Local Devepment with Docker

## Build the image
Ensure Docker is installed and run the following command from the root folder, which has the docker-compose.yml file:

```
docker-compose build
```

## Start up the Docker containers
Start up the docker containers with this command:
```
docker-compose up -d
```


# Running Smoke Tests
To run the smoke tests, after the containers are up and running you can run this command:
```
docker exec tests python3 sk/sk_smoke_tests.py
```