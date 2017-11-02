import glob
from impactlab_tools.utils import files
from openest.generate import formatting
from interpret import calculator, specification
from adaptation import csvvfile

config = files.get_allargv_config()
if 'models' in config:
    csvvs = files.configpath(config['models'][0]['csvvs'])
    csvvpath = glob.glob(csvvs)[0]
    csvv = csvvfile.read(csvvpath)
    specconf = config['models'][0]['specification']
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
