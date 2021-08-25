from contextlib import contextmanager
from copy import deepcopy
from tempfile import TemporaryDirectory
from pathlib import Path

from generate.generate import main as main_generate

@contextmanager
def tmpdir_projection(cfg, cfg_name, projection_module=main_generate, outdir_parameter="outputdir"):
    """Context manager to generate projection in tmpdir, then cleanup output

    Parameters
    ----------
    cfg : dict
        Run configuration dict.
    cfg_name : str
    projection_module : a function
        a function generating and writing projection output, taking a config and config name as first parameters 
    outdir_parameter : str 
        the key in the `projection_module` config that points to the output directory in which `projection_module` writes data.

    Yields
    ------
    tempdir_path : pathlib.Path
    """
    cfg = deepcopy(cfg)  # so we don't overwrite values in `cfg`.
    with TemporaryDirectory() as tmpdirname:

        tempdir_path = Path(tmpdirname)
        cfg[outdir_parameter] = str(tempdir_path)

        projection_module(cfg, cfg_name)
        yield tempdir_path
