import numpy as np

from xarray import Dataset, open_dataset, open_rasterio, merge

import os
from glob import glob
from fnmatch import fnmatch
from zipfile import ZipFile, BadZipFile
import tarfile
from tarfile import ReadError

import gdal

from warnings import warn


def _compressed(filename, substring=None):
    contents = []
    try:  # will work for various zip file formats
        f_ = ZipFile(filename)
        contents = f_.namelist()
        prefix = 'zip'
    except BadZipFile:
        pass

    try:  # will work for .tar, .tar.gz...
        f_ = tarfile.open(filename)
        contents = f_.getnames()
        prefix = 'tar'
    except ReadError:
        pass

    if substring is None:
        substring = '*'  # match everything

    files = []
    for item in contents:
        if item.startswith('._'):  # skip hidden files
            continue

        if fnmatch(item, substring) or substring in item:
            files.append('/vsi{}/'.format(prefix) +
                         os.path.join(filename, item))
    return files


def get_info(filename, substring=None, format='text', **kwargs):
    errors = []

    # check if file is a raster
    try:  # json format generates a TypeError if not a raster
        info = gdal.Info(filename, format=format, **kwargs)
        if info:
            return [info]
    except TypeError:
        pass

    # file is not a raster...
    errors.append(gdal.GetLastErrorMsg())
    # try compressed formats
    files = _compressed(filename, substring)
    if files:
        info = []
        for f in files:
            try:
                info_ = gdal.Info(f, format=format, **kwargs)
                if info_:
                    info.append(info_)
                elif not info_:
                    errors.append(gdal.GetLastErrorMsg())
            except TypeError:
                pass
        if info:
            return info

    # file is not compressed or no raster was found in file
    # try url...

    # not implemented yet

    raise OSError(f'Could not find raster file in {filename}...\n'
                   'Collected messages from gdal:\n'
                  f'{errors}')


def _normalize_longitude(lon):
    return lon - 360 if lon > 179 else lon


SOURCES = {
    'AsterGDEM': '*_{y_sep}{y:02d}{x_sep}{x:03d}*',
    'SRTM': '{y_sep}{y:02d}{x_sep}{x:03d}.*',
}


def _get_tiles(path, x1, x2, y1, y2, template='AsterGDEM', ext='.nc',
               lonlat=True, tilesize=1):
    """
    This is a helper function for making up a mosaic. It generates a
    list of tile filenames that are needed for the stitching process.

    In both AsterGDEM and SRTM files, the ``[N,S]??[E,W]???`` coordinate
    string points to the lower-left (SW) corner of the tile::

            +-----------------------+--------------------+----+
            |                       |                    |    |
        N89 <                       |                N89 +----+
            |                       |                   E179  |
            |                       |                         |
            |                       |                         |
            |                       |                         |
        N00 +------------------+----+-------------------------+
            |                  |    |                         |
        S01 <              S01 +----+                         |
            |                 W001  |                         |
            |                       |                         |
            |                       |                         |
            |                       |                         |
        S90 +------------------V----+--------------------V----+
           W180               W001 E000                 E179

    Parameters
    ----------
    path : str
        Base directory where tiles reside.

    x1, x2, y1, y2 : float
        The left-, right-, bottom-, and top-most coordinates of the
        bounding box.

    template : {'AsterGDEM', 'SRTM'} or str
        `'AsterGDEM'` and `'SRTM'` are both undertood and have a known
        filename template. Pass a user-defined template to format.
        The template string will be formatted with
        `.format(y_sep=y_sep, y=y, x_sep=x_sep, x=x)`.  Make sure to
        separate the extention from the user-defined template.

    ext : str
        By default, `'.nc'` files are used. Set to `'.zip'` or any other
        extention if needed. Make sure to separate the extention from
        the user-defined template.

    lonlat : bool
        By default x coordinates are treated as longitude and are
        normalized between [W180, E179]. set to `False` to forgo this
        normalization.

    tilesize : float
        It is assumed that tiles are 1x1 degrees. Set to update this
        assumption. If a single value is passed, tile size is assumed to
        be the same in the x and y directions. Otherwise pass a tuple
        with ``x``, ``y`` values.
    """
    if isinstance(tilesize, (tuple, list)):
        tsx, tsy = tilesize
    else:
        tsx = tsy = tilesize

    # To get the SW corner coordinates of a tile with negative
    # coordinates, subtract
    y1 -= tsy if y1 < 0 else 0
    x1 -= tsx if x1 < 0 else 0

    if x1 >= x2:
        raise ValueError('`x1` must be < `x2`')
    if y1 >= y2:
        raise ValueError('`y1` must be < `y2`')

    yrange = range(int(y1), int(y2) + tsy)
    xrange = range(int(x1), int(x2) + tsx)
    if lonlat:
        xrange = [_normalize_longitude(x) for x in xrange]

    template = SOURCES.get(template, template) + ext

    tile_filenames = []
    for y in yrange:
        if y < 0:
            y_sep = 'S'
            y *= -1
        else:
            y_sep = 'N'
        for x in xrange:
            if x < 0:
                x_sep = 'W'
                x *= -1
            else:
                x_sep = 'E'

            glob_expression = template.format(
                y_sep=y_sep, y=y, x_sep=x_sep, x=x
            )
            files = glob(os.path.join(path, glob_expression))
            if not files:
                warn(f'Unable to find file {glob_expression}...')
            else:
                tile_filenames.append(files[0])

    return tile_filenames


