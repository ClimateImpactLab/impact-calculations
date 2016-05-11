from impacts import weather, effectset, caller
from adaptation import adapting_curve

basedir = '/shares/gcp/BCSD/grid2reg/cmip'

pvals = effectset.ConstantPvals(.5)

for clim_scenario, clim_model, weatherbundle in weather.iterate_bundles(basedir):
    break

for econ_scenario, econ_model, economicmodel in adapting_curve.iterate_econmodels():
    break
     
print clim_scenario, clim_model, econ_scenario, econ_model
   
calculation, dependencies, curve, baseline_get_predictors = caller.call_prepare('adaptation.mortality_allages_notime', weatherbundle, economicmodel, pvals['interpolated_mortality_allages'])



#baseline_get_predictors('USA.2.84')
#curve.create('USA.2.84')
