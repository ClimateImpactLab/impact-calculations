"""General system for retrieving known data.

This script currently only provides a `get_data` function, which has a
very general interface. `get_data` is called with the id (a string) of
a known data variable and the desired units for that
variable. Typically, the id is intended to be formatted as
"<group>-<item>". The structure of the resulting data is
unspecified. The units may only be used for unit checking, and an
error is produced if the units do not match.

If the id is not recognized, nothing is returned. If it is matched, a
tuple of the data and the version of the data is returned.

`get_data` also has a simple caching system, where data is returned
directly if it was previously loaded.  Units are not checked for
cached variables, since it is assumed that the same units were
used. This should be improved in the future (at which point units
could also be used for conversions).
"""

import csv
import numpy as np
from impactlab_tools.utils import files
from helpers import header

cached_data = {} # id => (data, version)

def get_data(id, units):
    """Returns a known data object, referenced by its id.

    Parameters
    ----------
    id : str
        The known name of the data object.
    units : str
        The known units for this data.

    Returns
    -------
    tuple(any, str)
        The data may have any structure. The second item in the tuple
    is the version of the data.
    """
    # Return if this is in the cache
    if id in cached_data:
        return cached_data[id]

    ### Known data items below

    # Average death rates from 2001 to 2010 by region
    if id == 'mortality-deathrates':
        assert units == 'deaths/person'

        #import mortality
        #return mortality.load_mortality_rates(), "CMF-1999-2010"

        # Load the data
        dependencies = []
        with open(files.sharedpath("social/baselines/mortality-physical/combined.csv"), 'r') as fp:
            reader = csv.reader(header.deparse(fp, dependencies))
            headrow = next(reader)

            yearcol = headrow.index('year')
            regcol = headrow.index('hierid')
            valcol = headrow.index('value')

            # Collect data over the baseline period
            yearvalues = {} # {region: [values]}
            for row in reader:
                year = int(row[yearcol])
                if year >= 2001 and year <= 2010:
                    if row[regcol] in yearvalues:
                        yearvalues[row[regcol]].append(float(row[valcol]))
                    else:
                        yearvalues[row[regcol]] = [float(row[valcol])]

            # Construct averages for each region
            allmeans = []
            for region in yearvalues:
                regmean = np.mean(yearvalues[region])
                allmeans.append(regmean)
                yearvalues[region] = regmean

            # Also report an average across the whole world, for missing resions
            yearvalues['mean'] = np.mean(allmeans)

            # Store this in the cache
            cached_data[id] = (yearvalues, dependencies[0])
            return cached_data[id]
