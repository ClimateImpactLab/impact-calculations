from impactlab_tools.utils import files
from openest.generate import formatting
from interpret import calculator, specification
from adaptation import csvvfile

config = files.get_allargv_config()

csvv = csvvfile.read(files.configpath(config['csvvpath']))

covariator = None #specification.create_covariator(config)
model = specification.create_curvegen(csvv, covariator, ['universe'], farmer='full', specconf=config['specification'])
calculation = calculator.create_calculation(config['calculation'], dict(default=model))

print "\nLaTeX:"
print formatting.format_latex(calculation)

print "\nJulia:"
print formatting.format_julia(calculation)
