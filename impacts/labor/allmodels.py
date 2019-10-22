"""
Setup labor sector-specific calcs, generators, and iterators for projection.
"""

import glob
import os

import numpy as np
from impactlab_tools.utils import files

from adaptation import csvvfile
from climate.discover import discover_versioned
from generate import weather, effectset, caller, checks


def preload():
    """Preloading step run prior to iterating to create various products.

    Labor sector preloading does nothing.
    """
    pass


def get_bundle_iterator(config):
    """Get a generator for needed weather variables

    Parameters
    ----------
    config : dict
        Unused.

    Returns
    -------
    generate.weather.iterate_bundles
        Generator(s) for the various weather variables needed for the
        projection.
    """
    reorder = True  # ('filter_region' in config)
    return weather.iterate_bundles(
        discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/tasmax"), 'tasmax', reorder=reorder),
        discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/tasmax-poly-2"), 'tasmax-poly-2',
                           reorder=reorder),
        discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/tasmax-poly-3"), 'tasmax-poly-3',
                           reorder=reorder),
        discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/tasmax-poly-4"), 'tasmax-poly-4',
                           reorder=reorder))


def check_doit(targetdir, basename, suffix, deletebad=False):
    """Checks whether file exists

    Check for a file with path
    `os.path.join(targetdir, basename + suffix + '.nc4')`, with the option of
    deleting it if it does not pass validation.

    Parameters
    ----------
    targetdir : str
        Path to a target directory.
    basename : str
        A "base" of a file name.
    suffix : str
        Any additional component directly appended to the end of `basename`.
    deletebad : bool, optional
        Whether to delete the target file, if it does not pass
        generate.checks.check_result_100years.

    Returns
    -------
    bool
    """
    filepath = os.path.join(targetdir, basename + suffix + '.nc4')
    if not os.path.exists(filepath):
        print("REDO: Cannot find", filepath)
        return True

    # Check if has 100 valid years
    if not checks.check_result_100years(filepath):
        print("REDO: Incomplete", basename, suffix)
        if deletebad:
            os.remove(filepath)
        return True

    return False


def produce(targetdir, weatherbundle, economicmodel, pvals, config, push_callback=None, suffix='', profile=False,
            diagnosefile=False):
    """Function used to passing climate impact projection to effectset.generate

    Nothing is directly returned by this function. Instead it has a side-effect
    by calling generate.effectset.generate.

    Parameters
    ----------
    targetdir : str
        Path to directory projections files are output to.
    weatherbundle : generate.weather.WeatherBundle-like
        To access climate variables.
    economicmodel : adaptation.econmodel.SSPEconomicModel
        Economic model to apply to projection.
    pvals : generate.pvalses.ConstantPvals, generate.pvalses.ConstantDictionary,
    generate.pvalses.OnDemandRandomDictionary, or generate.pvalses.OnDemand.RandomPvals
        p-values to use for this projection.
    config : dict
        Dictionary of configuration parameters for this projection.
    push_callback : callable or None, optional
        Passed to generate.effectset.generate. If None, passes function that
        returns None.
    suffix : str, optional
        Optional string appended to filename of output files.
    profile : bool, optional
        Does nothing.
    diagnosefile : str or bool, optional
        Path to CSV diagnostic file or False. Passed to
        generate.effectset.generate.
    """
    if config['do_only'] is None or config['do_only'] == 'interpolation':
        if push_callback is None:
            def push_callback(reg, yr, app, predget, mod):
                return None

        csvvfiles = glob.glob(files.sharedpath(config['csvvfile']))

        for filepath in csvvfiles:
            basename = os.path.basename(filepath)[:-5]

            # Split into risk groups and lock in q-draw
            csvv = csvvfile.read(filepath)
            csvvfile.collapse_bang(csvv, pvals[basename].get_seed('csvv'))
            # numpreds = len(config['terms'])
            numpreds = 5  # THIS IS A MAGIC NUMBER!

            # Loop over different risk groups.
            for idx, riskgroup in enumerate(['low', 'high']):
                # Because first terms in csvv are low risk, second are high.
                subcsvv = csvvfile.subset(csvv, idx * numpreds + np.arange(numpreds))
                fullbasename = basename + ('-risk%s' % riskgroup)

                # Full Adaptation
                if check_doit(targetdir, fullbasename, suffix):
                    print('Full Adaptation')
                    calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(
                        subcsvv,
                        'impacts.labor.ols_polynomial',
                        weatherbundle,
                        economicmodel,
                        pvals[basename],
                        config=config,
                    )
                    effectset.generate(
                        targetdir,
                        fullbasename + suffix,
                        weatherbundle,
                        calculation,
                        'Extensive margin labor impacts, with interpolation and adaptation through interpolation.',
                        dependencies + weatherbundle.dependencies + economicmodel.dependencies, config,
                        push_callback=lambda reg, yr, app: push_callback(reg, yr, app,
                                                                         baseline_get_predictors,
                                                                         fullbasename),
                        diagnosefile=diagnosefile.replace('.csv',
                                                          '-' + fullbasename + '.csv') if diagnosefile else False,
                    )

                if config['do_farmers'] and not weatherbundle.is_historical():
                    # Lock in the values
                    pvals[basename].lock()

                    # No Adaptation
                    if check_doit(targetdir, fullbasename + "-noadapt", suffix):
                        print('No Adaptation')
                        calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(
                            subcsvv,
                            'impacts.labor.ols_polynomial',
                            weatherbundle,
                            economicmodel,
                            pvals[basename],
                            farmer='coma',
                            config=config,
                        )
                        effectset.generate(targetdir,
                                           fullbasename + "-noadapt" + suffix, weatherbundle,
                                           calculation,
                                           "Extensive margin labor impacts, with no adaptation.",
                                           dependencies + weatherbundle.dependencies + economicmodel.dependencies,
                                           config,
                                           push_callback=lambda reg, yr, app: push_callback(reg, yr, app,
                                                                                            baseline_get_predictors,
                                                                                            fullbasename))

                    # Income-only Adaptation
                    if check_doit(targetdir, fullbasename + "-incadapt", suffix):
                        print('Income-only adaptation')
                        calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(
                            subcsvv,
                            'impacts.labor.ols_polynomial',
                            weatherbundle,
                            economicmodel,
                            pvals[basename],
                            farmer='dumb',
                            config=config,
                        )
                        effectset.generate(
                            targetdir,
                            fullbasename + "-incadapt" + suffix,
                            weatherbundle,
                            calculation,
                            "Extensive margin labor impacts, with interpolation and only environmental adaptation.",
                            dependencies + weatherbundle.dependencies + economicmodel.dependencies,
                            config,
                            push_callback=lambda reg, yr, app: push_callback(reg, yr, app,
                                                                             baseline_get_predictors,
                                                                             fullbasename),
                        )
