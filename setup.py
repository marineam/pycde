#!/usr/bin/python

from distutils.core import setup, Extension

_gain = Extension('pycde.replaygain._gain',
                  libraries = ['sndfile'],
                  extra_compile_args = ["-std=gnu99"],
                  sources = ['pycde/replaygain/gain_module.c',
                             'pycde/replaygain/gain_analysis.c'])

setup(name = 'pycde',
      version = '0.1',
      description = 'A Ripper',
      ext_modules = [_gain])
