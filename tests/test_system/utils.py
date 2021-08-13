from contextlib import contextmanager
from copy import deepcopy
from tempfile import TemporaryDirectory
from pathlib import Path

from generate.generate import main as main_generate
from generate.aggregate import main as main_aggregate


@contextmanager
def tmpdir_projection(cfg, cfg_name, projection_module=main_generate):
    """Context manager to generate projection in tmpdir, then cleanup output

    Parameters
    ----------
    cfg : dict
        Run configuration dict.
    cfg_name : str

    Yields
    ------
    tempdir_path : pathlib.Path
    """
    cfg = deepcopy(cfg)  # so we don't overwrite values in `cfg`.
    with TemporaryDirectory() as tmpdirname:

        tempdir_path = Path(tmpdirname)
        cfg["outputdir"] = str(tempdir_path)

        projection_module(cfg, cfg_name)
        yield tempdir_path
