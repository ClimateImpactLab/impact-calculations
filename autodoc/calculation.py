import glob
from impactlab_tools.utils import files
from openest.generate import formatting
from generate import caller, loadmodels, pvalses
from interpret import calculator, specification, container, configs
from adaptation import csvvfile

config = files.get_allargv_config()
if 'models' in config:
    config = configs.merge(config, config['models'][0])
    csvvs = files.configpath(config['csvvs'])
    csvvpath = glob.glob(csvvs)[0]
    csvv = csvvfile.read(csvvpath)
    #specconf = config['models'][0]['specification']

    model, csvvs, module, specconf = next(container.get_modules(config))

    clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel = loadmodels.single(container.get_bundle_iterator(config))
    pvals = pvalses.ConstantPvals(.5)

    calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(csvv, module, weatherbundle, economicmodel, pvals["doc"], specconf=specconf, config=config, standard=False)
else:
    csvv = csvvfile.read(files.configpath(specconf['csvvpath']))
    specconf = config['specification']

    covariator = specification.create_covariator(config)
    model = specification.create_curvegen(csvv, covariator, ['universe'], farmer='full', specconf=specconf)
    calculation = calculator.create_calculation(specconf['calculation'], dict(default=model))

print "\nLaTeX:"
print formatting.format_latex(calculation)

print "\nJulia:"
print formatting.format_julia(calculation)
