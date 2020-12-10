"""Handling of impact regions and impact region hierarchy data.

"Impact regions" are the high-resolution regions at which CIL results
are projected. These were developed using an agglomeration algorithm,
which is in the socioeconomics repository:
https://bitbucket.org/ClimateImpactLab/socioeconomics/src/master/aggloms/

While much of the data used as inputs to the projection system is at
the impact region level, the functions in this file are for handling
the regions themselves, and the small amount of information stored
within the region definitions.

The hierarchy file, which describes the impact regions, is stored in
the regions/hierarchy.csv file in the shared directory.

"""

import csv
from impactlab_tools.utils import files
import helpers.header as headre


def contains_region(parents, candidate, hierid_df):
    """True if parents region is or contains candidate region

    Parameters
    ----------
    parents : Sequence of str
        Parent region(s).
    candidate : str
        Region to test if within `parents`.
    hierid_df : pandas.core.frame.DataFrame
        DataFrame of hierarchical region relationships. Must index
        'region-key', with column 'parent-key' populated with str.

    Returns
    -------
    bool
    """
    candidate = str(candidate)

    try:
        parent_key = hierid_df.loc[candidate, "parent-key"]
    except KeyError:  # No parent_key, so at trunk of tree or bad candidate.
        return False

    if parent_key in parents or candidate in parents:
        return True

    return contains_region(parents, parent_key, hierid_df)


def load_regions(hierarchy, dependencies):
    """Load the rows of hierarchy.csv associated with all known regions."""
    mapping = {} # color to hierid

    with open(files.sharedpath("regions/" + hierarchy), 'r') as fp:
        reader = csv.reader(headre.deparse(fp, dependencies))
        header = next(reader)
        for row in reader:
            if row[header.index('agglomid')]:
                mapping[int(row[header.index('agglomid')])] = row[0]

    regions = []
    for ii in range(len(mapping)):
        regions.append(mapping[ii + 1])

    return regions

def load_region_attr(filepath, indexcol, valcol, dependencies):
    """Load a column of attributes from an attribute file."""
    mapping = {} # hierid to attribute

    with open(files.sharedpath(filepath), 'r') as fp:
        reader = csv.reader(headre.deparse(fp, dependencies))
        header = next(reader)
        for row in reader:
            mapping[row[header.index(indexcol)]] = float(row[header.index(valcol)])

    return mapping

