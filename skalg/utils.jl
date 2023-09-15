using LinearAlgebra
using StaticArrays
using NearestNeighbors
using Distances, LinearAlgebra
include("gates.jl")


function trace_dist(u, v)
    return abs(0.5 * tr(sqrt(inv(u - v) * (u - v))))
end

function norm_dist(u, v)
    return norm(u - v)
end

"""
Convert a 2x2 unitary to a unitary with determinant 1.0.
"""
function to_su2(u)
    return sqrt(1 / Complex(det(u))) * u
end


function get_global_phase(u)
    return sqrt(Complex(det(u)))
end

"""
Compute the real angle theta, axis and global phase of a unitary matrix.
"""
function get_axis_theta_global_phase(u)
    global_phase = get_global_phase(u)
    # Compute the angle of rotation theta.
    if abs(real(tr(u)) / 2) > 1.0
        theta = 0
    else
        theta = 2 * acos(real(tr(u)) / 2)
    end
    nx = tr(u * X) / (-2im * sin(theta / 2))
    ny = tr(u * Y) / (-2im * sin(theta / 2))
    nz = tr(u * Z) / (-2im * sin(theta / 2))
    # global_phase_conj = conj(global_phase)
    # nx = global_phase_conj * tr(u * X) / (-2im * sin(theta / 2))
    # ny = global_phase_conj * tr(u * Y) / (-2im * sin(theta / 2))
    # nz = global_phase_conj * tr(u * Z) / (-2im * sin(theta / 2))
    axis = real([nx, ny, nz])
    return axis, theta, global_phase
end


"""
Produce the single-qubit rotation operator.
"""
function rotate_around_vector(vec, theta)
    return cos(theta / 2) * I - 1im * sin(theta / 2) * (vec[1] * X + vec[2] * Y + vec[3] * Z)
end


function rotate_around_x(theta)
    return rotate_around_vector([1.0, 0.0, 0.0], theta)
end

function rotate_around_y(theta)
    return rotate_around_vector([0.0, 1.0, 0.0], theta)
end

function rotate_around_z(theta)
    return rotate_around_vector([0.0, 0.0, 1.0], theta)
end

function uniterize(u)
    u_, s_, v_ = svd(u)
    return u_ * inv(v_)
end

"""
Group commutator decomposition.
"""
function gc_decomp(u)
    function permute_columns(m)
        col1 = m[:, 1]
        col2 = m[:, 2]
        return m = hcat(col2, col1)
    end

    # Do unitarization of u for numerical accuracy
    u = uniterize(u)

    # Get axis and theta for the operator.
    axis, theta, global_phase = get_axis_theta_global_phase(u)
    # The angle phi comes from eq 10 in 'The Solovay-Kitaev Algorithm' by Dawson, Nielsen.
    phi = 2.0 * asin(sqrt(sqrt((0.5 - 0.5 * cos(theta / 2)))))

    v = rotate_around_x(phi)
    w = rotate_around_y(phi)

    # Decompose u as PDP'
    p = eigvecs(u)
    # Decompose vwv'w' as CAC'
    c = eigvecs(v * w * inv(v) * inv(w))
    # c = eigvecs(v * w * inv(w * v))

    # Then we want PDP' = SCAC'S' for some S. Then P = SC. Solve for S.
    s_a = p * inv(c)
    s_b = permute_columns(eigvecs(u)) * inv(c)

    # Check if the eigendecomposition gave the right order of column vecs
    if opnorm(s_a * v * w * inv(v) * inv(w) * inv(s_a) - u) > opnorm(s_b * v * w * inv(v) * inv(w) * inv(s_b) - u)
        s = s_b
    else
        s = s_a
    end

    v_hat = s * v * inv(s)
    w_hat = s * w * inv(s)

    # if opnorm(v_hat * w_hat * inv(v_hat) * inv(w_hat) - u) > opnorm(u - [1 0; 0 1])
    #     @warn "gc_decomp failed to find good approximator" u
    # end
    return v_hat, w_hat
end


# u = to_su2(1 / sqrt(2) * SA[1 1; 1 -1])
# u = to_su2(SA[1 0; 0 im])
# u = -H * T
# display(u)
# axis, angle, global_phase = get_axis_theta_global_phase(u)
# res = global_phase * (cos(angle / 2) * I - im * sin(angle / 2) * (axis[1] * X + axis[2] * Y + axis[3] * Z))
# norm(res - u, 2)

# scaler = 0.001
# theta = scaler * rand() * 2 * pi
# phi = scaler * rand() * 2 * pi
# lambda = scaler * rand() * 2 * pi
# u = create_u(theta, phi, lambda)

# vh, wh, global_phase = gc_decomp(u)
# reconstructed_u = global_phase * vh * wh * vh' * wh'
# norm(u - reconstructed_u)

# print(r, "\n")
# base = [H, T]
# lib = create_library(base, 5)
# display(lib)
# data = [vec(X), vec(X), vec(X)]
# tree = KDTree(data, Euclidean())
# eigv = eigvecs(H)
# display(eigv)
# H * eigv[:,2]

# p1 = SA[1, 0]
# p2 = SA[2, 0]
# hcat(p1, p2)
