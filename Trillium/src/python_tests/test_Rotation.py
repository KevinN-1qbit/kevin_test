from ..python_wrapper.Rotation import *
import pytest
from math import pi

@pytest.fixture 
def ro():
    return Rotation(3, 0, [], [])


def test_is_tgate(ro):
    Xpi8 = Rotation(1,1,['x'],[0])
    I    = Rotation(1,1)
    Zpi2 = Rotation(1,0,['z'],[0])
    Zpi4 = Rotation(1,-2,['z'],[0])

    cases    = [Xpi8, I, Zpi2, Zpi4]
    expected = [True, False, False, False]
    results  = []

    for each in cases:
        results.append(each.is_tgate())
    assert expected == results


def test_eq(ro):
    Xpi8    = Rotation(1,1,['x'],[0])
    Xpi8n   = Rotation(1,-1,['x'],[0])
    Zpi2    = Rotation(1,0,['z'],[0])
    Zpi2_2  = Rotation(1,0,['z'],[0])
    I1      = Rotation(1,0)
    I2      = Rotation(2,1)

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