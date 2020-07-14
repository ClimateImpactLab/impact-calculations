import numpy as np
from . import multithread, weather

# Allow any thread to request the bundle first
class SlaveParallelWeatherBundle(weather.WeatherBundle):
    def __init__(self, master, local):
        self.master = master
        self.local = local
        
    def yearbundles(self, maxyear=np.inf, variable_ofinterest=None):
        while True:
            outputs = self.master.request_action(self.local, 'yearbundles', maxyear=maxyear, variable_ofinterest=variable_ofinterest)
            if 'ds' not in outputs:
                self.master.end_timestep(self.local) # Acknowledge end
                break
            yield outputs['year'], outputs['ds']
            self.master.end_timestep(self.local)

    def __getattr__(self, name):
        return getattr(self.master.weatherbundle, name)
    
