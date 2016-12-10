import sys, os, itertools
import standard, loadmodels
from impacts import weather, effectset
from adaptation import adapting_curve

mode = sys.argv[1]
assert mode in ['median', 'montecarlo']

get_model = effectset.get_model_server

do_only = "interpolation"

outputdir = sys.argv[1]

standard.preload()

for batch in itertools.count():
    for clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in loadmodels.random_order():
        print clim_scenario, clim_model
        print econ_scenario, econ_model
        if mode == 'median':
            pvals = effectset.ConstantPvals(.5)
            targetdir = os.path.join(outputdir, 'median', clim_scenario, clim_model, econ_model, econ_scenario)
        else:
            pvals = effectset.OnDemandRandomPvals()
            targetdir = os.path.join(outputdir, 'batch' + str(batch), clim_scenario, clim_model, econ_model, econ_scenario)

        if os.path.exists(targetdir):
            continue

        print targetdir
        os.makedirs(targetdir)

        effectset.make_pval_file(targetdir, pvals)
        standard.produce(targetdir, weatherbundle, economicmodel, get_model, pvals, do_only=do_only, do_farmers=True)

        # Generate historical baseline
        historybundle = weather.RepeatedHistoricalWeatherBundle.make_historical(weatherbundle, None if mode == 'median' else pvals['histclim'].get_seed())
        pvals.lock()

        effectset.make_pval_file(targetdir, pvals)

        standard.produce(targetdir, historybundle, economicmodel, get_model, pvals, country_specific=False, suffix='-histclim', do_only=do_only)