def _readrasterfile(filename, substring=None):
    # first try openning with xarray's open_dataset
    try:
        ds = open_dataset(filename)
        return ds

    # if that fails, try various VSI type files
    # this is done by first trying to get some information on the file
    except:
        infos = get_info(filename, substring, format='json')
        files = []
        for info in infos:
            for f in info['files']:
                files.append(f)

    if len(files) > 1:
        _files = '\n'.join(files)
        warn( 'Found more than one raster file in container:\n'
             f'{_files}\n'
              'Try provide a `substring` to refine your selection...')
    ds = Dataset()
    for j, f in enumerate(files):
        for i, band in enumerate(open_rasterio(f), 1):
            ds[f'band{j}_{i}'] = band
    ds.attrs = band.attrs
    return ds


def read(path, substring=None, extent=None, **kwargs):
    """
    Read a raster file to a :class:`~xarray.Dataset` object.

    Parameters
    ----------
    filename : str, list
        Path (relative or absolute) to a file or a directory or a
        compressed container (.zip, .tar, .tar.gz, etc.), local or
        remote, containing raster data.

        If ``path`` points a directory, ``extent`` should be
        defined in the form ``(x1, x2, y1, y2)``. This is used to read
        tiles, e.g., AsterGDEM, SRTM, etc. and stich them together into
        a single :class:`~xarray.Dataset`. See more keyword arguments
        that can be passed on to :func:`~._get_tiles`.

        Alternatively, an explicit list of paths to files can be
        provided for merging.

    substring : str, optional
        If path points to a compressed container, that may contain more
        than one file, this ``substring`` can be used to limit the files
        read. Patterns recognized by `fnmatch`_ are understood.

    extent : Tuple, None, Optional
        If extent is not ``None``, it is used to trim the data to the
        extend bound by the tuple ``(x1, x2, y1, y2)`` defining the
        left-, right-, bottom-, and top-most coordinates of the
        bounding box.

        Extend is needed if ``path`` is a directory.

    Notes
    -----
    If ``path`` is a directory, list of filenames that are needed for
    the stitching process is generated using the ``extent`` argument.

    In both AsterGDEM and SRTM files, the ``[N,S]??[E,W]???`` coordinate
    string points to the lower-left (SW) corner of the tile::

            +-----------------------+--------------------+----+
            |                       |                    |    |
        N89 <                       |                N89 +----+
            |                       |                   E179  |
            |                       |                         |
            |                       |                         |
            |                       |                         |
        N00 +------------------+----+-------------------------+
            |                  |    |                         |
        S01 <              S01 +----+                         |
            |                 W001  |                         |
            |                       |                         |
            |                       |                         |
            |                       |                         |
        S90 +------------------V----+--------------------V----+
           W180               W001 E000                 E179

    Other Parameters
    ----------------
    template : {'AsterGDEM', 'SRTM'} or str
        `'AsterGDEM'` and `'SRTM'` are both undertood and have a known
        filename template. Pass a user-defined template to format.
        The template string will be formatted with
        `.format(y_sep=y_sep, y=y, x_sep=x_sep, x=x)`.  Make sure to
        separate the extention from the user-defined template.

    ext : str
        By default, `'.nc'` files are used. Set to `'.zip'` or any other
        extention if needed. Make sure to separate the extention from
        the user-defined template.

    lonlat : bool
        By default x coordinates are treated as longitude and are
        normalized between [W180, E179]. set to `False` to forgo this
        normalization.

    tilesize : float
        It is assumed that tiles are 1x1 degrees. Set to update this
        assumption. If a single value is passed, tile size is assumed to
        be the same in the x and y directions. Otherwise pass a tuple
        with ``x``, ``y`` values.


    .. _fnmatch:
        https://docs.python.org/3.8/library/fnmatch.html#module-fnmatch
    """
    try:
        if os.path.isdir(path):
            try:
                x1, x2, y1, y2 = extent
            except TypeError:
                raise ValueError(
                    '`path` is a directory. Indicate `extent=(x1, x2, y1, y2)`'
                )
            path = _get_tiles(path, x1, x2, y1, y2, **kwargs)
    except TypeError:  # if error than it is probably a list
        pass
    if isinstance(path, (list, tuple)):
        files = '\n'.join(path)
        print(f'Reading {len(path)} tiles:\n{files}')
        tiles = []
        for f in path:
            tile = _readrasterfile(f, substring)
            tiles.append(tile)

        print('Merging tiles... be patient, this may take some time...')
        ds = merge(tiles)

    else:
        ds = _readrasterfile(path, substring=None)

    if extent is not None:
        ds = ds.geo.trim(*extent)

    return ds
