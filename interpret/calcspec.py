"""Generation module for configurations with multiple specifications.

See docs/models.md for the programming structure this is designed to
follow. This module is used when the specification configuration is
organized in the form:

```
specifications:
    <name>:
        <configuration>
    ...
calculation:
    - <calculation>
```

"""

from copy import deepcopy
import numpy as np
from interpret import specification, configs, calculator
from adaptation import csvvfile


def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer="full", specconf=None, config=None):
    """Interpret configurations with multiple specifications

    Parameters
    ----------
    csvv : dict
        Various parameters and curve descriptions from CSVV file.
    weatherbundle : generate.weather.WeatherBundle
    economicmodel : adaptation.econmodel.SSPEconomicModel
    qvals : generate.pvalses.ConstantDictionary
    farmer : {"full", "noadapt", "incadapt"}, optional
        Adaptation scheme to use.
    specconf : dict or None, optional
        This is the model containing 'specifications' and 'calculation' keys.
    config : dict or None, optional

    Returns
    -------
    calculation
    List
    Callable
    """
    if specconf is None:
        specconf = {}
    if config is None:
        config = {}

    assert "calculation" in specconf
    assert "specifications" in specconf

    if config.get("report-variance", False):
        csvv["gamma"] = np.zeros(len(csvv["gamma"]))  # So no mistaken results
    else:
        csvvfile.collapse_bang(csvv, qvals.get_seed("csvv"))

    covariator = specification.create_covariator(
        specconf, weatherbundle, economicmodel, config, quiet=config.get("quiet", False), farmer=farmer
    )

    models = {}
    extras = dict(errorvar=csvvfile.get_errorvar(csvv))
    for key in specconf["specifications"]:
        modelspecconf = configs.merge(specconf, specconf["specifications"][key])

        this_csvv = deepcopy(csvv)
        diag_infix = ""

        # If used csvv-subset: option in specifications config:
        csvv_subset = modelspecconf.get("csvv-subset")
        if csvv_subset:
            this_csvv = csvvfile.subset(this_csvv, slice(*csvv_subset))
            diag_infix += "s%d-%d-" % tuple(csvv_subset)

        # If used csvv-reunit: option in specifications config:
        csvv_reunit = modelspecconf.get("csvv-reunit")
        if csvv_reunit:
            for reunit_spec in csvv_reunit:
                target_variable = str(reunit_spec["variable"])
                new_unit = str(reunit_spec["new-unit"])
                this_csvv["variables"][target_variable]["unit"] = new_unit

        # Subset to regions (i.e. hierids) to act on. Does config have a
        # filter-region?
        filter_region = config.get("filter-region")
        if filter_region:
            target_regions = [str(filter_region)]
        else:
            target_regions = weatherbundle.regions

        model = specification.create_curvegen(
            this_csvv,
            covariator,
            target_regions,
            farmer=farmer,
            specconf=modelspecconf,
            diag_infix=diag_infix
        )
        modelextras = dict(
            output_unit=modelspecconf["depenunit"],
            units=modelspecconf["depenunit"],
            curve_description=modelspecconf["description"],
        )
        models[key] = model
        extras[key] = modelextras

    calculation = calculator.create_calculation(
        specconf["calculation"], models, extras=extras
    )

    if covariator is None:
        return calculation, [], lambda region: {}
    else:
        return calculation, [], covariator.get_current
