from src.python_wrapper.Measure import *
import pytest
from math import pi

@pytest.fixture 
def mr():
    return Measure(3, 0, [], [])


def test_eq(mr):
    Xpi8    = Measure(1,True,['x'],[0])
    Xpi8n   = Measure(1,False,['x'],[0])
    Zpi2    = Measure(1,True,['z'],[0])
    Zpi2_2  = Measure(1,True,['z'],[0])
    I1      = Measure(1,False)
    I2      = Measure(2,True)

    cases    = [Xpi8, Xpi8n, Zpi2, Zpi2_2, I1, I2]
    expected = [False,False,True,False,True]
    results  = []

    i = 1
    for each in cases:
        if i < len(cases):
            results.append((each == cases[i]))
            i += 1
        else:
            break

    assert expected == results