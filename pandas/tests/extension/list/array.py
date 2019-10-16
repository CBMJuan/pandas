"""
Test extension array for storing nested data in a pandas container.

The ListArray stores an ndarray of lists.
"""
import numbers
import random
import string

import numpy as np

from pandas.core.dtypes.base import ExtensionDtype

import pandas as pd
from pandas.core.arrays import ExtensionArray


class ListDtype(ExtensionDtype):
    type = list
    name = "list"
    na_value = np.nan

    @classmethod
    def construct_array_type(cls):
        """
        Return the array type associated with this dtype.

        Returns
        -------
        type
        """
        return ListArray

    @classmethod
    def construct_from_string(cls, string):
        if string == cls.name:
            return cls()
        else:
            raise TypeError("Cannot construct a '{}' from '{}'".format(cls, string))


class ListArray(ExtensionArray):
    dtype = ListDtype()
    __array_priority__ = 1000

    def __init__(self, values, dtype=None, copy=False):
        if not isinstance(values, np.ndarray):
            raise TypeError("Need to pass a numpy array as values")
        for val in values:
            if not isinstance(val, self.dtype.type) and not pd.isna(val):
                raise TypeError("All values must be of type " + str(self.dtype.type))
        self.data = values

    @classmethod
    def _from_sequence(cls, scalars, dtype=None, copy=False):
        data = np.empty(len(scalars), dtype=object)
        data[:] = scalars
        return cls(data)

    def __getitem__(self, item):
        if isinstance(item, numbers.Integral):
            return self.data[item]
        else:
            # slice, list-like, mask
            return type(self)(self.data[item])

    def __len__(self) -> int:
        return len(self.data)

    def isna(self):
        return np.array(
            [not isinstance(x, list) and np.isnan(x) for x in self.data], dtype=bool
        )

    def take(self, indexer, allow_fill=False, fill_value=None):
        # re-implement here, since NumPy has trouble setting
        # sized objects like UserDicts into scalar slots of
        # an ndarary.
        indexer = np.asarray(indexer)
        msg = (
            "Index is out of bounds or cannot do a "
            "non-empty take from an empty array."
        )

        if allow_fill:
            if fill_value is None:
                fill_value = self.dtype.na_value
            # bounds check
            if (indexer < -1).any():
                raise ValueError
            try:
                output = [
                    self.data[loc] if loc != -1 else fill_value for loc in indexer
                ]
            except IndexError:
                raise IndexError(msg)
        else:
            try:
                output = [self.data[loc] for loc in indexer]
            except IndexError:
                raise IndexError(msg)

        return self._from_sequence(output)

    def copy(self):
        return type(self)(self.data[:])

    def astype(self, dtype, copy=True):
        if isinstance(dtype, type(self.dtype)) and dtype == self.dtype:
            if copy:
                return self.copy()
            return self
        elif pd.api.types.is_string_dtype(dtype) and not pd.api.types.is_object_dtype(
            dtype
        ):
            # numpy has problems with astype(str) for nested elements
            return np.array([str(x) for x in self.data], dtype=dtype)
        return np.array(self.data, dtype=dtype, copy=copy)

    @classmethod
    def _concat_same_type(cls, to_concat):
        data = np.concatenate([x.data for x in to_concat])
        return cls(data)


def make_data():
    # TODO: Use a regular dict. See _NDFrameIndexer._setitem_with_indexer
    data = np.empty(100, dtype=object)
    data[:] = [
        [random.choice(string.ascii_letters) for _ in range(random.randint(0, 10))]
        for _ in range(100)
    ]
    return data