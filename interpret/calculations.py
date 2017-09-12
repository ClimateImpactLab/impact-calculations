import inspect
from openest.generate import stdlib
from openest.generate.calculation import Calculation

for clsname in dir(stdlib):
    cls = getattr(stdlib, clsname)
    if inspect.isclass(cls) and issubclass(cls, Calculation):
        print clsname
        
