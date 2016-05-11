import sys, os
import standard
from loadmodels import basedir
from impacts import weather, effectset, caller
from adaptation import adapting_curve
import cProfile, pstats, StringIO

get_model = effectset.get_model_server
pvals = effectset.ConstantPvals(.5)

standard.preload()

for clim_scenario, clim_model, weatherbundle in weather.iterate_bundles(basedir):
    print clim_scenario, clim_model
    for econ_scenario, econ_model, economicmodel in adapting_curve.iterate_econmodels():
        print econ_scenario, econ_model

        pr = cProfile.Profile()
        pr.enable()

        if True:
            #calculation, dependencies, curve, baseline_get_predictors = caller.call_prepare('adaptation.mortality_allages_notime', weatherbundle, economicmodel, pvals['interpolated_mortality_allages'])
            calculation, dependencies, curve, baseline_get_predictors = caller.call_prepare('adaptation.mortality_65plus_notime', weatherbundle, economicmodel, pvals['interpolated_mortality_65plus'])
        else:
            gcpid = 'GHA2003_BRA_national_mortality_all'
            calculation, dependencies = caller.call_prepare('impacts.health.' + gcpid, weatherbundle, economicmodel, pvals[gcpid])
            baseline_get_predictors = None
        
        effectset.small_test(weatherbundle, calculation, baseline_get_predictors, num_regions=1)
        #effectset.write_ncdf('.', "InterpolatedMortalityAllAges", weatherbundle, calculation, baseline_get_predictors, "Mortality for all ages, with interpolation and adaptation through interpolation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies)

        pr.disable()

        break
    break

s = StringIO.StringIO()
sortby = 'cumulative'
ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
ps.print_stats()
#ps.print_callers(.5, 'sum')
print s.getvalue()
