from contextlib import contextmanager
from copy import deepcopy
from tempfile import TemporaryDirectory
from pathlib import Path

from generate.generate import main


@contextmanager
def tmpdir_projection(cfg, runid):
    """Context manager to generate projection in tmpdir, then cleanup output

    Parameters
    ----------
    cfg : dict
        Run configuration dict.
    runid : str

    Yields
    ------
    tempdir_path : pathlib.Path
    """
    cfg = deepcopy(cfg)  # so we don't overwrite values in `cfg`.
    with TemporaryDirectory() as tmpdirname:

        tempdir_path = Path(tmpdirname)
        cfg["outputdir"] = str(tempdir_path)

        main(cfg, runid)
        yield tempdir_path
