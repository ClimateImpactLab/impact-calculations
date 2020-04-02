"""Format a calculation in LaTeX and Julia.

Translates the calculations performed in a given specification
configuration file into both LaTeX text and Julia commands. If there
are multiple models in the spec. configuration, only the first is
reported.

Called as:
```
python -m autodoc.calculation <spec-config.yml>
```

"""

import glob
from impactlab_tools.utils import files
from openest.generate import formatting
from generate import caller, loadmodels, pvalses
from interpret import calculator, specification, container, configs
from adaptation import csvvfile

# Read the spec. config
config = files.get_allargv_config()
if 'models' in config:
    config = configs.merge(config, config['models'][0])
    # Load the CSVV content
    csvvs = files.configpath(config['csvvs'])
    csvvpath = glob.glob(csvvs)[0]
    csvv = csvvfile.read(csvvpath)
    #specconf = config['models'][0]['specification']

    # Translate this config. into a module
    model, csvvs, module, specconf = next(container.get_modules(config))

    # Read a single weather dataset
    clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel = loadmodels.single(container.get_bundle_iterator(config))
    pvals = pvalses.ConstantPvals(.5)

    # Construct the calculation
    calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(csvv, module, weatherbundle, economicmodel, pvals["doc"], specconf=specconf, config=config, standard=False)
else:
    # Assume that there is a specification option
    csvv = csvvfile.read(files.configpath(specconf['csvvpath']))
    specconf = config['specification']

    # Construct the covariates
    covariator = specification.create_covariator(config)
    model = specification.create_curvegen(csvv, covariator, ['universe'], farmer='full', specconf=specconf)

    # Construct the calculation
    calculation = calculator.create_calculation(specconf['calculation'], dict(default=model))

## Outputs

print("\nLaTeX:")
print((formatting.format_latex(calculation)))

print("\nJulia:")
print((formatting.format_julia(calculation)))
