from impactcommon.math import averages

lookup = {'mean': averages.MeanAverager,
          'median': averages.MedianAverager,
          'bucket': averages.BucketAverager,
          'bartlett': averages.BartlettAverager}

def interpret(config, default, values):
    avgcls = config.get('class', default['class'])
    assert avgcls in lookup:
    return lookup[avgcls](values, config.get('length', default['length']))

