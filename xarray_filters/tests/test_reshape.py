from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict

import numpy as np
import pytest
import xarray as xr

from xarray_filters import *
from xarray_filters.tests.test_data import *

def test_aggregations_can_chain():
    X = new_test_dataset(TEST_LAYERS)
    # The following should be the same: new_X and new_Xb
    #    the aggregations are just done in 2 or 1 calls to new_layer
    new_X = X.new_layer(name='tp1', # giving name != None
                                    # that means whatever ends up
                                    # as layers will need to do
                                    # to_ml_features or a custom
                                    # concatenator/reshaper
                                    # to make a single DataArray
                                    # out of the temperature, pressure
                                    # DataArrays
                        layers=['temperature', 'pressure'],
                        transforms=[['mean', dict(dim='z')], # From 4D to 3D
                                   ['std', dict(dim='t')]], # From 3D to 2D
                        flatten=True,
                        return_dict=False).compute()

    new_Xb = X.new_layer(name=None, # With name = None, temperature and
                                    # and pressure are modified
                                    # and returned in modified condition
                         layers=['temperature', 'pressure'],
                         transforms=['mean', dict(dim='z')], # aggregate over z
                         flatten=False  # Do not flatten to features
                         ).compute().new_layer(
                           name='tp2', #now make the new layer
                           layers=['temperature', 'pressure'], # 3D here
                           transforms=['std', dict(dim='t')], # 2D here
                           flatten=True, # call to_ml_features with defaults
                        ).compute()
    assert np.all(new_Xb.tp2 == new_X.tp1)


def test_transform_no_name():
    '''with no "name" keyword - all layers are returned'''
    X = new_test_dataset(TEST_LAYERS)
    example = X.new_layer(
        name=None,  # with name=None, all layers are passed through
        layers=None, # optionally a list of layers can be given
                     # to redact some of the existing layers
                     # from return value
        transforms=iqr_standard, # transforms, callable or list of callables
                                 # or list like this if passing args / kwargs
                                    # ['mean', ['arg1', 'arg2'], dict(dim='z')]
                                 # or list like this if no args/kwargs:
                                    # ['mean']
                                 # or a list like this if just kwargs:
                                    # ['mean', dict(dim='t')]  # or...
                                    # ['mean', [], dict(dim='t')]
                                # in each of those examples:
                                # 'mean' is the string name of a
                                # DataArray method
                                # Alternatively we can pass a function
                                # handle in place of where 'mean'
                                # was used in lists above, e.g.
                                # [custom_func, [1, 2, 3], dict(abc=99)]

                                # Or a list of the any of the list items above:
                                # to indicate transforms in series
        flatten=False,
    ).compute()
    assert isinstance(example, MLDataset)
    assert list(example.data_vars) == TEST_LAYERS
    for key, data_arr in example.data_vars.items():
        assert key in X.data_vars
        assert X[key].dims == data_arr.dims


def test_transforms_no_name():
    '''with no "name" keyword, all layers are passed through
    but transforms changes the dimensionality'''
    X = new_test_dataset(TEST_LAYERS)
    example = X.new_layer(
        name=None,
        layers=None,
        transforms=[['quantile', (0.5,), dict(dim=('t', 'z'))],
                    iqr_standard],
        flatten=False,
    ).compute()
    assert isinstance(example, MLDataset)
    assert list(example.data_vars) == TEST_LAYERS
    for key, data_arr in example.data_vars.items():
        assert key in X.data_vars
        assert data_arr.dims == ('x', 'y')


def test_named_aggregation_to_features():
    X = new_test_dataset(TEST_LAYERS)
    name = 'new_data_array'
    example = X.new_layer(
        name=name,
        layers=None,
        transforms=[iqr_standard, ['quantile', (0.5,), dict(dim=('t', 'z'))]],
        flatten=True,
    ).compute()
    assert isinstance(example, MLDataset)
    assert name not in X.data_vars
    assert tuple(example.data_vars) == (name,)
    assert example[name].dims == ('space', 'layer')
    assert list(example[name].layer.values) == TEST_LAYERS
    assert len(tuple(example[name].space.values[0])) == 2 # (x, y)


def test_to_and_from_feature_matrix():
    X = new_test_dataset(TEST_LAYERS).mean(dim=('z', 't'))
    X2 = X.to_ml_features()
    assert (FEATURES_LAYER,) == tuple(X2.data_vars)
    arr = X2[FEATURES_LAYER]
    assert arr.shape[1] == len(X.data_vars)
    assert arr.shape[0] == X.temperature.size
    X3 = X2.from_ml_features()
    for layer, data_arr in X3.data_vars.items():
        assert layer in X.data_vars
        assert np.allclose(X[layer].values, X3[layer].values)


def test_data_vars_keywords_varkw():
    X = new_test_dataset(TEST_LAYERS)
    layers_with_mag = tuple(TEST_LAYERS) + ('magnitude',)

    @data_vars_kwargs
    def example(**kw):
        for layer in TEST_LAYERS:
            assert layer in X.data_vars
            assert isinstance(X[layer], xr.DataArray)
        mag = (kw['wind_x'] ** 2 + kw['wind_y'] ** 2) ** 0.5
        arrs = tuple(kw.values(),) + (mag,)
        return OrderedDict(zip(layers_with_mag, arrs))
    X2 = X.new_layer(layers=layers_with_mag, transforms=example, compute=True)
    assert isinstance(X2, MLDataset)
    assert 'magnitude' in X2.data_vars
    assert all(layer in X2.data_vars for layer in TEST_LAYERS)


@pytest.mark.parametrize('layers', (None, ('wind_x', 'wind_y')))
def test_data_vars_keywords_positional(layers):
    X = new_test_dataset(TEST_LAYERS)
    layers_with_mag = tuple(TEST_LAYERS) + ('magnitude',)
    @data_vars_kwargs
    def example(wind_x, wind_y, temperature, pressure, **kw):
        mag = (wind_x ** 2 + wind_y ** 2) ** 0.5
        arrs = (wind_x, wind_y, temperature, pressure, mag)

        return OrderedDict(zip(layers_with_mag, arrs))

    X2 = X.new_layer(layers=layers_with_mag,
                     transforms=example,
                     compute=True)
    assert isinstance(X2, MLDataset)
    assert 'magnitude' in X2.data_vars
    if layers is not None:
        assert all(layer in X2.data_vars for layer in TEST_LAYERS)
    else:
        assert len(X2.data_vars)


