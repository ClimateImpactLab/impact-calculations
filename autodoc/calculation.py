from impactlab_tools.utils import files
from interpret import calculator, specification
from adaptation import csvvfile

config = files.get_allargv_config()

csvv = csvvfile.read(config['csvv'])

covariator = None #specification.create_covariator(config)
model = specification.create_curvegen(csvv, covariator, ['universe'], farmer='full', specconf=config['specification'])
calculation = calculator.create_calculation(config['calculation'], models)

print calculation
print calculation.format('latex')
print calculation.format('julia')
