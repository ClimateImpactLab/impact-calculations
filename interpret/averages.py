"""Translation from configuration options to covariate averaging.

Configurations can specify different kernels for economic and climate
covariate estimates: mean, median, exponential (or bucket), or
bartlett kernels. They can also specify the length of the kernel. See
the "Covariate Averging" section in docs/generate.md for more details.
"""

from impactcommon.math import averages

lookup = {'mean': averages.MeanAverager,
          'median': averages.MedianAverager,
          'bucket': averages.BucketAverager,
          'bartlett': averages.BartlettAverager}

def interpret(config, default, values):
    avgcls = config.get('class', default['class'])
    assert avgcls in lookup
    return lookup[avgcls](values, config.get('length', default['length']))
