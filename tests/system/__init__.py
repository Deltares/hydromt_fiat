import pytest
from packaging.version import Version

try:
    import fiat  # noqa: F401

    HAS_FIAT = True

except ImportError:
    HAS_FIAT = False

if HAS_FIAT:
    from fiat import GeomModel, GridModel, __version__
    from fiat.settings import load_settings
else:
    __version__ = "NOT INSTALLED"
    GeomModel = None
    GridModel = None
    load_settings = None


SKIP_IF_FIAT_INCOMPATIBLE = pytest.mark.skipif(
    not HAS_FIAT or Version(__version__) < Version("1.0.0.dev0"),
    reason=f"At least Delft-FIAT version 1.0.0 is required (got {__version__}).",
)
