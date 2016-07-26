from datastore import population

halfweight = population.SpaceTimeBipartiteData(1981, 2100, None)

for clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in loadmodels.random_order():
    print targetdir
    print econ_model, econ_scenario

    get_population = lambda year0, year1: halfweight.load_population(year0, year1, econ_model, econ_scenario)

    # Estimate E[T]

    # Estimate E[D[T]], E[D[Y]], E[D[P]]

    # Estimate E[T D[T]], E[T D[Y]], E[T D[P]]
