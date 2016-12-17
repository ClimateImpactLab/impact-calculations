"""
Provides iterators of WeatherReaders (typically a historical and a
future reader).
"""
import os
from dailyreader import DailyWeatherReader, YearlyBinnedWeatherReader

def discover_models(basedir):
    """
    basedir points to directory with both 'historical', 'rcp*'
    """
    # Collect the entire complement of models
    models = os.listdir(os.path.join(basedir, 'historical'))

    for scenario in os.listdir(basedir):
        if scenario[0:3] != 'rcp':
            continue

        for model in models:
            pastdir = os.path.join(basedir, 'historical', model)
            futuredir = os.path.join(basedir, scenario, model)

            yield scenario, model, pastdir, futuredir

### Reader discovery functions
# Yield

def discover_tas_binned(basedir):
    for scenario, model, pastdir, futuredir in discover_models(basedir):
        pasttemplate = os.path.join(pastdir, 'tas/tas_Bindays_aggregated_historical_r1i1p1_' + model + '_%d.nc')
        futuretemplate = os.path.join(futuredir, 'tas/tas_Bindays_aggregated_' + scenario + '_r1i1p1_' + model + '_%d.nc')

        pastreader = YearlyBinnedWeatherReader(pasttemplate, 1981, 'DayNumber')
        futurereader = YearlyBinnedWeatherReader(futuretemplate, 2006, 'DayNumber')

        yield scenario, model, pastreader, futurereader

def discover_variable(basedir, variable):
    for scenario, model, pastdir, futuredir in discover_models(basedir):
        pasttemplate = os.path.join(pastdir, variable, variable + '_day_aggregated_historical_r1i1p1_' + model + '_%d.nc')
        futuretemplate = os.path.join(futuredir, variable, variable + '_day_aggregated_' + scenario + '_r1i1p1_' + model + '_%d.nc')

        pastreader = DailyWeatherReader(pasttemplate, 1981, variable)
        futurereader = DailyWeatherReader(futuretemplate, 2006, variable)

        yield scenario, model, pastreader, futurereader
