"""
Reconfigures stdout/stderr to UTF-8 with error-replacement so importing
drone_orchard_system (which prints an emoji banner at package-init time,
plus emoji throughout flight_controller.py's methods) doesn't crash under
non-UTF-8 consoles (e.g. Windows' default cp1252).

Import this module first, for its side effect, in every file that imports
anything from drone_orchard_system - import order matters here since the
reconfiguration must run before drone_orchard_system's package __init__
executes, and Python runs a package's __init__ on the first import of any
of its submodules.
"""
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

#print statement
print("success")