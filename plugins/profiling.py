import os
import signal
import sys
import threading
import traceback

from cloudbot import hook
from cloudbot.util import web

PYMPLER_ENABLED = False

if PYMPLER_ENABLED:
    try:
        import pympler
        import pympler.muppy
        import pympler.summary
        import pympler.tracker
    except ImportError:
        pympler = None
else:
    pympler = None
try:
    import objgraph
except ImportError:
    objgraph = None


def create_tracker():
    if pympler is None:
        return None

    return pympler.tracker.SummaryTracker()


tr = create_tracker()


def get_name(thread_id):
    current_thread = threading.current_thread()
    if thread_id == current_thread.ident:
        is_current = True
        thread = current_thread
    else:
        is_current = False
        thread = None
        for t in threading.enumerate():
            if t.ident == thread_id:
                thread = t
                break

    if thread is not None:
        if thread.name is not None:
            name = thread.name
        else:
            name = "Unnamed thread"
    else:
        name = "Unknown thread"

    name = f"{name} ({thread_id})"
    if is_current:
        name += " - Current thread"

    return name


def get_thread_dump():
    code = []
    threads = [
        (get_name(thread_id), traceback.extract_stack(stack))
        for thread_id, stack in sys._current_frames().items()
    ]
    for thread_name, stack in threads:
        code.append(f"# {thread_name}")
        for filename, line_num, name, line in stack:
            code.append(f"{filename}:{line_num} - {name}")
            if line:
                code.append(f"    {line.strip()}")
        code.append("")  # new line
    return web.paste("\n".join(code), ext="txt")


@hook.command("threaddump", autohelp=False, permissions=["botcontrol"])
async def threaddump_command():
    """- Return a full thread dump"""
    return get_thread_dump()


@hook.command("objtypes", autohelp=False, permissions=["botcontrol"])
def show_types():
    """- Print object type data to the console"""
    if objgraph is None:
        return "objgraph not installed"
    objgraph.show_most_common_types(limit=20)
    return "Printed to console"


@hook.command("objgrowth", autohelp=False, permissions=["botcontrol"])
def show_growth():
    """- Print object growth data to the console"""
    if objgraph is None:
        return "objgraph not installed"
    objgraph.show_growth(limit=10)
    return "Printed to console"


@hook.command("pymsummary", autohelp=False, permissions=["botcontrol"])
def pympler_summary():
    """- Print object summary data to the console"""
    if pympler is None:
        return "pympler not installed / not enabled"
    all_objects = pympler.muppy.get_objects()
    summ = pympler.summary.summarize(all_objects)
    pympler.summary.print_(summ)
    return "Printed to console"


@hook.command("pymdiff", autohelp=False, permissions=["botcontrol"])
def pympler_diff():
    """- Print object diff data to the console"""
    if pympler is None:
        return "pympler not installed / not enabled"
    tr.print_diff()
    return "Printed to console"


# # Provide an easy way to get a threaddump, by using SIGUSR1 (only on POSIX systems)
if os.name == "posix":
    # The handler is called with two arguments: the signal number and the current stack frame
    # These parameters should NOT be removed
    def debug(sig, frame):
        print(get_thread_dump())

    signal.signal(signal.SIGUSR1, debug)  # Register handler
