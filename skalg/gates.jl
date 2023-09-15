using StaticArrays
X = SA[0.0 1.0; 1.0 0.0]
Y = SA[0.0 -1.0im; 1.0im 0.0]
Z = SA[1.0 0.0; 0.0 -1.0]
I = SA[1.0 0.0; 0.0 1.0]
H = 1.0 / sqrt(2.0) * SA[1.0 1.0; 1.0 -1.0]
T = SA[1.0 0.0; 0.0 exp(im * pi / 4.0)]
S = SA[1.0 0; 0.0 1.0im]

"""
Create a u gate using the angles theta, phi and lambda.
"""
function create_u(theta, phi, lam)
    theta_half = theta / 2
    phase_1 = -exp(im * lam)
    phase_2 = exp(im * phi)
    phase_3 = exp(im * (phi + lam))
    return SA[cos(theta_half) phase_1*sin(theta_half); phase_2*sin(theta_half) phase_3*cos(theta_half)]
end
