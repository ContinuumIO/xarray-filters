from __future__ import absolute_import, division, print_function, unicode_literals


from collections import OrderedDict
from pprint import pformat

import numpy as np
import xarray as xr

from xarray_filters import *

@return_dataset
@for_each_array
def iqr_standard(arr, **kw):
    '''Uses data_vars_kwargs to turn a DataArray function
    into one that operates on each array in a Dataset like
    structure'''
    median = arr.quantile(0.5)
    upper = arr.quantile(0.75)
    lower = arr.quantile(0.25)
    return (arr - median) / (upper - lower)

## The following are "spec" arguments to build_run_spec for testing

Spec_0 = [('tp1',   # Name of new DataArray is tp1
  [['layers', ['temperature', 'pressure']], # layers needed for calculation
   ['agg', 'mean', [], {'dim': 'z'}], # aggregate over z dimension
   ['agg', 'std', [], {'dim': 't'}], # aggregate over t dimension
   ['flatten', 'space', ['y', 'x']]])] # call to_ml_features, transposing to (y, x) before ravel on each DataArray.values
Spec_1 = [(('temperature', 'pressure'),
  [['layers', ['temperature', 'pressure']], ['agg', 'mean', [], {'dim': 'z'}]])]
Spec_2 = [('tp2',
  [['layers', ['temperature', 'pressure']],
   ['agg', 'std', [], {'dim': 't'}],
   ['flatten', 'space', ['y', 'x']]])]
Spec_3 = [(('temperature', 'wind_x', 'wind_y', 'pressure'),
  [['layers', ['temperature', 'wind_x', 'wind_y', 'pressure']],
   ['transform',
    iqr_standard,
    [],
    {}]])]
Spec_4 = [(('temperature', 'wind_x', 'wind_y', 'pressure'),
  [['layers', ['temperature', 'wind_x', 'wind_y', 'pressure']],
   ['transform',
    iqr_standard,
    [],
    {}],
   ['agg', 'quantile', (0.5,), {'dim': ('t', 'z')}]])]
Spec_5 = [('features',
  [['layers', ['temperature', 'wind_x', 'wind_y', 'pressure']],
   ['transform',
    iqr_standard,
    [],
    {}],
   ['agg', 'quantile', (0.5,), {'dim': ('t', 'z')}],
   ['flatten', 'space', ['y', 'x']]])]
Spec_6 = [('features',
  [['layers', ['temperature', 'wind_x', 'wind_y', 'pressure']],
   ['flatten', 'space', ('x', 'y')]])]

shp = 20, 15, 8, 48
dims = 'x', 'y', 'z', 't'
# We are changing "band" to "layer" in Elm / Earthio (band Phase I - satellite mindset)
TEST_LAYERS = ['temperature', 'wind_x', 'wind_y', 'pressure']
r = lambda: np.random.uniform(0, 1, shp)
c = lambda: OrderedDict([(dim, np.arange(s)) for dim, s in zip(dims, shp)])
a = lambda: xr.DataArray(r(), coords=c(), dims=dims)
new_test_dataset = lambda layers: MLDataset(OrderedDict([(layer, a()) for layer in layers]))


extras = ['new_test_dataset', 'TEST_LAYERS', 'iqr_standard']
__all__ = [name for name in tuple(globals().keys())
           if name.startswith('Spec')] + extras