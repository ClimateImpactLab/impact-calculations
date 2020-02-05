import csv
from pandas import read_csv
from impactlab_tools.utils import files
import helpers.header as headre

def contains_region(parents, candidate, hierid_df):
    """Test if parent region contains candidate region

    Parameters
    ----------
    parents : str or Sequence of str
        Parent region(s).
    candidate : str
        Region to test if within `parents`.
    hierid_df : pandas.core.frame.DataFrame
        DataFrame of hierarchical region relationships. Must have columns 
        'region-key', 'parent-key', populated with str.

    Returns
    -------
    bool
    """
    # This may be candidate for lru_cache once python version upgraded.
    if isinstance(parents, str):
        parents = [parents]
    candidate = str(candidate)

    try:
        parent_key = (hierid_df
                      .loc[hierid_df.loc[:, "region-key"] == candidate, "parent-key"]
                      .values.item())
    except ValueError:  # No parent_key, so at trunk of tree.
        return False

    if parent_key in parents:
        return True

    return contains_region(parents, parent_key, hierid_df)

def read_hierid(csvpath):
    """Read hierarchy.csv hierid file from path, return pandas.DataFrame
    """
    return read_csv(csvpath, skiprows=31)

def load_regions(hierarchy, dependencies):
    """Load the rows of hierarchy.csv associated with all known regions."""
    mapping = {} # color to hierid

    with open(files.sharedpath("regions/" + hierarchy), 'r') as fp:
        reader = csv.reader(headre.deparse(fp, dependencies))
        header = reader.next()
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
        header = reader.next()
        for row in reader:
            mapping[row[header.index(indexcol)]] = float(row[header.index(valcol)])

    return mapping

