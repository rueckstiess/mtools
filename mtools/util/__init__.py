# make OrderedDict available from either collections (python 2.7) or ordereddict (python 2.6)
try:
	from collections import OrderedDict
except ImportError:
	from ordereddict import OrderedDict
