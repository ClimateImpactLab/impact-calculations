"""
Compute mortality from yearly day bins, as deaths per person.
"""

from openest.generate.stdlib import *

mortality_tas_url = "/collection/retrieve_hierarchical_normal_merge_muid?collection_id=525dded88309fa1cbb844c96&simuids=53594152434fd733f817dd29,53594152434fd733f817dd2b,53594152434fd733f817dd2d,53594152434fd733f817dd2f,53594153434fd733f817dd31,53594153434fd733f817dd33,53594153434fd733f817dd35,53594153434fd733f817dd37,53594153434fd733f817dd39,53594153434fd733f817dd3b,53594152434fd733f817dd2a,53594152434fd733f817dd2c,53594152434fd733f817dd2e,53594153434fd733f817dd30,53594153434fd733f817dd32,53594153434fd733f817dd34,53594153434fd733f817dd36,53594153434fd733f817dd38,53594153434fd733f817dd3a,53594153434fd733f817dd3c"
# Generated from "/collection/generate_hierarchical_normal_merge_muid?collection_id=525dded88309fa1cbb844c96&meta_ids=5279840c8309fa1a04a6ada1%2C531f48ea434fd70e335f3c75&weights=1%2C1&iterations=100000"

def prepare_raw(pvals, get_model, get_data):
    model_tas = get_model(mortality_tas_url)
    mortality_rates, mortality_version = get_data('mortality-deathrates', 'deaths/person')

    return Scale(
        YearlyDayBins(model_tas, 'portion', pval=pvals['tas']),
        mortality_rates, 'portion', 'deaths/person/year', logscalefunc), [mortality_version]
