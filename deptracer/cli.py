# deptracer/cli.py
import argparse
import sys
import urllib.request
import json
from .core import run_akdeptracer
from .explain import explain_problem
from . import __version__

def check_for_updates():
    """Pings the PyPI API and enforces version deprecation rules."""
    if __version__ == "0.1.0":
        print(f"\n\033[91m\033[1m[CRITICAL] You are running v{__version__} which contains known fatal syntax errors!\033[0m")
        print("\033[93mPlease upgrade immediately to a stable release.\033[0m")
        print(f"\033[92mRun \033[1mpip install --upgrade deptracer\033[0m\033[92m to patch your system.\033[0m\n")
        return

    try:
        print("\033[90mChecking global registry for updates...\033[0m")
        req = urllib.request.Request(
            "https://pypi.org/pypi/deptracer/json", 
            headers={'User-Agent': 'deptracer-cli'}
        )
        
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            latest = data["info"]["version"]

        local_v = tuple(map(int, __version__.split('.')))
        latest_v = tuple(map(int, latest.split('.')))

        if local_v < latest_v:
            print(f"\n\033[93m\033[1m[UPDATE AVAILABLE]\033[0m You are running v{__version__}, but v{latest} is live on PyPI!")
            print(f"\033[92mRun \033[1mpip install --upgrade deptracer\033[0m\033[92m to patch your system.\033[0m\n")
        else:
            # Matches if local_v == latest_v OR if you are developing ahead of PyPI!
            print("\033[92mYou are running the latest production build of deptracer.\033[0m\n")
            
    except Exception:
        # Silently pass on network timeouts/offline state
        pass
def main():

    if "--version" in sys.argv:
        print(f"deptracer v{__version__}")
        check_for_updates()
        sys.exit(0)

    cli_parser = argparse.ArgumentParser(prog="deptracer", description="Universal Dependency Auto-Patcher")
    cli_parser.add_argument("--version", action="store_true", help="Show version and check for updates")
    cli_parser.add_argument("-v", "--verbose", action="store_true", help="Enable raw engine logs and PyInstaller passthrough")
    
    subparsers = cli_parser.add_subparsers(dest="command", help="Available engine commands")
    
    build_parser = subparsers.add_parser("build", help="Initiate the self-healing loop")
    build_parser.add_argument("project_dir", help="Path to the folder containing the .spec file")
    build_parser.add_argument("binary_name", help="Name of the executable")
    build_parser.add_argument("spec_name", help="Name of the .spec file")
    
    subparsers.add_parser("explain", help="Diagnose the last failed compilation trace")

    args = cli_parser.parse_args()

    if args.command == "explain":
        explain_problem()
    elif args.command == "build":
        run_akdeptracer(args.project_dir, args.binary_name, args.spec_name, verbose=args.verbose)
    else:
        cli_parser.print_help()

if __name__ == "__main__":
    main()