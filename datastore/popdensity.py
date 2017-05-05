import csv
from impactlab_tools.utils import files

def simple_densities(dependencies):
    densities = {} # {region: density}
    areas = {} # {region: area}
    with open(files.sharedpath('social/processed/LandScan2011/gcpregions.csv'), 'r') as fp:
        reader = csv.reader(header.deparse(fp, dependencies))
        headrow = reader.next()

        for row in reader:
            region = row[headrow.index('hierid')]

            area = float(row[headrow.index('area_km2')])
            areas[region] = area

            density = float(row[headrow.index('lspopzeros')]) / area
            densities[region] = density

    return densities, areas

def load_popop():
    popops = {} # {region: popop}

    with open(files.sharedpath('social/baselines/popop_baseline.csv'), 'r') as fp:
        reader = csv.reader(fp)
        headrow = reader.next()

        for row in reader:
            value = row[headrow.index('popop')]
            if value != 'NA' and 'E' not in value:
                popops[row[headrow.index('hierid')]] = float(value)

    return popops
