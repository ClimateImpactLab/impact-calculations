import numpy as np
import weather
from adaptation import adapting_curve

do_econ_model_only = ["OECD Env-Growth"]
do_econ_scenario_only = ['SSP3']

def random_order(climatebasedir):
    print "Loading models..."
    allecons = []
    for econ_model, econ_scenario, economicmodel in adapting_curve.iterate_econmodels():
        allecons.append((econ_scenario, econ_model, economicmodel))

    allclims = []
    for clim_scenario, clim_model, weatherbundle in weather.iterate_binned_bundles(climatebasedir):
        allclims.append((clim_scenario, clim_model, weatherbundle))

    allexogenous = []
    for econ_scenario, econ_model, economicmodel in allecons:
        for clim_scenario, clim_model, weatherbundle in allclims:
            # Drop PIK GDP-32 (it's USA-only)
            if econ_model == 'PIK GDP-32':
                continue
            if do_econ_model_only is not None and econ_model not in do_econ_model_only:
                continue
            if do_econ_scenario_only is not None and econ_scenario[0:4] not in do_econ_scenario_only:
                continue
            # Drop SSP1 with RCP 8.5
            if econ_scenario[:4] == 'SSP1' and clim_scenario == 'rcp85':
                continue

            allexogen = (clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel)
            allexogenous.append(allexogen)

    allexogenous = np.random.permutation(allexogenous)
    for clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in allexogenous:
        yield clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel
