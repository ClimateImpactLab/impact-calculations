"""
Compute mortality for DM2009_USA_national_mortality_all, using a gender pooled, binned model.

Model computes mortality per day; MonthlyDayBins scales by 12, so further multiply by 365.25 / 12
"""

from openest.generate.stdlib import *

def prepare_raw_spr(spreadrow, pvals, get_model, get_data):
    print(spreadrow['DMAS ID'])
    model_tas = get_model(spreadrow['DMAS ID'])
    print(model_tas)

    return Transform(
        MonthlyDayBins(model_tas, 'deaths/100000people/day', pval=pvals['tas'], weather_change=c2f),
        'deaths/100000people/day', 'deaths/person/year', lambda mortrate: (365.25 / 12.) * mortrate / 100000., 'convert to deaths/person/year', "MonthlyDayBins scales by 12, so further multiply by 365.25 / 12."), []
