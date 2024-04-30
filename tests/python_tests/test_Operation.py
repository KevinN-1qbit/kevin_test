from src.python_wrapper.Rotation import *
from src.python_wrapper.Measure import *
import pytest
from math import pi

@pytest.fixture 
def op():
    return Operation(3, [], [])

def test_is_commute(op):
    X    = Rotation(1,0,['x'],[0])
    Y    = Rotation(1,0,['y'],[0])
    Z    = Rotation(1,0,['z'],[0])
    XY   = Rotation(2,0,['x','y'],[0,1]) 
    IZ   = Rotation(2,0,['z'],[1])
    ZYZ  = Rotation(3,0,['z','y','z'],[0,1,2])
    XZY  = Rotation(3,0,['x','z','y'],[0,1,2])
 
    MX   = Measure(1,True,['x'],[0])
    MY   = Measure(1,True,['y'],[0])
    MZ   = Measure(1,True,['z'],[0])
    MIZ  = Measure(2,True,['z'],[1])
    MXY  = Measure(2,True,['x','y'],[0,1])
    MXZY = Measure(3,True,['x','z','y'],[0,1,2])

    cases = [
        [X,Y,Z,XY,X,Y,Z,XY,ZYZ,X,Y,Z,XY,X,Y,Z,XY,ZYZ],
        [MX,MY,MZ,MXY,MY,MZ,MX,IZ,MXZY,X,Y,Z,XY,Y,Z,X,IZ,XZY]
    ]

    expected = [True,True,True,True,False,False,False,False,False,True,True,True,True,False,False,False,False,False]
    results  = []

    for each_pair in zip(cases[0],cases[1]):
        results.append(each_pair[0].is_commute(each_pair[1]))

    assert expected == results


def test_is_identity(op):
    XIII = Rotation(4,0,['x'],[0])
    III  = Rotation(3,0)

    cases    = [XIII,III]
    expected = [False,True]
    results  = []
    for each in cases:
        results.append(each.is_identity())
    
    assert expected == results


def test_is_single_qubit(op):

    XIII = Rotation(4,0,['x'],[0])
    IZII = Rotation(4,0,['z'],[1])
    IIIY = Rotation(4,0,['y'],[3])
    YXII = Rotation(4,0,['y','x'],[0,1])
    YXZI = Rotation(4,0,['y','x','z'],[0,1,2])

    cases = [
        XIII,IZII,IIIY,YXII,YXZI
    ]
    expected = [True,True,True,False,False]
    results  = []

    for each in cases:
        results.append(each.is_single_qubit())

    assert expected == results

    
