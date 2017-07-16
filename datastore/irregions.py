import csv
from impactlab_tools.utils import files
import helpers.header as headre

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
