#!/usr/bin/env python3
"""Make OrderedDict available: collections (py2.7) or ordereddict (py2.6)."""

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
