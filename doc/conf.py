# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
import sphinx_bootstrap_theme

sys.path.insert(0, os.path.abspath('../'))

project = 'pyForTraCC'
copyright = '2024, Helvecio Neto, Alan Calheiros'
author = 'Helvecio Neto, Alan Calheiros'
release = '1.0.0'

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
    ]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

