OPENQASM 2.0;
include "qelib1.inc";
qreg q[16];
creg c[16];
h q[1];
t q[14];
rz(pi) q[12];
t q[12];
t q[1];
cx q[12],q[14];
rz(pi) q[14];
cx q[1],q[12];