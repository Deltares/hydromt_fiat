"""hydroMT plugin for fiat models."""

from os.path import dirname, join, abspath


__version__ = "0.1.2"

DATADIR = join(dirname(abspath(__file__)), "data")

from .fiat import *
