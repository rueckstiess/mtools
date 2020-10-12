#!/usr/bin/env python3
"""Utility for grouping items and working with grouped items."""

import re

from mtools.util import OrderedDict


class Grouping(object):
    """Grouping object and related functions."""

    def __init__(self, iterable=None, group_by=None):
        """Init object."""
        self.groups = {}
        self.group_by = group_by

        if iterable:
            for item in iterable:
                self.add(item, group_by)

    def add(self, item, group_by=None):
        """General purpose class to group items by certain criteria."""
        key = None

        if not group_by:
            group_by = self.group_by

        if group_by:
            # if group_by is a function, use it with item as argument
            if hasattr(group_by, '__call__'):
                key = group_by(item)

            # if the item has attribute of group_by as string, use that as key
            elif isinstance(group_by, str) and hasattr(item, group_by):
                key = getattr(item, group_by)

            else:
                key = None
                # try to match str(item) with regular expression
                if isinstance(group_by, str):
                    match = re.search(group_by, str(item))
                    if match:
                        if len(match.groups()) > 0:
                            key = match.group(1)
                        else:
                            key = match.group()

        self.groups.setdefault(key, list()).append(item)


    def __getitem__(self, key):
        """Return item corresponding to key."""
        return self.groups[key]

    def __iter__(self):
        """Iterate items in group."""
        for key in self.groups:
            try:
                yield key
            except StopIteration:
                return

    def __len__(self):
        """Return length of group."""
        return len(self.groups)

    def keys(self):
        """Return keys in group."""
        return self.groups.keys()

    def values(self):
        """Return values in group."""
        return self.groups.values()

    def items(self):
        """Return items in group."""
        return self.groups.items()

    def regroup(self, group_by=None):
        """Regroup items."""
        if not group_by:
            group_by = self.group_by

        groups = self.groups
        self.groups = {}

        for g in groups:
            for item in groups[g]:
                self.add(item, group_by)

    def move_items(self, from_group, to_group):
        """Take all elements from the from_group and add it to the to_group."""
        if from_group not in self.keys() or len(self.groups[from_group]) == 0:
            return

        self.groups.setdefault(to_group, list()).extend(self.groups.get
                                                        (from_group, list()))
        if from_group in self.groups:
            del self.groups[from_group]

    def sort_by_size(self, group_limit=None, discard_others=False,
                     others_label='others'):
        """
        Sort the groups by the number of elements they contain, descending.

        Also has option to limit the number of groups. If this option is
        chosen, the remaining elements are placed into another group with the
        name specified with others_label. if discard_others is True, the others
        group is removed instead.
        """
        # sort groups by number of elements
        self.groups = OrderedDict(sorted(self.groups.items(),
                                         key=lambda x: len(x[1]),
                                         reverse=True))

        # if group-limit is provided, combine remaining groups
        if group_limit is not None:

            # now group together all groups that did not make the limit
            if not discard_others:
                group_keys = list(self.groups.keys())[group_limit - 1:]
                self.groups.setdefault(others_label, list())
            else:
                group_keys = list(self.groups.keys())[group_limit:]

            # only go to second last (-1), since the 'others' group is now last
            for g in group_keys:
                if not discard_others:
                    self.groups[others_label].extend(self.groups[g])
                del self.groups[g]

            # remove if empty
            if (others_label in self.groups and
                    len(self.groups[others_label]) == 0):
                del self.groups[others_label]

        # remove others group regardless of limit if requested
        if discard_others and others_label in self.groups:
            del self.groups[others_label]


if __name__ == '__main__':
    # Example
    items = [1, 4, 3, 5, 7, 8, 6, 7, 9, 8, 6, 4, 2, 3, 3, 0]

    grouping = Grouping(items, r'[3, 4, 5, 6, 7]')
    grouping.sort_by_size(group_limit=1, discard_others=True)
    # grouping.move_items('no match', 'foo')

    grouping.regroup(lambda x: 'even' if x % 2 == 0 else 'odd')

    for g in grouping:
        print('%s %s' % (g, grouping[g]))
