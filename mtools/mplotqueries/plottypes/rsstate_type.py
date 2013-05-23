from mtools.mplotqueries.plottypes.base_type import BasePlotType


class RSStatePlotType(EventPlotType):
    """ This plot type derives from the event plot type (vertical lines), but instead of
        plotting arbitrary events, it will only accept lines that indicate a replica set change.

        Those lines either contain the string "is now in state" (for other members) or are
        of the form "[rsMgr] replSet PRIMARY" for own state changes. 

        A custom group_by method 'lastword()' groups those lines by their last word (which is
        representative of the new state) and an overloaded color_map() method assigns colors
        to each of those states, similar to the ones used in MMS.
    """

    plot_type_str = 'rsstate'

    # force group() to always use lastword method to group by
    group_by = 'lastword'

    colors = ['m', 'y', 'r', 'g', 'g', 'k', 'b', 'c']
    states = ['PRIMARY', 'SECONDARY', 'DOWN', 'STARTUP', 'STARTUP2', 'RECOVERING', 'ROLLBACK', 'ARBITER']

    
    def accept_line(self, logline):
        """ only match log lines containing 'is now in state' (reflects other node's state changes) 
            or of type "[rsMgr] replSet PRIMARY" (reflects own state changes). 
        """
        if "is now in state" in logline.line_str and logline.split_tokens[-1] in self.states:
            return True

        if "replSet" in logline.line_str and logline.thread == "rsMgr" and logline.split_tokens[-1] in self.states:
            return True

        return False


    def lastword(self, logline):
        """ group by the last token of the log line (PRIMARY, SECONDARY, ...) """
        return logline.split_tokens[-1]


    @classmethod
    def color_map(cls, group):
        """ change default color behavior to map certain states always to the same colors (similar to MMS). """
        try:
            state_idx = cls.states.index(group)
        except KeyError:
            # on any unexpected state, return black
            return 'k'
        return cls.colors[state_idx], cls.markers[0]
