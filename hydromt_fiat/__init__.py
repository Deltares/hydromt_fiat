"""HydroMT plugin for FIAT models."""

from .fiat import FiatModel
from .version import __version__

__all__ = ["FiatModel", "__version__"]
