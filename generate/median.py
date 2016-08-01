import sys, os
import standard, loadmodels
from impacts import weather, effectset
from adaptation import adapting_curve

get_model = effectset.get_model_server
pvals = effectset.ConstantPvals(.5)

do_only = "interpolation"

basedir = '/shares/gcp/BCSD/grid2reg/cmip5'

outputdir = sys.argv[1]

standard.preload()

for clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in loadmodels.random_order():
    print clim_scenario, clim_model
    print econ_scenario, econ_model
    targetdir = os.path.join(outputdir, 'median', clim_scenario, clim_model, econ_model, econ_scenario)

    if os.path.exists(targetdir):
        continue

    print targetdir
    os.makedirs(targetdir)

    effectset.make_pval_file(targetdir, pvals)
    standard.produce(targetdir, weatherbundle, economicmodel, get_model, pvals, country_specific=False, do_only=do_only, do_farmers=True)

    # Generate historical baseline
    historybundle = weather.RepeatedHistoricalWeatherBundle.make_historical(weatherbundle, None)
    standard.produce(targetdir, historybundle, economicmodel, get_model, pvals, country_specific=False, suffix='-histclim', do_only=do_only)
