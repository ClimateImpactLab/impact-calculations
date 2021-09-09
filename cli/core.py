import os
from pathlib import Path
import click
from yaml import safe_load
from impactlab_tools.utils.files import get_file_config
from interpret.configs import merge_import_config
from generate.generate import main as ggmain
from generate.aggregate import main as gamain


# This is your main entry point
@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def impactcalculations_cli():
    """Launch impact projection calculations"""


@impactcalculations_cli.command(help="Post-process aggregation of impact projections")
@click.argument("confpath", type=click.Path())
def aggregate(confpath):
    """Run the impact projection aggregation system with configuration file"""
    file_configs = get_file_config(confpath)
    # Interpret "import" in configs here while we have file path info.
    file_configs = merge_import_config(file_configs, confpath.parent)
    gamain(file_configs)


@impactcalculations_cli.command(
    help="Generate impact projections from configuration file"
)
@click.argument("confpath", type=click.Path())
@click.option(
    "-c",
    "--conf",
    nargs=1,
    multiple=True,
    help="Additional KEY=VALUE configuration option.",
)
def generate(confpath, conf):
    """Run the impact projection generate system with configuration file"""
    confpath = Path(confpath)
    file_configs = get_file_config(confpath)
    # Interpret "import" in configs here while we have file path info.
    file_configs = merge_import_config(file_configs, confpath.parent)

    # Parse CLI config values as yaml str before merging.
    arg_configs = {}
    for k, v in (arg.strip().split("=") for arg in conf):
        arg_configs[k] = safe_load(v)
    file_configs.update(arg_configs)

    # For legacy purposes
    if not file_configs.get("config_name"):
        file_configs["config_name"] = str(confpath.stem)

    ggmain(file_configs)


@impactcalculations_cli.command(
    help="Generate diagnostic impact projection run from configuration file"
)
@click.argument("confpath", type=click.Path())
def diagnostic(confpath):
    """Run the impact projection diagnostic system with configuration path"""
    confpath = Path(confpath)
    file_configs = get_file_config(confpath)
    # Interpret "import" in configs here while we have file path info.
    file_configs = merge_import_config(file_configs, confpath.parent)

    # For legacy purposes
    if not file_configs.get("config_name"):
        file_configs["config_name"] = str(confpath.stem)

    diagnostic_configs = {
        "filter-region": "USA.14.608",
        "outputdir": os.path.join(os.getcwd(), "temp"),  # PWD/temp
        "singledir": "single",
        "mode": "writecalcs",
    }

    file_configs.update(diagnostic_configs)
    ggmain(file_configs)
