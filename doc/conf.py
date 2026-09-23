# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
import sphinx_bootstrap_theme
import time

sys.path.insert(0, os.path.abspath('../'))

project = 'pyForTraCC'
current_year = time.strftime("%Y")
copyright = f'{current_year}, COPDT/CGIP/INPE (Brazil)'
author = 'Helvecio B. L. Neto, Alan J. P. Calheiros, Adriano P. Almeida, Arturo Sanchez, and Milton B. Silva'
# Read the version from the package
with open(os.path.join(os.path.dirname(__file__), '..', 'pyfortracc', '_version.py')) as f:
    release = f.read().split('=')[1].strip().strip('"').strip("'")

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
# For use myst-dialet, you need install myst-parser
# pip install myst-parser
# add to extensions: "myst_parser"

extensions = [
    "sphinx.ext.autodoc", 
    "sphinx.ext.todo", 
    "sphinx.ext.viewcode",
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.napoleon',
    ]

# Render the NumPy style docstrings of the package
napoleon_google_docstring = False
napoleon_numpy_docstring = True
# Section labels are prefixed with the document name (e.g. BI/BI_DATA:Title)
# to avoid duplicated labels between pages
autosectionlabel_prefix_document = True

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = []

