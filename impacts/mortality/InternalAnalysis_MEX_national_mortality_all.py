"""
Mortality calculation for InternalAnalysis_MEX_national_mortality_all.
"""
from openest.generate.stdlib import *

def prepare_raw_spr(spreadrow, pvals, get_model, get_data):
    model_tas = get_model(spreadrow['DMAS ID'])

    return Transform(
        YearlyDayBins(model_tas, 'deaths/100000people/year', pval=pvals['tas']),
        'deaths/100000people/year', 'deaths/person/year', lambda x: x / 1e5,
        'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year."), []
