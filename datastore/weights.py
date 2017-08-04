import population, agecohorts

def interpret(config):
    assert 'weighting' in config
    econ_model = config['iam']
    econ_scenario = config['ssp']

    if config['weighting'] == 'population':
        halfweight = population.SpaceTimeBipartiteData(1981, 2100, None)
        return lambda year0, year1: halfweight.load_population(year0, year1, econ_model, econ_scenario)

    if config['weighting'] in agecohorts.columns:
        halfweight = agecohorts.SpaceTimeBipartiteData(1981, 2100, None)
        return lambda year0, year1: halfweight.load_population(year0, year1, econ_model, econ_scenario, config['weighting'])

    raise ValueError("Unknown weighting.")
