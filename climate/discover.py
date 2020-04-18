"""
Provides iterators of WeatherReaders (typically a historical and a
future reader).
"""

import os, re, copy
import numpy as np
from impactlab_tools.utils import files
from openest.generate import fast_dataset
from interpret import configs
from .reader import *
from .dailyreader import DailyWeatherReader, YearlyBinnedWeatherReader, MonthlyBinnedWeatherReader, MonthlyDimensionedWeatherReader
from .yearlyreader import YearlyWeatherReader, YearlyDayLikeWeatherReader
from . import pattern_matching

RE_FLOATING = r"[-+]?[0-9]*\.?[0-9]*"
re_dotsplit = re.compile("\.(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)")

def standard_variable(name, mytimerate, **config):
    if '/' in name:
        if os.path.exists(files.configpath(name)):
            return discover_versioned(files.configpath(name), os.path.basename(name), **config)

    if ' = ' in name:
        chunks = name.split(' = ')
        name = chunks[0].strip()
        defin = chunks[1].strip()
        return discover_rename(standard_variable(defin, mytimerate, **config), name)

    assert mytimerate in ['day', 'month', 'year']

    if ' * ' in name:
        chunks = name.split(' * ')
        left = chunks[0].strip()
        right = chunks[1].strip()

        leftnumber = re.match("^%s$" % RE_FLOATING, left)
        if leftnumber:
            left = float(left)
            iterator = discover_map(name, None, lambda b: left * b, standard_variable(right, 'day', **config))
        else:
            iterator = discover_map(name, None,
                                    lambda a, b: a * b, standard_variable(left, 'day', **config),
                                    standard_variable(right, 'day', **config))
        if mytimerate == 'day':
            return iterator
        elif mytimerate == 'month':
            return discover_day2month(iterator, lambda arr, dim: np.sum(arr, axis=dim))
        elif mytimerate == 'year':
            return discover_day2year(iterator, lambda arr, dim: np.sum(arr, axis=dim))

    if '.' in name:
        chunks = re_dotsplit.split(name)
        if len(chunks) > 1:
            if chunks[0][-1] == '-':
                var = standard_variable(chunks[0][:-1], mytimerate, **config)
                for chunk in chunks[1:]:
                    var = interpret_transform(var, chunk)

                return var

            var = standard_variable(chunks[0], 'day', **config)
            for chunk in chunks[1:]:
                var = interpret_transform(var, chunk)

            if mytimerate == 'day':
                return var
            elif mytimerate == 'month':
                return discover_day2month(var, lambda arr, dim: np.sum(arr, axis=dim))
            elif mytimerate == 'year':
                return discover_day2year(var, lambda arr, dim: np.sum(arr, axis=dim))

            return var

    version = None
    if '==' in name:
        chunks = name.split('==')
        name = chunks[0]
        version = chunks[1]

    if 'grid-weight' in config:
        timerate_translate = dict(day='daily', month='monthly', year='annual')
        path = files.sharedpath(os.path.join("climate/BCSD/hierid", config['grid-weight'], timerate_translate[mytimerate], name))
        if os.path.exists(path):
            return discover_versioned(path, name, version=version, **config)

        print(("WARNING: Cannot find new-style climate data %s, by %s, weighted by %s." % (name, mytimerate, config['grid-weight'])))

    if mytimerate == 'day':
        polyedvars = ['tas', 'tasmax']

        if name in polyedvars:
            return discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/" + name), name, version=version, **config)
        for ii in range(2, 10):
            if name in ["%s-poly-%d" % (var, ii) for var in polyedvars]:
                return discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/" + name), name, version=version, **config)
            if name in ["%s%d" % (var, ii) for var in polyedvars]:
                return discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/%s-poly-%s" % (name[:-1], name[-1])), '%s-poly-%s' % (name[:-1], name[-1]), version=version, **config)
        if name == 'prmm':
            if config.get('show-source', False):
                print((files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level/*/pr')))
            return discover_variable(files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level'), 'pr', **config)
        if name == 'tasmax_rcspline':
            found = configs.search(config, 'knots')
            assert found, "Cannot find references to any knots in config."
            assert len(found) == 1, "Multiple knots definitions in a config are not currently supported."
            for key in found:
                basedir = name + '_' + '_'.join(map(str, found[key]))
                return discover_rename(
                    discover_versioned_iterated(files.sharedpath("climate/BCSD/hierid/popwt/daily/" + basedir), 'tasmax_rcs_term_', len(found[key]) - 2, version=version, **config),
                    {'tasmax_rcs_term_' + str(ii+1): 'tasmax_rcspline' + str(ii+1) for ii in range(len(found[key]) - 2)})

    if mytimerate == 'month':
        if name in ['tas', 'tasmax', 'tasmin']:
            return discover_day2month(standard_variable(name, 'day', **config),  lambda arr, dim: np.mean(arr, axis=dim))
        if name == 'tasbin':
            if config.get('show-source', False):
                print((files.sharedpath('climate/BCSD/aggregation/cmip5_bins/IR_level/*/tas')))
            return discover_binned(files.sharedpath('climate/BCSD/aggregation/cmip5_bins/IR_level'), 'year', # Should this be year?
                                   'tas/tas_Bindays_aggregated_%scenario_r1i1p1_%model_%d.nc', 'SHAPENUM', 'DayNumber')
        if name == 'edd':
            if config.get('show-source', False):
                print((files.sharedpath('climate/BCSD/hierid/cropwt/monthly/edd_monthly')))
            return discover_rename(
                discover_versioned_binned(files.sharedpath('climate/BCSD/hierid/cropwt/monthly/edd_monthly'),
                                          'edd_monthly', 'refTemp', version=version, **config),
                {'edd_monthly': 'edd'})
        if name in ['pr', 'pr-poly-2']:
            return discover_versioned(files.sharedpath('climate/BCSD/hierid/cropwt/monthly/' + name),
                                      name, version=version, **config)
        if name in ['prmm', 'prmm-poly-2']:
            return discover_rename(
                discover_versioned(files.sharedpath('climate/BCSD/hierid/cropwt/monthly/' + name.replace('prmm', 'pr')),
                                   name.replace('prmm', 'pr'), version=version, **config), {name.replace('prmm', 'pr'): name})

    if mytimerate == 'year':
        polyedvars = ['tas-cdd-20', 'tas-hdd-20']
        polyedvars_daily = ['tas', 'tasmax'] # Currently do these as sums

        if name in polyedvars:
            if config.get('show-source', False):
                print((files.sharedpath("climate/BCSD/hierid/popwt/annual/" + name)))
            return discover_versioned_yearly(files.sharedpath("climate/BCSD/hierid/popwt/annual/" + name), name, version=version, **config)
        for ii in range(2, 10):
            if name in ["%s-poly-%d" % (var, ii) for var in polyedvars]:
                if config.get('show-source', False):
                    print((files.sharedpath("climate/BCSD/hierid/popwt/annual/" + name)))
                return discover_versioned_yearly(files.sharedpath("climate/BCSD/hierid/popwt/annual/" + name), name, version=version, **config)
            if name in ["%s%d" % (var, ii) for var in polyedvars]:
                if config.get('show-source', False):
                    print((files.sharedpath("climate/BCSD/hierid/popwt/annual/%s-poly-%s" % (name[:-1], name[-1]))))
                return discover_versioned_yearly(files.sharedpath("climate/BCSD/hierid/popwt/annual/%s-poly-%s" % (name[:-1], name[-1])), '%s-poly-%s' % (name[:-1], name[-1]), version=version, **config)

        if name in polyedvars_daily:
            return discover_day2year(standard_variable(name, 'day', **config), lambda arr, dim: np.sum(arr, axis=dim))

        for ii in range(2, 10):
            if name in ["%s-poly-%d" % (var, ii) for var in polyedvars_daily]:
                return discover_day2year(standard_variable(name, 'day', **config), lambda arr, dim: np.sum(arr, axis=dim))
            if name in ["%s%d" % (var, ii) for var in polyedvars_daily]:
                return discover_day2year(standard_variable(name, 'day', **config), lambda arr, dim: np.sum(arr, axis=dim))

            # If "mean" appended to front of daily variable name, do mean instead of sum...
            m = {"mean%s-poly-%d" % (v, ii): "%s-poly-%d" % (v, ii) for v in polyedvars_daily}
            if name in m:
                return discover_rename(
                    discover_day2year(standard_variable(m[name], 'day', **config), lambda arr, dim: np.mean(arr, axis=dim)),
                    {m[name]: name}
                    )
            m = {"mean%s%d" % (v, ii): "%s%d" % (v, ii) for v in polyedvars_daily}
            if name in m:
                return discover_rename(
                    discover_day2year(standard_variable(m[name], 'day', **config), lambda arr, dim: np.mean(arr, axis=dim)),
                    {m[name]: name}
                    )

        if name == 'meantas':
            return discover_rename(
                discover_day2year(standard_variable('tas', 'day', **config), lambda arr, dim: np.mean(arr, axis=dim)), {'tas': 'meantas'})
        if name == 'areatas-aggregated':
            if config.get('show-source', False):
                print((files.sharedpath("outputs/temps/*/*/areatas-aggregated.nc4")))
            return discover_covariate(files.sharedpath("outputs/temps"), "areatas-aggregated.nc4", "annual")
            
    raise ValueError("Unknown %s variable: %s" % (mytimerate, name))

def interpret_transform(var, transform):
    if transform == 'histclim':
        return discover_makehist(var)

    if transform[:7] == 'gddkdd(':
        lower, upper = tuple(map(float, transform[7:-1].split(',')))
        return discover_makegddkdd(var, lower, upper)

    if transform[:5] == 'step(':
        match = re.match(r"\s*(%s)\s*,\s*\[\s*(%s)\s*,\s*(%s)\s*\]\s*" % (RE_FLOATING, RE_FLOATING, RE_FLOATING),
                         transform[5:-1])
        assert match, "Step function misformed.  Use .step(#, [#, #])."
        stepval = float(match.group(1))
        befval = float(match.group(2))
        aftval = float(match.group(3))
        return discover_map(transform, None,
                            lambda xs: (aftval - befval) * (xs > stepval) + befval, var)

    if transform == 'country':
        def ds_conversion(ds):
            subcountries = np.array([region[:3] for region in ds.region.values])
            countries = np.unique(subcountries)
            def get_subcountryii(country):
                return np.nonzero(subcountries == country)[0]
            vars_only = list(ds.variables.keys())
            for name in ds.coords:
                if name in vars_only:
                    vars_only.remove(name)
            used_coords = ds.coords
            ds = fast_dataset.FastDataset({name: data_vars_space_conversion(countries, get_subcountryii, name, ds, 'vars', np.mean) for name in vars_only},
                                      coords={name: data_vars_space_conversion(countries, get_subcountryii, name, ds, 'coords', np.mean) for name in used_coords},
                                      attrs=ds.attrs)
            return ds

        return discover_convert(var, None, ds_conversion)

    assert False, "Cannot interpret transformation %s" % transform

def data_vars_space_conversion(newregions, get_oldii, name, ds, varset, accumfunc):
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
        dimnum = vardef[0].index('region')

        myshape = list(vardef[1].shape)
        myshape[dimnum] = len(newregions)
        result = np.zeros(tuple(myshape))
        for ii in range(len(newregions)):
            beforeindex = [slice(None)] * len(vardef[0])
            beforeindex[dimnum] = get_oldii(newregions[ii])
            afterindex = [slice(None)] * len(vardef[0])
            afterindex[dimnum] = ii
            result[tuple(afterindex)] = accumfunc(vardef[1][tuple(beforeindex)], dimnum)

        return (vardef[0], result)

    if name != 'region':
        return vardef

    return np.array(newregions)

def discover_models(basedir, **config):
    """
    basedir points to directory with both 'historical', 'rcp*'
    Aware configuration options:
     - pattern_matching
     - rcp or only-rcp
     - only-models
    """
    # Collect the entire complement of models
    models = os.listdir(os.path.join(basedir, 'historical'))

    for scenario in os.listdir(basedir):
        if scenario[0:3] != 'rcp':
            continue

        if config.get('only-rcp', config.get('rcp', scenario)) != scenario:
            continue

        if 'only-models' in config:
            modelset = config['only-models']
        else:
            modelset = copy.copy(models)
            if config.get('include_patterns', True):
                modelset += list(pattern_matching.rcp_models[scenario].keys())

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
                        print(("Missing pattern-base for %s %s" % (scenario, model)))
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
            pastreader = YearlyBinnedWeatherReader(pasttemplate, config.get('startyear', 1981), regionvar, ncvar)
            futurereader = YearlyBinnedWeatherReader(futuretemplate, 2006, regionvar, ncvar)
        elif timerate == 'month':
            pastreader = MonthlyBinnedWeatherReader(pasttemplate, config.get('startyear', 1981), regionvar, ncvar)
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

            pastreader = DailyWeatherReader(pasttemplate, config.get('startyear', 1981), 'SHAPENUM', variable)
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

            if os.path.exists(pasttemplate % (config.get('startyear', 1981))) and os.path.exists(futuretemplate % (2006)):
                pastreader = DailyWeatherReader(pasttemplate, config.get('startyear', 1981), 'SHAPENUM', variable)
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

def discover_versioned_models(basedir, version=None, **config):
    """Find the most recent version, if none specified."""
    if version is None:
        version = '%v'

    for scenario, model, pastdir, futuredir in discover_models(basedir, **config):
        pasttemplate = os.path.join(pastdir, "%d", version + '.nc4')
        futuretemplate = os.path.join(futuredir, "%d", version + '.nc4')

        yield scenario, model, pasttemplate, futuretemplate

def precheck_pastfuture(scenario, model, pasttemplate, futuretemplate, regionid, *variables):
    precheck_past = DailyWeatherReader.precheck(pasttemplate, 1981, regionid, *variables)
    if precheck_past:
        print("Skipping %s %s (past): %s" % (scenario, model, precheck_past))
        return False
    precheck_future = DailyWeatherReader.precheck(futuretemplate, 2006, regionid, *variables)
    if precheck_future:
        print("Skipping %s %s (future): %s" % (scenario, model, precheck_future))
        return False

    return True
        
def discover_versioned(basedir, variable, version=None, reorder=True, **config):
    if config.get('show-source', False):
        print(basedir)
    
    for scenario, model, pasttemplate, futuretemplate in discover_versioned_models(basedir, version, **config):
        if not precheck_pastfuture(scenario, model, pasttemplate, futuretemplate, 'hierid', variable):
            continue

        if reorder:
            pastreader = RegionReorderWeatherReader(DailyWeatherReader(pasttemplate, config.get('startyear', 1981), 'hierid', variable))
            futurereader = RegionReorderWeatherReader(DailyWeatherReader(futuretemplate, 2006, 'hierid', variable))
        else:
            pastreader = DailyWeatherReader(pasttemplate, config.get('startyear', 1981), 'hierid', variable)
            futurereader = DailyWeatherReader(futuretemplate, 2006, 'hierid', variable)

        yield scenario, model, pastreader, futurereader

def discover_versioned_iterated(basedir, prefix, count, version=None, reorder=True, **config):
    if config.get('show-source', False):
        print(basedir)

    variables = [prefix + str(ii + 1) for ii in range(count)]
        
    for scenario, model, pasttemplate, futuretemplate in discover_versioned_models(basedir, version, **config):
        if not precheck_pastfuture(scenario, model, pasttemplate, futuretemplate, 'hierid', *variables):
            continue

        if reorder:
            pastreader = RegionReorderWeatherReader(DailyWeatherReader(pasttemplate, config.get('startyear', 1981), 'hierid', *variables))
            futurereader = RegionReorderWeatherReader(DailyWeatherReader(futuretemplate, 2006, 'hierid', *variables))
        else:
            pastreader = DailyWeatherReader(pasttemplate, config.get('startyear', 1981), 'hierid', *variables)
            futurereader = DailyWeatherReader(futuretemplate, 2006, 'hierid', *variables)

        yield scenario, model, pastreader, futurereader

def discover_versioned_binned(basedir, variable, dim, version=None, reorder=True, **config):
    post_process = lambda x: RegionReorderWeatherReader(x) if reorder else lambda x: x

    for scenario, model, pasttemplate, futuretemplate in discover_versioned_models(basedir, version, **config):
        pastreader = MonthlyDimensionedWeatherReader(pasttemplate, config.get('startyear', 1981), 'hierid', variable, dim)
        futurereader = MonthlyDimensionedWeatherReader(futuretemplate, 2006, 'hierid', variable, dim)

        yield scenario, model, post_process(pastreader), post_process(futurereader)

def discover_versioned_yearly(basedir, variable, version=None, reorder=True, **config):
    for scenario, model, pasttemplate, futuretemplate in discover_versioned_models(basedir, version, **config):
        if reorder:
            pastreader = RegionReorderWeatherReader(YearlyDayLikeWeatherReader(pasttemplate, config.get('startyear', 1981), 'hierid', variable))
            futurereader = RegionReorderWeatherReader(YearlyDayLikeWeatherReader(futuretemplate, 2006, 'hierid', variable))
        else:
            pastreader = YearlyDayLikeWeatherReader(pasttemplate, config.get('startyear', 1981), 'hierid', variable)
            futurereader = YearlyDayLikeWeatherReader(futuretemplate, 2006, 'hierid', variable)

        yield scenario, model, pastreader, futurereader

def discover_covariate(basedir, filename, variable):
    for scenario in os.listdir(basedir):
        if scenario[0:3] != 'rcp':
            continue

        for model in os.listdir(os.path.join(basedir, scenario)):
            filepath = os.path.join(basedir, scenario, model, filename)
            if os.path.exists(filepath):
                reader = YearlyWeatherReader(filepath, 'annual', timevar='year', regionvar='regions')
                yield scenario, model, reader, reader
                                     
def discover_makehist(discover_iterator):
    """Mainly used with .histclim for, e.g., lincom (since normal historical is at the bundle level)."""
    for scenario, model, pastreader, futurereader in discover_iterator:
        yield scenario, model, RenameReader(pastreader, lambda x: x + '.histclim'), HistoricalCycleReader(pastreader, futurereader)

def discover_makegddkdd(discover_iterator, lower, upper):
    for scenario, model, pastreader, futurereader in discover_iterator:
        yield scenario, model, GDDKDDReader(pastreader, lower, upper), GDDKDDReader(futurereader, lower, upper)

def discover_rename(discover_iterator, name_dict):
    """name_dict can be a {new: old} dictionary, a string (if other discover produces only 1 var), or a function."""
    for scenario, model, pastreader, futurereader in discover_iterator:
        yield scenario, model, RenameReader(pastreader, name_dict), RenameReader(futurereader, name_dict)

def discover_day2month(discover_iterator, accumfunc):
    #time_conversion = lambda days: np.unique(np.floor((days % 1000) / 30.4167)) # Should just give 0 - 11
    time_conversion = lambda days: np.arange(12)
    def ds_conversion(ds):
        vars_only = list(ds.variables.keys())
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
        except Exception as ex:
            print("Exception but returning anyways:")
            print(ex)
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
        vars_only = list(ds.variables.keys())
        for name in ds.coords:
            if name in vars_only:
                vars_only.remove(name)
        used_coords = ds.coords
        if 'yyyyddd' in used_coords:
            del used_coords['yyyyddd']

        newvars = {}
        for name in vars_only:
            newvars[name] = data_vars_time_conversion_year(name, ds, 'vars', accumfunc)
            newvars['daily' + name] = data_vars_time_conversion_year(name, ds, 'vars', lambda arr, dim: np.mean(arr, axis=dim))
        ds = fast_dataset.FastDataset(newvars,
                                      coords={name: data_vars_time_conversion_year(name, ds, 'coords', accumfunc) for name in used_coords},
                                      attrs=ds.attrs)
        return ds

    return discover_convert(discover_iterator, time_conversion, ds_conversion)

def discover_map(name, unit, func, *iterators):
    pastfutures = {} # (scenario, model): (pastreader, futurereader)
    for iterator in iterators:
        for scenario, model, pastreader, futurereader in iterator:
            if (scenario, model) in pastfutures:
                pastfutures[(scenario, model)].append((pastreader, futurereader))
            else:
                pastfutures[(scenario, model)] = [(pastreader, futurereader)]

    for scenario, model in pastfutures:
        if len(pastfutures[(scenario, model)]) == len(iterators):
            yield scenario, model, MapReader(name, unit, func, *[pastfuture[0] for pastfuture in pastfutures[(scenario, model)]]), MapReader(name, unit, func, *[pastfuture[1] for pastfuture in pastfutures[(scenario, model)]])

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
        except Exception as ex:
            print("Exception but returning anyways:")
            print(ex)
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
