#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
rasterx: A python package for easy handling of raster datasets with xarray

**rasterx** is an open-source project dedicated to general tools for
interacting with raster datasets. It adds extra functionality, specific
for geo-raster files, on top of xarray's built in functionality

:author:
    Shahar Shani-Kadmiel (s.shanikadmiel@tudelft.nl)

:copyright:
    Shahar Shani-Kadmiel (s.shanikadmiel@tudelft.nl)

:license:
    This code is distributed under the terms of the
    GNU General Public License, Version 3
    (https://www.gnu.org/licenses/gpl-3.0.en.html)
"""

import os
import sys
from glob import glob
from setuptools import find_namespace_packages

try:
    from numpy.distutils.core import setup
except ImportError:
    msg = ('No module named numpy. Please install numpy first, it is '
           'needed before installing rasterx.')
    raise ImportError(msg)


SETUP_DIRECTORY = os.path.abspath('./')
name = 'rasterx'

DOCSTRING = __doc__.split('\n')

KEYWORDS = [
    'rasterx', 'geo', 'GIS',
    'AsterGDEM', 'SRTM', 'xarray'
]

INSTALL_REQUIRES = [
    'numpy>=1.16.2',
    'xarray>=0.14',
    'rasterio>=1.1.0',
    'gdal>=2.4.1',
    'netcdf4>=1.5.3'
]

ENTRY_POINTS = {
    'console_scripts': []
}

# get the package version from from the main __init__ file.
for line in open(os.path.join(SETUP_DIRECTORY, name, '__init__.py')):
    if '__version__' in line:
        package_version = line.strip().split('=')[-1]
        break


def setup_package():

    # setup package
    setup(
        name=name,
        version=package_version,
        description=DOCSTRING[1],
        long_description='\n'.join(DOCSTRING[3:]),
        author=[
            'Shahar Shani-Kadmiel'
        ],
        author_email='s.shanikadmiel@tudelft.nl',
        url='https://gitlab.com/shaharkadmiel/rasterx',
        download_url='https://gitlab.com/shaharkadmiel/rasterx.git',
        install_requires=INSTALL_REQUIRES,
        keywords=KEYWORDS,
        packages=find_namespace_packages(include=['rasterx.*']),
        entry_points=ENTRY_POINTS,
        zip_safe=False,
        classifiers=[
            'Development Status :: 4 - Beta',
            'Intended Audience :: Science/Research',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: ' +
                'GNU General Public License v3 (GPLv3)',
            'Programming Language :: Python',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: Scientific/Engineering',
            'Topic :: Scientific/Engineering :: GIS',
            'Operating System :: OS Independent'
        ],
    )


def clean():
    """
    Make sure to start with a fresh install
    """
    import shutil

    # delete complete build directory and egg-info
    path = os.path.join(SETUP_DIRECTORY, 'build')
    try:
        shutil.rmtree(path)
        print('removed ', path)
    except Exception:
        pass
    # delete complete build directory and egg-info
    path = os.path.join(SETUP_DIRECTORY, 'dist')
    try:
        shutil.rmtree(path)
        print('removed ', path)
    except Exception:
        pass
    # delete egg-info dir
    path = os.path.join(SETUP_DIRECTORY, name + '.egg-info')
    try:
        shutil.rmtree(path)
        print('removed ', path)
    except Exception:
        pass
    # delete __pycache__
    for path in glob(os.path.join(name, '**', '__pycache__'),
                     recursive=True):
        try:
            shutil.rmtree(path)
            print('removed ', path)
        except Exception:
            pass


if __name__ == '__main__':
    if 'clean' in sys.argv and '--all' in sys.argv:
        clean()
    else:
        clean()
        setup_package()
