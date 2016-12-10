"""
Compute mortality for B2012_USA_national_mortality_all.

Temperature is used as fraction of days within each bin, so result
from MonthlyDayBins is 365.25 / 12 larger than expected-- scaled.
"""

from openest.generate.stdlib import *

def prepare_raw_spr(spreadrow, pvals, get_model, get_data):
    model_tas = get_model(spreadrow['DMAS ID'])

    return Transform(
        MonthlyDayBins(model_tas, 'deaths/100000people/year', pval=pvals['tas'], weather_change=c2f),
        'deaths/100000people/year', 'deaths/person/year', lambda mortrate: (mortrate / 100000.) / (365.25 / 12.), 'convert to deaths/person/year', "MonthlyDayBins is 365.25 / 12 larger than expected"), []
