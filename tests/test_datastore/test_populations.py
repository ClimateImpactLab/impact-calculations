import numpy as np
from datastore import weights

def test_comparison():
    irs = ["USA.14.608", "USA.5.184"]

    pop_halfweight = weights.interpret_halfweight("population")
    popjo2016_halfweight = weights.interpret_halfweight("population_jo2016")

    pop_stweight = pop_halfweight.load(2000, 2035, 'high', 'SSP3')
    popjo2016_stweight = popjo2016_halfweight.load(2000, 2035, 'high', 'SSP3')

    for ir in irs:
        pop_wws = pop_stweight.get_time(ir)
        popjo2016_wws = popjo2016_stweight.get_time(ir)

        np.testing.assert_equal(pop_wws == popjo2016_wws, False)
        np.testing.assert_allclose(pop_wws, popjo2016_wws, rtol=.2)

