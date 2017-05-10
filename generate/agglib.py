import csv
from helpers import header

def copy_timereg_variable(writer, variable, key, dstvalues, suffix, unitchange, timevar='year'):
    column = writer.createVariable(key, 'f8', (timevar, 'region'))
    column.units = unitchange(variable.units)
    if hasattr(variable, 'long_title'):
        column.long_title = variable.long_title
    if hasattr(variable, 'source'):
        column.source = variable.source + " " + suffix

    column[:, :] = dstvalues

def iter_timereg_variables(reader, timevar='year'):
    for key in reader.variables.keys():
        if (timevar, 'region') == reader.variables[key].dimensions:
            print key
            variable = reader.variables[key]

            yield key, variable

def get_aggregated_regions(regions):
    # Collect all levels of aggregation
    originals = {} # { prefix: [region] }
    for region in regions:
        original = region
        while len(region) > 3:
            region = region[:region.rindex('.')]
            if region in originals:
                originals[region].append(original)
            else:
                originals[region] = [original]

    # Add the FUND regions
    dependencies = []
    with open('/shares/gcp/regions/macro-regions.csv', 'r') as fp:
        aggreader = csv.reader(header.deparse(fp, dependencies))
        headrow = aggreader.next()
        for row in aggreader:
            fundregion = 'FUND-' + row[headrow.index('FUND')]
            if fundregion not in originals:
                originals[fundregion] = []

            iso3 = row[headrow.index('region-key')]
            if iso3 not in originals:
                continue

            originals[fundregion].extend(originals[iso3])

    # Collect all prefixes with > 1 region
    prefixes = [''] # '' = world
    for prefix in originals:
        if originals[prefix] > 1:
            prefixes.append(prefix)

    return originals, prefixes, dependencies
