#!/usr/bin/env python3
"""Pickle overlay files for mplotqueries."""

import glob
import os
import pickle
import uuid


class OverlayMixin(object):
    """Load, save, list, and remove pickled plot overlays."""

    def list_overlays(self):
        target_path = os.path.join(self.home_path, self.mtools_path,
                                   self.overlay_path)
        if not os.path.exists(target_path):
            return

        # load groups and merge
        target_files = glob.glob(os.path.join(target_path, '*'))
        print("Existing overlays:")
        for f in target_files:
            print("   %s" % os.path.basename(f))

    def save_overlay(self):
        # make directory if not present
        target_path = os.path.join(self.home_path, self.mtools_path,
                                   self.overlay_path)
        if not os.path.exists(target_path):
            try:
                os.makedirs(target_path)
            except OSError:
                SystemExit("Couldn't create directory %s, quitting. "
                           "Check permissions, or run without --overlay to "
                           "display directly." % self.overlay_path)

        # create unique filename
        while True:
            uid = str(uuid.uuid4())[:8]
            target_file = os.path.join(target_path, uid)
            if not os.path.exists(target_file):
                break

        # dump plots and handle exceptions
        try:
            # Pickle protocol version 4 was added in Python 3.4. It adds
            # support for very large objects, pickling more kinds of objects,
            # and some data format optimizations.
            pickle.dump(self.plot_instances, open(target_file, 'wb'),
                        protocol=4)
            print("Created overlay: %s" % uid)
        except Exception as e:
            print("Error: %s" % e)
            SystemExit("Couldn't write to %s, quitting. Check permissions, "
                       "or run without --overlay to display directly."
                       % target_file)

    def load_overlays(self):
        target_path = os.path.join(self.home_path, self.mtools_path,
                                   self.overlay_path)
        if not os.path.exists(target_path):
            return False

        # load groups and merge
        target_files = glob.glob(os.path.join(target_path, '*'))
        for f in target_files:
            try:
                overlay = pickle.load(open(f, 'rb'))
            except Exception:
                print("Couldn't read overlay %s, skipping." % f)
                continue

            # extend each list according to its key
            self.plot_instances.extend(overlay)
            # for key in group_dict:
            #     self.groups.setdefault(key, list()).extend(group_dict[key])

            print("Loaded overlay: %s" % os.path.basename(f))

        if len(target_files) > 0:
            print('')

        return len(target_files) > 0

    def remove_overlays(self):
        target_path = os.path.join(self.home_path, self.mtools_path,
                                   self.overlay_path)
        if not os.path.exists(target_path):
            return 0

        target_files = glob.glob(os.path.join(target_path, '*'))
        # remove all group files
        for f in target_files:
            try:
                os.remove(f)
            except OSError:
                print("Error occured when deleting %s, skipping." % f)
                continue

        if len(target_files) > 0:
            print("Deleted overlays.")
