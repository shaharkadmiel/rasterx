from xarray import Dataset, register_dataset_accessor
import numpy as np
from warnings import warn


@register_dataset_accessor('geo')
class GeoAccessor:
    def __init__(self, xarray_obj):
        self._obj = xarray_obj
        # figure out the spatial coords
        try:
            self._set_spatial_coord(*self._get_spatial_coords())
        except TypeError:
            pass

        self.dx = self.x.data[1] - self.x.data[0]
        self.dy = self.y.data[1] - self.y.data[0]

    @property
    def extent(self):
        return (
            self.x.data[0] - 0.5 * self.dx,
            self.x.data[-1] + 0.5 * self.dx,
            self.y.data[0] - 0.5 * self.dy,
            self.y.data[-1] + 0.5 * self.dy
        )

    def _get_spatial_coords(self):
        for var in self._obj.values():
            if 'x' in var.dims and 'y' in var.dims:
                return var.dims

            if 'lon' in var.dims and 'lat' in var.dims:
                return var.dims

            warn('Not sure which coordinates are spatial. Try setting them...')
            return None, None

    def _set_spatial_coord(self, y, x):
        self._x = x
        self._y = y

    @property
    def x(self):
        return self._obj[self._x]

    @property
    def y(self):
        return self._obj[self._y]

    def set_x(self, x):
        self._obj[self._x] = x

    def set_y(self, y):
        self._obj[self._y] = y

    def set_xy(self, x, y):
        """
        Attach a 2D dimensions to the x (horizontal) and y (vertical)
        dimensions to be used as the spatial dimensions of the dataset.
        """
        self.set_x(x)
        self.set_y(y)

    def trim(self, x1, x2, y1, y2, pad=False, fill_value=None):
        """
        Trim the extent of the data and pad as needed.

        Parameters
        ----------
        x1, x2, y1, y2 : float
            The left-, right-, bottom-, and top-most coordinates of the
            bounding box.

        pad : bool, optional
            Gives the possibility to trim at coordinates outside the
            original extent, filling with the ``_FillValue`` or with a
            given ``fill_value``.

        fill_value : float or None, optional
            Value to pad the data with in case extent is expanded beyond
            the data. If ``None``, the ``_FillValue`` is used.

        """
        if x1 >= x2:
            raise ValueError('`x1` must be < `x2`')
        if y1 >= y2:
            raise ValueError('`y1` must be < `y2`')

        # Stage 1: Trim
        trimmed = self._obj.sel(
            {self._x: slice(x1, x2),
             self._y: slice(y1, y2)}
        )

        if pad is False:  # no padding...
            return trimmed

        # Stage 2: Pad (if needed):
        X1, X2, Y1, Y2 = (trimmed.geo.x.data[0],
                          trimmed.geo.x.data[-1],
                          trimmed.geo.y.data[0],
                          trimmed.geo.y.data[-1])

#         if X1 <= w < e <= X2 and Y1 <= s < n <= Y2:  # no need to pad
#             return trimmed

        # set the new coordinate space
        x = np.hstack(
            (np.arange(X1 - self.dx, x1, -self.dx)[::-1],
             trimmed.geo.x,
             np.arange(X2 + self.dx, x2, self.dx))
        )
        y = np.hstack(
            (np.arange(Y1 - self.dy, y1, -self.dy)[::-1],
             trimmed.geo.y,
             np.arange(Y2 + self.dy, y2, self.dy))
        )

        # make a dummy dataset with the new spatial extent
        padded = Dataset(
            data_vars={
                self._x: (
                    self._x,
                    x,
                    trimmed.geo.x.attrs,
                    trimmed.geo.x.encoding
                ),
                self._y: (
                    self._y,
                    y,
                    trimmed.geo.y.attrs,
                    trimmed.geo.y.encoding
                ),
            }
        )

        # update with the trimmed data
        padded.update(trimmed)
        return padded
