"""
Mortality calculation for BCDGS2013_USA_national_mortality_all.
"""
from openest.generate.stdlib import *

def prepare_raw_spr(spreadrow, pvals, get_model, get_data):
    model_tas = get_model(spreadrow['DMAS ID'])
    mortality_rates, mortality_version = get_data('mortality-deathrates', 'deaths/person')

    return Scale(
        MonthlyDayBins(model_tas, 'portion', pval=pvals['tas']),
        mortality_rates, 'portion', 'deaths/person/year', logscalefunc), [mortality_version]

