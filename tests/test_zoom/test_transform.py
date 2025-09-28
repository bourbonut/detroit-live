from detroit_live.zoom.transform import Transform, identity

def test_transform_1():
    assert identity == Transform(1, 0, 0)

def test_transform_2():
    transform = identity.scale(2.5)
    assert transform.scale(2) == Transform(5, 0, 0)

def test_transform_3():
    transform = identity.translate(2, 3)
    assert transform.translate(-4, 4) == Transform(1, -2, 7)
    assert transform.scale(2).translate(-4, 4) == Transform(2, -6, 11)

def test_transform_4():
    assert identity.translate(2, 3).scale(2)([4, 5]) == [10, 13]

def test_transform_5():
    assert identity.translate(2, 0).scale(2).apply_x(4) == 10

def test_transform_6():
    assert identity.translate(0, 3).scale(2).apply_y(5) == 13

def test_transform_7():
    assert identity.translate(2, 3).scale(2).invert([4, 5]) == [1, 1]

def test_transform_8():
    assert identity.translate(2, 0).scale(2).invert_x(4) == 1

def test_transform_9():
    assert identity.translate(0, 3).scale(2).invert_y(5) == 1

def test_transform_10():
    assert str(identity) == "translate(0,0) scale(1)"
