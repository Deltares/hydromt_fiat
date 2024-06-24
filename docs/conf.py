# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Python imports ----------------------------------------------------------
import os
import shutil
import sys
from distutils.dir_util import copy_tree

import hydromt
import hydromt_fiat

# -- Python functions --------------------------------------------------------
pwd = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(pwd, "..")))

def remove_dir_content(path: str) -> None:
    for root, dirs, files in os.walk(path):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))
    if os.path.isdir(path):
        shutil.rmtree(path)

# Copy necessary example notebooks
if os.path.isdir("_examples"):
    remove_dir_content("_examples")
os.makedirs("_examples")
copy_tree("../examples", "_examples")

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'hydromt_fiat'
copyright = '2024, Deltares'
author = 'Deltares'
version = hydromt_fiat.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx_design",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "sphinx.ext.githubpages",
    "sphinx.ext.intersphinx",
    "sphinx_autosummary_accessors",
    "IPython.sphinxext.ipython_directive",
    "IPython.sphinxext.ipython_console_highlighting",
    "nbsphinx",
]

autosummary_generate = True
source_suffix = ".rst"
templates_path = ['_templates']

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
language = "en"
master_doc = "index"
pygments_style = "sphinx"
todo_include_todos = False

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

autodoc_member_order = "bysource"
autoclass_content = "both"

bare_version = hydromt_fiat.__version__
doc_version = bare_version[: bare_version.find("dev") - 1]

html_context = {
    "github_url": "https://github.com",
    "github_user": "Deltares",
    "github_repo": "hydromt_fiat",
    "github_version": "main",  # FIXME
    "doc_path": "docs",
    "default_mode": "light",
}

html_css_files = ["theme-deltares.css"]
html_favicon = "_static/hydromt-icon.svg"
html_logo = "_static/hydromt-icon.svg"
html_static_path = ['_static']
html_theme = "pydata_sphinx_theme"

html_theme_options = {
    "show_nav_level": 2,
    "navbar_align": "content",
    "use_edit_page_button": True,
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/Deltares/hydromt_fiat",  # required
            "icon": "https://upload.wikimedia.org/wikipedia/commons/9/91/Octicons-mark-github.svg",
            "type": "url",
        },
        {
            "name": "Delft-FIAT",
            "url": "https://deltares.github.io/Delft-FIAT/latest/",
            "icon": "_static/fiat.svg",
            "type": "local",
        },
    ],
    "external_links": [
        {
            "name": "HydroMT core",
            "url": "https://deltares.github.io/hydromt/latest/index.html",
        },
    ],
    "logo": {
        "text": "HydroMT FIAT",
    },
    "navbar_end": ["navbar-icon-links", "version-switcher"],  # remove dark mode switch
    "switcher": {
        "json_url": "https://raw.githubusercontent.com/Deltares/hydromt_fiat/gh-pages/switcher.json",
        "version_match": doc_version,
    },
}

remove_from_toctrees = ["_generated/*"]

# -- Options for manual page output ---------------------------------------

man_pages = [
    (master_doc, "hydromt_fiat", "HydroMT FIAT plugin Documentation", [author], 1)
]


# -- INTERSPHINX -----------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable", None),
    # "numpy": ("https://numpy.org/doc/stable", None),
    "scipy": ("https://docs.scipy.org/doc/scipy", None),
    # "numba": ("https://numba.pydata.org/numba-doc/latest", None),
    # "matplotlib": ("https://matplotlib.org/stable/", None),
    # "dask": ("https://docs.dask.org/en/latest", None),
    "rasterio": ("https://rasterio.readthedocs.io/en/latest", None),
    "geopandas": ("https://geopandas.org/en/stable", None),
    "xarray": ("https://xarray.pydata.org/en/stable", None),
    "hydromt": ("https://deltares.github.io/hydromt/latest/", None),
}
