"""
Provides iterators of WeatherReaders (typically a historical and a
future reader).
"""
import os
from dailyreader import DailyWeatherReader, YearlyBinnedWeatherReader
from yearlyreader import YearlyWeatherReader, YearlyCollectionWeatherReader, YearlyArrayWeatherReader

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

            if not os.path.exists(futuredir):
                print "Missing %s %s" % (scenario, model)
                continue

            yield scenario, model, pastdir, futuredir

### Reader discovery functions
# Yields (scenario, model, pastreader, futurereader)

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

def discover_derived_variable(basedir, variable, suffix):
    for scenario, model, pastdir, futuredir in discover_models(basedir):
        pasttemplate = os.path.join(pastdir, variable + '_' + suffix, variable + '_day_aggregated_historical_r1i1p1_' + model + '_%d.nc')
        futuretemplate = os.path.join(futuredir, variable + '_' + suffix, variable + '_day_aggregated_' + scenario + '_r1i1p1_' + model + '_%d.nc')

        if os.path.exists(pasttemplate % (1981)) and os.path.exists(futuretemplate % (2006)):
            pastreader = DailyWeatherReader(pasttemplate, 1981, variable)
            futurereader = DailyWeatherReader(futuretemplate, 2006, variable)

            yield scenario, model, pastreader, futurereader

def discover_yearly(basedir, vardir, rcp_only=None):
    """
    Returns scenario, model, filepath for the given variable
    baseline points to directory with 'rcp*'
    """

    for scenario in os.listdir(basedir):
        if scenario[0:3] != 'rcp':
            continue
        if rcp_only is not None and scenario != rcp_only:
            continue

        for filename in os.listdir(os.path.join(basedir, scenario, vardir)):
            root, ext = os.path.splitext(filename)
            model = root.split('_')[-1]
            filepath = os.path.join(basedir, scenario, vardir, filename)
            pastpath = filepath.replace(scenario, 'historical')
    
            yield scenario, model, pastpath, filepath

def discover_yearly_variable(basedir, vardir, variable, rcp_only=None):
    """
    Returns scenario, model, YearlyReader for the given variable
    baseline points to directory with 'rcp*'
    """

    for scenario, model, pastpath, filepath in discover_yearly(basedir, vardir, rcp_only=rcp_only):
        yield scenario, model, YearlyWeatherReader(pastpath, variable), YearlyWeatherReader(filepath, variable)

def discover_yearly_array(basedir, vardir, variable, labels, rcp_only=None):
    """
    Returns scenario, model, YearlyReader for the given variables
    baseline points to directory with 'rcp*'
    """

    for scenario, model, pastpath, filepath in discover_yearly(basedir, vardir, rcp_only=rcp_only):
        yield scenario, model, YearlyArrayWeatherReader(pastpath, variable, labels), YearlyArrayWeatherReader(filepath, variable, labels)

def discover_yearly_collection(basedir, vardir, variables, rcp_only=None):
    """
    Returns scenario, model, YearlyReader for the given variables
    baseline points to directory with 'rcp*'
    """

    for scenario, model, pastpath, filepath in discover_yearly(basedir, vardir, rcp_only=rcp_only):
        yield scenario, model, YearlyCollectionWeatherReader(pastpath, variables), YearlyCollectionWeatherReader(filepath, variables)

def discover_yearly_corresponding(basedir, scenario, vardir, model, variable):
    for filename in os.listdir(os.path.join(basedir, scenario, vardir)):
        root, ext = os.path.splitext(filename)
        thismodel = root.split('_')[-1]

        if thismodel == model:
            filepath = os.path.join(basedir, scenario, vardir, filename)
            return YearlyWeatherReader(filepath, variable)
