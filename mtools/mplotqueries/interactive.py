#!/usr/bin/env python3
"""Keyboard and mouse handlers for mplotqueries."""

import matplotlib.pyplot as plt

import mtools.mplotqueries.plottypes as plottypes


class InteractiveMixin(object):
    """Pan, zoom, opacity, and marker shortcuts for an open plot."""

    def print_shortcuts(self, scatter=False):
        print("\nkeyboard shortcuts (focus must be on figure window):\n")

        print("    %8s  %s" % ("p", "switch to pan mode"))
        print("    %8s  %s" % ("o", "switch to zoom mode"))
        print("    %8s  %s" % ("left/right", "back / forward"))
        print("    %8s  %s" % ("h", "home (original view)"))
        print("    %8s  %s" % ("l", "toggle log/linear y-axis"))
        print("    %8s  %s" % ("f", "toggle fullscreen"))
        print("    %8s  %s"
              % ("1-9", "toggle visibility of top 10 individual plots 1-9"))
        print("    %8s  %s" % ("0", "toggle visibility of all plots"))
        print("    %8s  %s" % ("-", "toggle visibility of legend"))
        if scatter:
            print("    %8s  %s"
                  % ("[/]", "decrease / increase opacity by 10%"))
            print("    %8s  %s" % ("{/}", "decrease / increase opacity by 1%"))
            print("    %8s  %s" % ("</>", "decrease / increase marker size"))
            print("    %8s  %s" % ("e", "toggle marker edges"))
        print("    %8s  %s" % ("g", "toggle grid"))
        print("    %8s  %s" % ("c", "toggle 'created with' footnote"))
        print("    %8s  %s" % ("s", "save figure"))
        print("    %8s  %s" % ("q", "quit mplotqueries"))

        print("")

    def onpick(self, event):
        """Called per artist (group), with possibly a list of indices."""
        if hasattr(event.artist, '_mt_legend_item'):
            # legend item, instead of data point
            idx = event.artist._mt_legend_item
            try:
                self.toggle_artist(self.artists[idx])
            except IndexError:
                pass
            return

        # only print logevents of visible points
        if not event.artist.get_visible():
            return

        # get PlotType and let it print that event
        plot_type = event.artist._mt_plot_type
        plot_type.clicked(event)

    def toggle_artist(self, artist):
        try:
            visible = artist.get_visible()
            artist.set_visible(not visible)
            plt.gcf().canvas.draw()
        except Exception:
            pass

    def _init_opacities(self):
        for artist in self.artists:
            if not hasattr(artist, '_mt_opacity'):
                artist._mt_opacity = artist.get_alpha()

    def _any_opacities_to_increase(self):
        for artist in self.artists:
            if artist._mt_opacity < 0.99:
                return True
        return False

    def _any_opacities_to_decrease(self):
        for artist in self.artists:
            if artist._mt_opacity > 0.01:
                return True
        return False

    def set_opacities(self):
        for artist in self.artists:
            if artist._mt_opacity > 1.0:
                artist.set_alpha(1.0)
            elif artist._mt_opacity < 0.01:
                artist.set_alpha(0.01)
            else:
                artist.set_alpha(artist._mt_opacity)

    def increase_opacity(self, amount):
        self._init_opacities()
        if self._any_opacities_to_increase():
            for artist in self.artists:
                artist._mt_opacity = artist._mt_opacity + amount
            self.set_opacities()

    def decrease_opacity(self, amount):
        self._init_opacities()
        if self._any_opacities_to_decrease():
            for artist in self.artists:
                artist._mt_opacity = artist._mt_opacity - amount
            self.set_opacities()

    def toggle_marker_edges(self):
        for artist in self.artists:
            if artist.get_markeredgewidth() != 0:
                artist._mt_markeredgewidth = artist.get_markeredgewidth()
                artist.set_markeredgewidth(0)
            else:
                artist.set_markeredgewidth(artist._mt_markeredgewidth)

    def _init_markersizes(self):
        for artist in self.artists:
            if not hasattr(artist, '_mt_markersize'):
                artist._mt_markersize = artist.get_markersize()

    def _any_markersizes_to_increase(self):
        for artist in self.artists:
            if artist._mt_markersize < 10.0:
                return True
        return False

    def _any_markersizes_to_decrease(self):
        for artist in self.artists:
            if artist._mt_markersize > 1.0:
                return True
        return False

    def set_markersizes(self):
        for artist in self.artists:
            if artist._mt_markersize > 10.0:
                artist.set_markersize(10.0)
            elif artist._mt_markersize < 1.01:
                artist.set_markersize(1.0)
            else:
                artist.set_markersize(artist._mt_markersize)

    def increase_marker_size(self, amount=1):
        self._init_markersizes()
        if self._any_markersizes_to_increase():
            for artist in self.artists:
                artist._mt_markersize = artist._mt_markersize + amount
            self.set_markersizes()

    def decrease_marker_size(self, amount=1):
        self._init_markersizes()
        if self._any_markersizes_to_decrease():
            for artist in self.artists:
                artist._mt_markersize = artist._mt_markersize - amount
            self.set_markersizes()

    def onpress(self, event):
        # number keys
        if event.key in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            idx = int(event.key) - 1
            try:
                self.toggle_artist(self.artists[idx])
            except IndexError:
                pass

        # 0, toggle all plots
        if event.key == '0':
            try:
                visible = any([a.get_visible() for a in self.artists])
            except AttributeError:
                return

            for artist in self.artists:
                artist.set_visible(not visible)
            plt.gcf().canvas.draw()

        # quit
        if event.key == 'q':
            raise SystemExit('quitting.')

        # toggle legend
        if event.key == '-':
            if self.legend:
                self.toggle_artist(self.legend)
                plt.gcf().canvas.draw()

        # toggle created footnote
        if event.key == 'c':
            self.toggle_artist(self.footnote)
            plt.gcf().canvas.draw()

        # toggle yaxis logscale
        if event.key == 'l':
            scale = plt.gca().get_yscale()
            if scale == 'linear':
                plt.gca().set_yscale('log')
            else:
                plt.gca().set_yscale('linear')

            plt.autoscale(True, axis='y', tight=True)
            # honor forced limits
            if self.args['ylimits']:
                plt.gca().set_ylim(self.args['ylimits'])

            plt.gcf().canvas.draw()

        # opacity
        if isinstance(self.plot_instance, plottypes.ScatterPlotType):
            if event.key == '[':
                self.decrease_opacity(0.10)
                plt.gcf().canvas.draw()

            if event.key == '{':
                self.decrease_opacity(0.01)
                plt.gcf().canvas.draw()

            if event.key == ']':
                self.increase_opacity(0.10)
                plt.gcf().canvas.draw()

            if event.key == '}':
                self.increase_opacity(0.01)
                plt.gcf().canvas.draw()

            # edge on/off
            if event.key == 'e':
                self.toggle_marker_edges()
                plt.gcf().canvas.draw()

            # marker size
            if event.key == '<':
                self.decrease_marker_size()
                plt.gcf().canvas.draw()

            if event.key == '>':
                self.increase_marker_size()
                plt.gcf().canvas.draw()
