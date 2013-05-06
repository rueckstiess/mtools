from event_type import EventPlotType

class RSStatePlotType(EventPlotType):
    plot_type_str = 'rsstate'

    # force group() to always use lastword method to group by
    group_by = 'lastword'

    colors = ['m', 'y', 'r', 'g', 'g', 'k', 'b', 'c']
    states = ['PRIMARY', 'SECONDARY', 'DOWN', 'STARTUP', 'STARTUP2', 'RECOVERING', 'ROLLBACK', 'ARBITER']

    @classmethod
    def color_map(cls, group):
        """ change default color behavior to map certain states always to the same colors (similar to MMS). """
        try:
            state_idx = cls.states.index(group)
        except KeyError:
            # on any unexpected state, return black
            return 'k'
        return cls.colors[state_idx], cls.markers[0]


    def lastword(self, logline):
        """ group by the last token of the log line (PRIMARY, SECONDARY, ...) """
        return logline.split_tokens[-1]


    def accept_line(self, logline):
        """ only match log lines containing 'is now in state' (reflects other node's state changes) 
            or of type "[rsMgr] replSet PRIMARY" (reflects own state changes). 
        """
        if "is now in state" in logline.line_str and logline.split_tokens[-1] in self.states:
            return True

        if "replSet" in logline.line_str and logline.thread == "rsMgr" and logline.split_tokens[-1] in self.states:
            return True

        return False

