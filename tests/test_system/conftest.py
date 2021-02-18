"""pytest pluggins available to tests within this directory.

These are pytest pluggins, you do not need to import these to use with tests.
"""

import pytest
import adaptation.csvvfile


@pytest.fixture(scope="module")
def _monkeymodule():
    """Hack to get a module-scoped monkeypatch pytest fixture"""
    from _pytest.monkeypatch import MonkeyPatch

    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope="module")
def static_mvn(_monkeymodule):
    """Makes stochastic, unstable multivariate normal draws purely deterministic with monkeypatch

    This fixture allows us to test software that depends on random
    multivariate normal (MVN) distribution draws, even if we're testing on
    different systems. We need this because multivariate normal distribution
    draws are infamous for their instability - even when seeding the RNG and
    pinning software dependency versions.
    """

    def mock_collapse_bang(data=None, seed=None):
        """Mock/stub adaptation.csvvfile.collapse_bang() to stabilize an MVN

        Note this stub has default arguments - unlike the original func. This
        helps prevent namespace conflicts.
        """
        if seed is None:
            data["gammavcv"] = None
        else:
            # MVN now just flips gamma in place of RNG draw...
            data["gamma"] = data["gamma"][::-1]
            data["gammavcv"] = None  # this will cause errors if used again

    _monkeymodule.setattr(adaptation.csvvfile, "collapse_bang", mock_collapse_bang)
