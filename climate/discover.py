"""
Provides iterators of WeatherReaders (typically a historical and a
future reader).
"""
import os, re, copy
import numpy as np
from impactlab_tools.utils import files
from openest.generate import fast_dataset
from reader import ConversionWeatherReader, RegionReorderWeatherReader, HistoricalCycleReader, RenameReader
from dailyreader import DailyWeatherReader, YearlyBinnedWeatherReader, MonthlyBinnedWeatherReader
from yearlyreader import YearlyWeatherReader, YearlyDayLikeWeatherReader
import pattern_matching

re_dotsplit = re.compile("\.(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)")

def standard_variable(name, mytimerate, **config):
    if '/' in name:
        if os.path.exists(files.configpath(name)):
            return discover_versioned(files.configpath(name), os.path.basename(name), **config)

    if '.' in name:
        chunks = re_dotsplit.split(name)
        if len(chunks) > 1:
            var = standard_variable(chunks[0], mytimerate, **config)
            for chunk in chunks[2:]:
                var = interpret_transform(var, chunk)
            return var
        
    assert mytimerate in ['day', 'month', 'year']

    if mytimerate == 'day':
        polyedvars = ['tas', 'tasmax']
    
        if name in polyedvars:
            return discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/" + name), name, **config)
        for ii in range(2, 10):
            if name in ["%s-poly-%d" % (var, ii) for var in polyedvars]:
                return discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/" + name), name, **config)
            if name in ["%s%d" % (var, ii) for var in polyedvars]:
                return discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/%s-poly-%s" % (name[:-1], name[-1])), '%s-poly-%s' % (name[:-1], name[-1]), **config)
        if name == 'prmm':
            return discover_variable(files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level'), 'pr', **config)
        
    if mytimerate == 'month':
        if name in ['tas', 'tasmax']:
            return discover_day2month(standard_variable(name, 'day', **config),  lambda arr, dim: np.mean(arr, axis=dim))
        if name == 'tasbin':
            return discover_binned(files.sharedpath('climate/BCSD/aggregation/cmip5_bins/IR_level'), 'year', # Should this be year?
                                   'tas/tas_Bindays_aggregated_%scenario_r1i1p1_%model_%d.nc', 'SHAPENUM', 'DayNumber')
        if name == 'edd':
            return discover_rename(
                discover_binned(files.sharedpath('climate/BCSD/Agriculture/Degree_days/snyder'), 'month',
                                'Degreedays_aggregated_%scenario_%model_cropwt_%d.nc', 'SHAPENUM', 'EDD_agg', include_patterns=False), {'EDD_agg': 'edd', 'month': 'time'})
        if name == 'prmm':
            discover_iterator = standard_variable(name, 'day', **config)
            return discover_rename(
                discover_day2month(discover_iterator, lambda arr, dim: np.sum(arr, axis=dim)), {'pr': 'prmm'})

    if mytimerate == 'year':
        polyedvars = ['tas-cdd-20', 'tas-hdd-20']
        polyedvars_daily = ['tas', 'tasmax'] # Currently do these as sums
        
        if name in polyedvars:
            return discover_versioned_yearly(files.sharedpath("climate/BCSD/hierid/popwt/annual/" + name), name, **config)
        for ii in range(2, 10):
            if name in ["%s-poly-%d" % (var, ii) for var in polyedvars]:
                return discover_versioned_yearly(files.sharedpath("climate/BCSD/hierid/popwt/annual/" + name), name, **config)
            if name in ["%s%d" % (var, ii) for var in polyedvars]:
                return discover_versioned_yearly(files.sharedpath("climate/BCSD/hierid/popwt/annual/%s-poly-%s" % (name[:-1], name[-1])), '%s-poly-%s' % (name[:-1], name[-1]), **config)

        if name in polyedvars_daily:
            return discover_day2year(standard_variable(name, 'day', **config), lambda arr, dim: np.sum(arr, axis=dim))
        for ii in range(2, 10):
            if name in ["%s-poly-%d" % (var, ii) for var in polyedvars_daily]:
                return discover_day2year(standard_variable(name, 'day', **config), lambda arr, dim: np.sum(arr, axis=dim))
            if name in ["%s%d" % (var, ii) for var in polyedvars_daily]:
                return discover_day2year(standard_variable(name, 'day', **config), lambda arr, dim: np.sum(arr, axis=dim))
            
    raise ValueError("Unknown variable: " + name)

def interpret_transform(var, transform):
    if transform == 'histclim':
        return discover_makehist(var)

    if transform[:7] == 'gddkdd(':
        lower, upper = tuple(map(float, transform[7:-1].split(',')))
        return discover_makegddkdd(var, lower, upper)
    
    assert False, "Cannot interpret transformation %s" % transform

def discover_models(basedir, **config):
    """
    basedir points to directory with both 'historical', 'rcp*'
    Aware configuration options:
     - pattern_matching
     - only_rcp
     - only-models
    """
    # Collect the entire complement of models
    models = os.listdir(os.path.join(basedir, 'historical'))

    for scenario in os.listdir(basedir):
        if scenario[0:3] != 'rcp':
            continue

        if config.get('rcp_only', scenario) != scenario:
            continue

        if 'only-models' in config:
            modelset = config['only-models']
        else:
            modelset = copy.copy(models)
            if config.get('include_patterns', True):
                modelset += pattern_matching.rcp_models[scenario].keys()

        for model in modelset:
            pastdir = os.path.join(basedir, 'historical', model)
            futuredir = os.path.join(basedir, scenario, model)

            if not os.path.exists(futuredir):
                continue # Silently drop

            if not os.path.exists(pastdir):
                if model in pattern_matching.rcp_models[scenario]:
                    pastdir = os.path.join(basedir, 'historical',
                                           pattern_matching.rcp_models[scenario][model])
                    if not os.path.exists(pastdir):
                        print "Missing pattern-base for %s %s" % (scenario, model)
                        continue

            yield scenario, model, pastdir, futuredir

### Reader discovery functions
# Yields (scenario, model, pastreader, futurereader)

def discover_binned(basedir, timerate, template, regionvar, ncvar, **config):
    for scenario, model, pastdir, futuredir in discover_models(basedir, **config):
        get_template = lambda scenario, model: template.replace("%scenario", scenario).replace("%model", model)
        pasttemplate = os.path.join(pastdir, get_template('historical', model))
        futuretemplate = os.path.join(futuredir, get_template(scenario, model))
        
        if timerate == 'year':
            pastreader = YearlyBinnedWeatherReader(pasttemplate, 1981, regionvar, ncvar)
            futurereader = YearlyBinnedWeatherReader(futuretemplate, 2006, regionvar, ncvar)
        elif timerate == 'month':
            pastreader = MonthlyBinnedWeatherReader(pasttemplate, 1981, regionvar, ncvar)
            futurereader = MonthlyBinnedWeatherReader(futuretemplate, 2006, regionvar, ncvar)

        yield scenario, model, pastreader, futurereader

def discover_variable(basedir, variable, withyear=True, **config):
    for scenario, model, pastdir, futuredir in discover_models(basedir, **config):
        if withyear:
            if model in pattern_matching.rcp_models[scenario]:
                pasttemplate = os.path.join(pastdir, variable, variable + '_day_aggregated_historical_r1i1p1_' + pattern_matching.rcp_models[scenario][model] + '_%d.nc')
            else:
                pasttemplate = os.path.join(pastdir, variable, variable + '_day_aggregated_historical_r1i1p1_' + model + '_%d.nc')
            futuretemplate = os.path.join(futuredir, variable, variable + '_day_aggregated_' + scenario + '_r1i1p1_' + model + '_%d.nc')
            if not os.path.exists(futuretemplate % 2006):
                continue

            pastreader = DailyWeatherReader(pasttemplate, 1981, 'SHAPENUM', variable)
            futurereader = DailyWeatherReader(futuretemplate, 2006, 'SHAPENUM', variable)

            yield scenario, model, pastreader, futurereader
        else:
            if model in pattern_matching.rcp_models[scenario]:
                pastpath = os.path.join(pastdir, variable, variable + '_annual_aggregated_historical_r1i1p1_' + pattern_matching.rcp_models[scenario][model] + '.nc')
            else:
                pastpath = os.path.join(pastdir, variable, variable + '_annual_aggregated_historical_r1i1p1_' + model + '.nc')
            futurepath = os.path.join(futuredir, variable, variable + '_aggregated_' + scenario + '_r1i1p1_' + model + '.nc')
            if not os.path.exists(futurepath):
                continue

            pastreader = YearlyWeatherReader(pastpath, variable)
            futurereader = YearlyWeatherReader(futurepath, variable)

            yield scenario, model, pastreader, futurereader

def discover_derived_variable(basedir, variable, suffix, withyear=True, **config):
    for scenario, model, pastdir, futuredir in discover_models(basedir, **config):
        if withyear:
            pasttemplate = os.path.join(pastdir, variable + '_' + suffix, variable + '_day_aggregated_historical_r1i1p1_' + model + '_%d.nc')
            futuretemplate = os.path.join(futuredir, variable + '_' + suffix, variable + '_day_aggregated_' + scenario + '_r1i1p1_' + model + '_%d.nc')

            if os.path.exists(pasttemplate % (1981)) and os.path.exists(futuretemplate % (2006)):
                pastreader = DailyWeatherReader(pasttemplate, 1981, 'SHAPENUM', variable)
                futurereader = DailyWeatherReader(futuretemplate, 2006, 'SHAPENUM', variable)

                yield scenario, model, pastreader, futurereader
        else:
            pastpath = os.path.join(pastdir, variable + '_' + suffix, variable + '_annual_aggregated_historical_r1i1p1_' + model + '.nc')
            futurepath = os.path.join(futuredir, variable + '_' + suffix, variable + '_annual_aggregated_' + scenario + '_r1i1p1_' + model + '.nc')

            pastreader = YearlyWeatherReader(pastpath, variable)
            futurereader = YearlyWeatherReader(futurepath, variable)

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

            if not os.path.exists(pastpath):
                pastpath = filepath # Both contained in one file
                
            yield scenario, model, pastpath, filepath

def discover_yearly_variables(basedir, vardir, *variables, **kwargs):
    """
    Returns scenario, model, YearlyReader for the given variable
    baseline points to directory with 'rcp*'
    """

    for scenario, model, pastpath, filepath in discover_yearly(basedir, vardir, rcp_only=kwargs.get('rcp_only')):
        yield scenario, model, YearlyWeatherReader(pastpath, variable), YearlyWeatherReader(filepath, variable)

def discover_yearly_corresponding(basedir, scenario, vardir, model, variable):
    for filename in os.listdir(os.path.join(basedir, scenario, vardir)):
        root, ext = os.path.splitext(filename)
        thismodel = root.split('_')[-1]

        if thismodel == model:
            filepath = os.path.join(basedir, scenario, vardir, filename)
            return YearlyWeatherReader(filepath, variable)

    if 'pattern' in model and os.path.isdir(os.path.join(basedir, scenario, vardir, 'pattern')):
        for filename in os.listdir(os.path.join(basedir, scenario, vardir, 'pattern')):
            root, ext = os.path.splitext(filename)
            thismodel = root.split('_')[-1]

            if thismodel == model:
                filepath = os.path.join(basedir, scenario, vardir, 'pattern', filename)
                # Reorder these results, which use hierid, to SHAPENUM order
                return RegionReorderWeatherReader(YearlyWeatherReader(filepath, variable, timevar='time'))

def discover_convert(discover_iterator, time_conversion, ds_conversion):
    """Convert the readers coming out of a discover iterator."""
    for scenario, model, pastreader, futurereader in discover_iterator:
        newpastreader = ConversionWeatherReader(pastreader, time_conversion, ds_conversion)
        newfuturereader = ConversionWeatherReader(futurereader, time_conversion, ds_conversion)
        yield scenario, model, newpastreader, newfuturereader
        
def discover_versioned(basedir, variable, version=None, reorder=True, **config):
    """Find the most recent version, if none specified."""
    if version is None:
        version = '%v'
    
    for scenario, model, pastdir, futuredir in discover_models(basedir, **config):
        pasttemplate = os.path.join(pastdir, "%d", version + '.nc4')
        futuretemplate = os.path.join(futuredir, "%d", version + '.nc4')

        precheck_past = DailyWeatherReader.precheck(pasttemplate, 1981, 'hierid', variable)
        if precheck_past:
            print "Skipping %s %s (past): %s" % (scenario, model, precheck_past)
            continue
        precheck_future = DailyWeatherReader.precheck(futuretemplate, 2006, 'hierid', variable)
        if precheck_future:
            print "Skipping %s %s (future): %s" % (scenario, model, precheck_future)
        
        if reorder:
            pastreader = RegionReorderWeatherReader(DailyWeatherReader(pasttemplate, 1981, 'hierid', variable))
            futurereader = RegionReorderWeatherReader(DailyWeatherReader(futuretemplate, 2006, 'hierid', variable))
        else:
            pastreader = DailyWeatherReader(pasttemplate, 1981, 'hierid', variable)
            futurereader = DailyWeatherReader(futuretemplate, 2006, 'hierid', variable)
            
        yield scenario, model, pastreader, futurereader

def discover_versioned_yearly(basedir, variable, version=None, reorder=True, **config):
    """Find the most recent version, if none specified."""
    if version is None:
        version = '%v'
    
    for scenario, model, pastdir, futuredir in discover_models(basedir, **config):
        pasttemplate = os.path.join(pastdir, "%d", version + '.nc4')
        futuretemplate = os.path.join(futuredir, "%d", version + '.nc4')

        if reorder:
            pastreader = RegionReorderWeatherReader(YearlyDayLikeWeatherReader(pasttemplate, 1981, 'hierid', variable))
            futurereader = RegionReorderWeatherReader(YearlyDayLikeWeatherReader(futuretemplate, 2006, 'hierid', variable))
        else:
            pastreader = YearlyDayLikeWeatherReader(pasttemplate, 1981, 'hierid', variable)
            futurereader = YearlyDayLikeWeatherReader(futuretemplate, 2006, 'hierid', variable)
            
        yield scenario, model, pastreader, futurereader

def discover_makehist(discover_iterator):
    """Mainly used with .histclim for, e.g., lincom (since normal historical is at the bundle level)."""
    for scenario, model, pastreader, futurereader in discover_iterator:
        yield scenario, model, RenameReader(pastreader, lambda x: x + '.histclim'), HistoricalCycleReader(pastreader, futurereader)

def discover_makegddkdd(discover_iterator, lower, upper):
    for scenario, model, pastreader, futurereader in discover_iterator:
        yield scenario, model, GDDKDDReader(pastreader, lower, upper), GDDKDDReader(futurereader, lower, upper)

def discover_rename(discover_iterator, name_dict):
    for scenario, model, pastreader, futurereader in discover_iterator:
        yield scenario, model, RenameReader(pastreader, name_dict), RenameReader(futurereader, name_dict)
        
def discover_day2month(discover_iterator, accumfunc):
    #time_conversion = lambda days: np.unique(np.floor((days % 1000) / 30.4167)) # Should just give 0 - 11
    time_conversion = lambda days: np.arange(12)
    def ds_conversion(ds):
        vars_only = ds.variables.keys()
        for name in ds.coords:
            if name in vars_only:
                vars_only.remove(name)
        used_coords = ds.coords
        if 'yyyyddd' in used_coords:
            del used_coords['yyyyddd']

        ds = fast_dataset.FastDataset({name: data_vars_time_conversion(name, ds, 'vars', accumfunc) for name in vars_only},
                                      coords={name: data_vars_time_conversion(name, ds, 'coords', accumfunc) for name in used_coords},
                                      attrs=ds.attrs)
        return ds
    
    return discover_convert(discover_iterator, time_conversion, ds_conversion)

def data_vars_time_conversion(name, ds, varset, accumfunc):
    if isinstance(ds, fast_dataset.FastDataset):
        if varset == 'vars':
            vardef = ds.original_data_vars[name]
        elif varset == 'coords':
            vardef = ds.original_coords[name]
        else:
            assert False, "Unknown varset."
    else:
        if varset == 'vars':
            vardef = (ds.variables[name].dims, ds.variables[name].values)
        elif varset == 'coords':
            vardef = ds.coords[name]
        else:
            assert False, "Unknown varset."
            
    if isinstance(vardef, tuple):
        try:
            dimnum = vardef[0].index('time')
        except:
            return vardef

        myshape = list(vardef[1].shape)
        myshape[dimnum] = 12
        result = np.zeros(tuple(myshape))
        for mm in range(12):
            beforeindex = [slice(None)] * len(vardef[0])
            beforeindex[dimnum] = slice(int(mm * 30.4167), int((mm+1) * 30.4167))
            afterindex = [slice(None)] * len(vardef[0])
            afterindex[dimnum] = mm
            result[tuple(afterindex)] = accumfunc(vardef[1][tuple(beforeindex)], dimnum)

        return (vardef[0], result)

    if name != 'time':
        return vardef

    return np.arange(12)

def discover_day2year(discover_iterator, accumfunc):
    time_conversion = lambda days: np.array([days[0] // 1000])
    def ds_conversion(ds):
        vars_only = ds.variables.keys()
        for name in ds.coords:
            if name in vars_only:
                vars_only.remove(name)
        used_coords = ds.coords
        if 'yyyyddd' in used_coords:
            del used_coords['yyyyddd']

        ds = fast_dataset.FastDataset({name: data_vars_time_conversion_year(name, ds, 'vars', accumfunc) for name in vars_only},
                                      coords={name: data_vars_time_conversion_year(name, ds, 'coords', accumfunc) for name in used_coords},
                                      attrs=ds.attrs)
        return ds
    
    return discover_convert(discover_iterator, time_conversion, ds_conversion)

def data_vars_time_conversion_year(name, ds, varset, accumfunc):
    if isinstance(ds, fast_dataset.FastDataset):
        if varset == 'vars':
            vardef = ds.original_data_vars[name]
        elif varset == 'coords':
            vardef = ds.original_coords[name]
        else:
            assert False, "Unknown varset."
    else:
        if varset == 'vars':
            vardef = (ds.variables[name].dims, ds.variables[name].values)
        elif varset == 'coords':
            vardef = ds.coords[name]
        else:
            assert False, "Unknown varset."
            
    if isinstance(vardef, tuple):
        try:
            dimnum = vardef[0].index('time')
        except:
            return vardef

        myshape = list(vardef[1].shape)
        myshape[dimnum] = 1
        result = np.zeros(tuple(myshape))
        beforeindex = [slice(None)] * len(vardef[0])
        afterindex = [slice(None)] * len(vardef[0])
        afterindex[dimnum] = 0
        result[tuple(afterindex)] = accumfunc(vardef[1][tuple(beforeindex)], dimnum)

        return (vardef[0], result)

    if name != 'time':
        return vardef

    return np.array([ds['time.year'][0]])
