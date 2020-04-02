"""Report all available calculation steps in the standard calculation library.

Available calculation steps are provided in a
`openest.generate.stdlib`, as subclasses of the Calculation
class. This tool prints the names of all of these out, and in the
future will provide additional information about them.

Called as:
```
python -m autodoc.available
```
"""

import inspect
from openest.generate import stdlib
from openest.generate.calculation import Calculation

for clsname in dir(stdlib):
    cls = getattr(stdlib, clsname)
    if inspect.isclass(cls) and issubclass(cls, Calculation):
        print(clsname)
