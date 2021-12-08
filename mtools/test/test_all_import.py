from functools import wraps

# tools without any external dependencies
from mtools.mlogfilter.mlogfilter import MLogFilterTool
from mtools.mloginfo.mloginfo import MLogInfoTool

tools = [MLogFilterTool, MLogInfoTool]


# mlaunch depends on pymongo
try:
    from mtools.mlaunch.mlaunch import MLaunchTool
    tools.append(MLaunchTool)
except ImportError:
    pass


# mplotqueries depends on matplotlib
try:
    from mtools.mplotqueries.mplotqueries import MPlotQueriesTool
    tools.append(MPlotQueriesTool)
except ImportError:
    pass


def all_tools(fn):
    """
    This is a decorator for test functions, that runs a loop over all command
    line tool classes imported above and passes each class to the test
    function.

    To use this decorator, the test function must accept a single
    parameter. Example:

        @all_tools
        def test_something(tool_cls):
            tool = tool_cls()
            # test tool here ...
    """
    @wraps(fn)
    # copies __name__ of the original function, pytest requires the name
    # to start with "test_"
    def new_func():
        for tool in tools:
            fn(tool)
    return new_func


def test_import_all():
    """
    Import all tools from mtools module.

    The tools that have external dependencies will only be imported if the
    dependencies are fulfilled. This test just passes by default because the
    imports are tested implicitly by loading this file.
    """
    pass
