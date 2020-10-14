from mtools.mplotqueries.plottypes.base_type import BasePlotType

try:
    from matplotlib.dates import date2num
except ImportError as error:
    raise ImportError("Can't import matplotlib. See "
                      "https://matplotlib.org/users/installing.html "
                      "for instructions on how to install matplotlib."
                      "Error: " + str(error))


class EventPlotType(BasePlotType):

    plot_type_str = 'event'

    def plot_group(self, group, idx, axis):
        x = date2num([logevent.datetime for logevent in self.groups[group]])

        # event plots use axvline
        artists = []
        color, marker = self.color_map(group)

        for i, xcoord in enumerate(x):
            if i == 0:
                artist = axis.axvline(xcoord, linewidth=2, picker=5,
                                      color=color, alpha=0.8, label=group)
            else:
                artist = axis.axvline(xcoord, linewidth=2, picker=5,
                                      color=color, alpha=0.8)
            # add meta-data for picking
            artist._mt_plot_type = self
            artist._mt_group = group
            artist._mt_line_id = i
            artists.append(artist)

        axis.autoscale_view(scaley=False)
        return artists

    def clicked(self, event):
        group = event.artist._mt_group
        line_id = event.artist._mt_line_id
        print(self.groups[group][line_id].line_str)


class RSStatePlotType(EventPlotType):
    """
    RSStatePlotType object.

    This plot type derives from the event plot type (vertical lines), but
    instead of plotting arbitrary events, it will only accept lines that
    indicate a replica set change.

    Those lines either contain the string "is now in state" (for other members)
    or are of the form "[rsMgr] replSet PRIMARY" for own state changes.

    A custom group_by method 'lastword()' groups those lines by their last word
    (which is representative of the new state) and an overloaded color_map()
    method assigns colors to each of those states, similar to the ones used in
    MMS.
    """

    plot_type_str = 'rsstate'

    # force group() to always use lastword method to group by
    # group_by = 'lastword'

    colors = ['m', 'y', 'r', 'g', 'g', 'k', 'b', 'c']
    states = ['PRIMARY', 'SECONDARY', 'DOWN', 'STARTUP', 'STARTUP2',
              'RECOVERING', 'ROLLBACK', 'ARBITER']

    def accept_line(self, logevent):
        """
        Return True on match.

        Only match log lines containing 'is now in state' (reflects other
        node's state changes) or of type "[rsMgr] replSet PRIMARY" (reflects
        own state changes).
        """
        if ("is now in state" in logevent.line_str and
                logevent.split_tokens[-1] in self.states):
            return True

        if ("replSet" in logevent.line_str and
                logevent.thread == "rsMgr" and
                logevent.split_tokens[-1] in self.states):
            return True

        return False

    def group_by(self, logevent):
        """Group by the last token of the log line (PRIMARY, SECONDARY,...)."""
        return logevent.split_tokens[-1]

    @classmethod
    def color_map(cls, group):
        print("Group %s" % group)
        """
        Change default color behavior.

        Map certain states always to the same colors (similar to MMS).
        """
        try:
            state_idx = cls.states.index(group)
        except ValueError:
            # on any unexpected state, return black
            state_idx = 5
        return cls.colors[state_idx], cls.markers[0]
