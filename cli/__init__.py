"""Command-line interface for impact projections
"""

import os
import click
from impactlab_tools.utils.files import get_file_config
import generate.generate as gg
import generate.aggregate as ga


# This is your main entry point
@click.group(context_settings={'help_option_names': ['-h', '--help']})
def impactcalculations_cli():
    """Launch impact projection calculations"""


@impactcalculations_cli.command(
    help='Post-process aggregation of impact projections'
)
@click.argument('confpath', type=click.Path())
def aggregate(confpath):
    """Run the impact projection aggregation system with configuration file"""
    file_configs = get_file_config(confpath)
    ga.main(file_configs)


@impactcalculations_cli.command(
    help='Generate impact projections from configuration file'
)
@click.argument('confpath', type=click.Path())
@click.option('-c', '--conf', nargs=1, default='', multiple=True,
              help='Additional KEY=VALUE configuration option.')
def generate(confpath, conf):
    """Run the impact projection generate system with configuration file"""
    file_configs = get_file_config(confpath)
    arg_configs = dict(arg.split('=') for arg in conf)
    configs_out = file_configs.update(arg_configs)
    gg.main(configs_out)


@impactcalculations_cli.command(
    help='Generate diagnostic impact projection run from configuration file'
)
@click.argument('confpath', type=click.Path())
def diagnose(confpath):
    """Run the impact projection diagnostic system with configuration path"""
    file_configs = get_file_config(confpath)

    diagnostic_configs = {
        'filter-region': 'USA.14.608',
        'outputdir': os.path.join(os.getcwd(), 'temp'),  # PWD/temp
        'singledir': 'single',
        'mode': 'writecalcs',
    }

    file_configs.update(diagnostic_configs)
    gg.main(file_configs)
