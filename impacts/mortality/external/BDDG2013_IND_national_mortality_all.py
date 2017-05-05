"""
Mortality calculation for BDDG2013_IND_national_mortality_all.
"""

from openest.generate.stdlib import *

def prepare(pvals, get_model, get_data):
    model_tas = get_model(TODO) # TODO
    mortality_rates, mortality_version = get_data('mortality-deathrates', 'deaths/person')

    return Instabase(
        Scale(
            #Sum(
                YearlyDayBins(model_tas, 'portion', pval=pvals['tas'], weather_change=c2f),
            #    YearlyDayBins(model_pr, 'portion', pval=pvals['pr'])), # Need to calculate terciles
            mortality_rates, 'portion', 'deaths/person'),
        2012, lambda x, y: x - y, units='deaths/person'), [mortality_version]

