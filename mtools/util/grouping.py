from mtools.util import OrderedDict
import re

class Grouping(object):

    def __init__(self, iterable=None, group_by=None):
        self.groups = {}
        self.group_by = group_by

        if iterable:
            for item in iterable:
                self.add(item, group_by)


    def add(self, item, group_by=None):
        """ General purpose class to group items by certain criteria. """

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
                    else:
                        key = 'no match'
        else:
            # group_by is None, throw it all in one big bucket
            key = 'others'
            
        self.groups.setdefault(key, list()).append(item)
        

    def __getitem__(self, key):
        return self.groups[key]


    def __iter__(self):
        for key in self.groups:
            yield key


    def regroup(self, group_by):
        if not group_by:
            group_by = self.group_by

        groups = self.groups
        self.groups = {}

        for g in groups:
            for item in groups[g]:
                self.add(item, group_by)



    def sort_by_size(self, group_limit=None, discard_others=False, others_label='others'):

        # sort groups by number of elements
        self.groups = OrderedDict( sorted(self.groups.iteritems(), key=lambda x: len(x[1]), reverse=True) )

        # if group-limit is provided, combine remaining groups
        if group_limit != None:

            # now group together all groups that did not make the limit
            if not discard_others:
                self.groups.setdefault(others_label, list())

            # only go to second last (-1), since the 'others' group is now last
            for g in self.groups.keys()[ group_limit:-1 ]:
                if not discard_others:
                    self.groups[others_label].extend(self.groups[g])
                del self.groups[g]

            # remove if empty
            if others_label in self.groups and len(self.groups[others_label]) == 0:
                del self.groups[others_label]



if __name__ == '__main__':
    items = [1, 4, 3, 5, 7, 8, 6, 7, 9, 8, 6, 4, 2, 3, 3, 0]

    grouping = Grouping(items, r'[3, 4, 5, 6, 7]')
    grouping.sort_by_size(group_limit=2, discard_others=False, others_label='foo')
    
    # grouping.regroup(lambda x: 'even' if x % 2 == 0 else 'odd')

    for g in grouping:
        print g, grouping[g]

