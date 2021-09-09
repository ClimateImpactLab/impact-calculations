import numpy as np
from interpret.variables import interpret_ds_transform


def test_interpret_ds_transform_scalarname():
    """Tests that interpret_ds_transform() gives scalar if `name` arg is float

    If this fails it might be that FastDataset interface has changed. I'm so
    sorry if you're reading this.
    """
    scalar = 2.5

    class MockFastDataset(object):
        """Mocking FastDataset because I'm allergic to FastData*s.
        """
        def __init__(self):
            class MockValues(object):
                _values = np.ones((1, 3))
            self.coords = {}
            self.original_coords = []
            self.variables = {'foobar': MockValues}
            self._values = MockValues

        def __getitem__(self, x):
            return self.variables[x]

    victim = interpret_ds_transform(str(scalar), {})
    out = victim(MockFastDataset())
    # MockFastDataset is essentially empty with metadata for (1, 3) array. Goal
    # is to have array filled with our scalar as float.
    assert (out.values == np.array([[scalar] * 3], dtype='float')).all()
