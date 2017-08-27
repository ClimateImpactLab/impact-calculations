from impacts import weather

def test_repeated():
    basedir = '/shares/gcp/BCSD/grid2reg/cmip'
    scenario, model, weatherbundle = weather.iterate_bundles(basedir).next()
    historybundle = weather.HistoricalWeatherBundle.make_historical(weatherbundle, None)
    for yyyyddd, values in historybundle.yearbundles():
        print yyyyddd[0], values[0, 0]

def test_shuffled():
    basedir = '/shares/gcp/BCSD/grid2reg/cmip'
    scenario, model, weatherbundle = weather.iterate_bundles(basedir).next()
    historybundle = weather.HistoricalWeatherBundle.make_historical(weatherbundle, 1)
    for yyyyddd, values in historybundle.yearbundles():
        print yyyyddd[0], values[0, 0]

if __name__ == '__main__':
    test_repeated()
    test_shuffled()
