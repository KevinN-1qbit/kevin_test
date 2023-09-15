OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
rz(0.78539816339744831) q[0];
s q[0];
ry(0.78539816339744831) q[0];
s q[1];
cx q[0],q[1];
