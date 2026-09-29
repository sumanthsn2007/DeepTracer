# linux_core/explain.py
import os

# We redefine the UI here to prevent messy circular imports with core.py
class UI:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[34m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @classmethod
    def success(cls, text): print(f"{cls.GREEN}{cls.BOLD}{text}{cls.RESET}")
    @classmethod
    def error(cls, text): print(f"{cls.RED}{cls.BOLD}{text}{cls.RESET}")
    @classmethod
    def warn(cls, text): print(f"{cls.YELLOW}{text}{cls.RESET}")
    @classmethod
    def layout(cls, text): print(f"{cls.BOLD}{cls.BLUE}{text}{cls.RESET}")

STATE_LOG = ".akdeptracer_state"

def explain_problem():
    """The Deep Diagnostic Engine for akdeptracer."""
    
    if not os.path.exists(STATE_LOG):
        UI.error("Diagnosis: Unknown Pipeline State.")
        UI.warn("Explanation: The solution to this problem is not known (No state log found).")
        return

    with open(STATE_LOG, "r") as f:
        data = f.read().split("|")

    if len(data) < 3:
        UI.error("Diagnosis: Corrupted Pipeline State.")
        UI.warn("Explanation: The solution to this problem is not known (State log malformed).")
        return

    stage, error, fix = data[0], data[1], data[2]

    if stage == "SUCCESS":
        UI.success("[EXPLAIN] The last build was 100% SUCCESSFUL!")
        UI.success("Your executable is fully patched and safe for production.")
        return

    KNOWN_ERRORS = {
        "ENVIRONMENT": ("Environment Compatibility", f"{error} deptracer requires the Linux kernel. Switch to a Linux machine or WSL2."),
        "SETUP": ("Missing Configuration", f"{error} {fix}"),
        "TRACER": ("Sandbox Failure", f"{error} {fix}"),
        "APPLICATION": ("Runtime Logic Error", f"Your PyInstaller libraries are perfectly patched, but your Python application crashed (Code {error}). {fix}"),
        "RESOLVER": ("Missing System Dependency", f"{error} {fix}"),
        "FIXER": ("File Permission Lock", f"{error} {fix}"),
        "COMPILER": ("PyInstaller Build Crash", f"{error} {fix}"),
        "DEADLOCK": ("Deadlock Detected", f"{error} {fix}"),
        "PARSER": ("Kernel Log Parsing Issue", f"{error} {fix}")
    }

    if stage in KNOWN_ERRORS:
        title, details = KNOWN_ERRORS[stage]
        UI.error(f"Pipeline crashed at stage: [{stage}]")
        UI.warn(f"Diagnosis: {title}")
        UI.success(f"Recommended Fix: {details}")
    else:
        UI.error(f"Pipeline crashed at stage: [{stage}]")
        UI.warn(f"Reported Error: {error}")
        UI.error("Explanation: The solution to this problem is not currently known.")