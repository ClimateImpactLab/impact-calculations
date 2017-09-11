import numpy as np
import weather
from adaptation import covariates

do_econ_model_only = None
do_econ_scenario_only = None #{'rcp45': ['SSP4', 'SSP1'], 'rcp85': ['SSP4', 'SSP3']}

single_clim_model = 'CCSM4'
single_clim_scenario = 'rcp85'
single_econ_model = 'high'
single_econ_scenario = 'SSP3'

def single(bundle_iterator):
    allecons = []
    for econ_model, econ_scenario, economicmodel in covariates.iterate_econmodels():
        allecons.append((econ_scenario, econ_model, economicmodel))

    allclims = []
    for clim_scenario, clim_model, weatherbundle in bundle_iterator:
        allclims.append((clim_scenario, clim_model, weatherbundle))

    allexogenous = []
    for econ_scenario, econ_model, economicmodel in allecons:
        for clim_scenario, clim_model, weatherbundle in allclims:
            if clim_scenario != single_clim_scenario or clim_model != single_clim_model:
                continue
            if single_econ_scenario is not None:
                if econ_scenario[:4] == single_econ_scenario and econ_model == single_econ_model:
                    return clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel
                continue
            
            if (do_econ_scenario_only is not None and econ_scenario[0:4] != do_econ_scenario_only[clim_scenario][0]) or (do_econ_model_only is not None and econ_model != do_econ_model_only[0]):
                continue

            return clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

def random_order(bundle_iterator):
    print "Loading models..."
    allecons = []
    for econ_model, econ_scenario, economicmodel in covariates.iterate_econmodels():
        allecons.append((econ_scenario, econ_model, economicmodel))

    allclims = []
    for clim_scenario, clim_model, weatherbundle in bundle_iterator:
        allclims.append((clim_scenario, clim_model, weatherbundle))

    allexogenous = []
    for econ_scenario, econ_model, economicmodel in allecons:
        for clim_scenario, clim_model, weatherbundle in allclims:
            # Drop PIK GDP-32 (it's USA-only)
            if econ_model == 'PIK GDP-32':
                continue
            if do_econ_model_only is not None and econ_model not in do_econ_model_only:
                continue
            if do_econ_scenario_only is not None and econ_scenario[0:4] not in do_econ_scenario_only[clim_scenario]:
                continue
            # Drop SSP1 with RCP 8.5
            if econ_scenario[:4] == 'SSP1' and clim_scenario == 'rcp85':
                continue

            allexogen = (clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel)
            allexogenous.append(allexogen)

    allexogenous = np.random.permutation(allexogenous)
    for clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in allexogenous:
        print clim_scenario, clim_model, econ_scenario, econ_model
        yield clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel
