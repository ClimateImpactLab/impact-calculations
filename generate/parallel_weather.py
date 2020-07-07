import multithread

# Allow any thread to request the bundle first
class SlaveParallelWeatherBundle(WeatherBundle):
    def __init__(self, master, local):
        self.master = master
        self.local = local
        
    def yearbundles(self, maxyear=np.inf, variable_ofinterest=None):
        while True:
            outputs = self.master.request_action(self.local, 'yearbundles', maxyear=maxyear, variable_ofinterest=variable_ofinterest)
            if 'ds' not in outputs:
                break
            yield outputs['year'], outputs['ds']
