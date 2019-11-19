from impacts import weather

def test_repeated():
    basedir = '/shares/gcp/BCSD/grid2reg/cmip'
    scenario, model, weatherbundle = weather.iterate_bundles(basedir).next()
    historybundle = weather.HistoricalWeatherBundle.make_historical(weatherbundle, None)
    for year, ds in historybundle.yearbundles():
        print year, ds

def test_shuffled():
    basedir = '/shares/gcp/BCSD/grid2reg/cmip'
    scenario, model, weatherbundle = weather.iterate_bundles(basedir).next()
    historybundle = weather.HistoricalWeatherBundle.make_historical(weatherbundle, 1)
    for year, ds in historybundle.yearbundles():
        print year, ds

if __name__ == '__main__':
    test_repeated()
    test_shuffled()
