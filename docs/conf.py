"""
Configuration file for the Sphinx documentation builder.
"""

import os
import sys
sys.path.insert(0, os.path.abspath('..'))

# Project information
project = 'Blue Firmament'
copyright = '2025, BlueFirmament'
author = 'Lan_zhijiang'

# The full version, including alpha/beta/rc tags
import blue_firmament
release = blue_firmament.__version__

# Extensions
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
]

# Add any paths that contain templates here
templates_path = ['_templates']

# List of patterns to exclude
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# HTML output
# html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

# Language
# language = 'zh-CN'
# locale_dirs = ['locale/']
