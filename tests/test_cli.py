"""
White-box testing to ensure the CLI can be invoked and that it passes
args correctly.
"""

import os
import pytest
import click
from click.testing import CliRunner
import cli


@pytest.fixture
def tmpconf_path(tmpdir):
    """Creates a temporary config yaml, returning its path"""
    file = tmpdir.join("conf_file.yaml")
    file.write("k1: v1")
    return str(file)


@pytest.fixture
def ggmain_stub(mocker):
    """Mocks/stubs of ggmain, prints input for debugging
    """
    mocker.patch.object(
        cli, "ggmain", new=lambda *a: click.echo(a),
    )


@pytest.mark.parametrize("subcmd", [None, "generate", "diagnostic", "aggregate"])
def test_imperics_helpflags(subcmd):
    """Ensure all commands print error if given --help flag
    """
    runner = CliRunner()

    # Setup CLI args
    cli_args = ["--help"]
    if subcmd is not None:
        cli_args = [subcmd, "--help"]

    result = runner.invoke(cli.impactcalculations_cli, cli_args)

    assert "Error:" not in result.output


def test_generate_basic(tmpconf_path, ggmain_stub):
    """Check generate CLI subcommand with config path
    """
    runner = CliRunner()
    expected = f"({{'k1': 'v1', 'config_name': 'conf_file'}},)\n"
    result = runner.invoke(cli.impactcalculations_cli, ["generate", tmpconf_path])
    assert result.output == expected


def test_generate_extraconfigs(tmpconf_path, ggmain_stub):
    """Check generate CLI subcommand with config path and -c args
    """
    runner = CliRunner()
    expected = f"({{'k1': 'v1', 'k2': 'v2', 'k3': 'v3', 'config_name': 'conf_file'}},)\n"
    result = runner.invoke(
        cli.impactcalculations_cli, ["generate", tmpconf_path, "-c k2=v2", "-c k3=v3"]
    )
    assert result.output == expected


def test_diagnostic_basic(tmpconf_path, ggmain_stub):
    """Check diagnostic CLI subcommand with config path
    """
    runner = CliRunner()

    # Setup expected output
    diagnostic_configs = {
        "k1": "v1",
        "config_name": "conf_file",
        "filter-region": "USA.14.608",
        "outputdir": os.path.join(os.getcwd(), "temp"),  # PWD/temp
        "singledir": "single",
        "mode": "writecalcs",
    }
    expected = f"({diagnostic_configs},)\n"

    result = runner.invoke(cli.impactcalculations_cli, ["diagnostic", tmpconf_path])
    assert result.output == expected
