import os
import sys
import platform
import time
from pathlib import Path

class UI:
    GREEN = "\033[92m"
    RED = "\033[91m"
    BLUE = "\033[34m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @classmethod
    def step(cls, module, text):
        print(f"{cls.BLUE}{cls.BOLD}[{module}]{cls.RESET} {text}")

    @classmethod
    def success(cls, module, text):
        print(f"{cls.GREEN}{cls.BOLD}[{module}] {text}{cls.RESET}")

    @classmethod
    def error(cls, module, text):
        print(f"{cls.RED}{cls.BOLD}[{module}] {text}{cls.RESET}")

from . import tracer
from . import parser
from . import resolver
from . import fixer
from . import compiler

STATE_LOG = ".akdeptracer_state"

def set_pipeline_state(stage, error, fix):
    with open(STATE_LOG, "w") as f:
        f.write(f"{stage}|{error}|{fix}")

def run_akdeptracer(project_dir, binary_name, spec_name, verbose=False):
    
    if platform.system().lower() != "linux":
        UI.error("CORE", "Non-Linux OS detected.")
        set_pipeline_state("ENVIRONMENT", "Non-Linux OS detected.", "Use Linux.")
        sys.exit(1)

    root_dir = Path(project_dir).resolve()
    
    # 🎯 NEW: AUTONOMOUSLY GENERATE THE RUNTIME PROBE
    probe_path = root_dir / "_akdeptracer_probe.py"
    with open(probe_path, "w") as f:
        f.write("import builtins\nimport sys\n_orig = builtins.__import__\n")
        f.write("def _probe(*args, **kwargs):\n")
        f.write("    try: return _orig(*args, **kwargs)\n")
        f.write("    except ImportError as e:\n")
        f.write("        sys.stderr.write(f'[DEPTRACER-PROBE] {e}\\n')\n")
        f.write("        sys.stderr.flush()\n")
        f.write("        raise\n")
        f.write("builtins.__import__ = _probe\n")

    target_binary = root_dir / "dist" / binary_name
    spec_file = root_dir / spec_name
    
    if not spec_file.exists():
        UI.error("CORE", f"Setup Error: {spec_file} not found.")
        sys.exit(1)

    iteration = 1
    unresolved_from_previous = set()
    historically_injected = set()
    known_system_noise = set() 
    
    while True:
        print("")
        UI.step("CORE", f"Starting iteration {iteration}")
        
        trace_result = tracer.run_and_trace(str(target_binary), str(project_dir), verbose=verbose)
        if not trace_result or not trace_result[0]:
            UI.error("CORE", "Tracer failed. Pipeline aborted.")
            break
        else:
            UI.step("TRACER", "Sandbox Created. Successfully Communicated with Kernel ")
            
        log_path, stderr_log, returncode = trace_result
        resolved_payload = {'binaries': [], 'data': [], 'hidden_imports': []}
        iteration_unresolved = set()
        new_fixes_made = 0
        
        deps = parser.extract_missing_libraries_and_hidden_imports(log_path, stderr_log, verbose=verbose)
            
        if not deps['binaries'] and not deps['data'] and not deps['hidden_imports']:
            print("")
            if returncode != 0:
                UI.error("CORE", f"DEPENDENCIES SECURE, BUT APPLICATION CRASHED (Code {returncode})")
            else:
                UI.success("CORE", "EXECUTABLE IS FULLY SAFE FOR PRODUCTION!")
            break

        for category in ['binaries', 'data']:
            for missing_full_path in deps[category]:
                target_filename = os.path.basename(missing_full_path)

                if target_filename in historically_injected:
                    print("")
                    UI.error("CORE", f"FATAL: Absolute Path / Logic Deadlock on '{target_filename}'!")
                    sys.exit(1)

                if target_filename in known_system_noise:
                    continue

                UI.step("PARSER", f" Missing file named {target_filename}")

                found_path = resolver.hunt_missing_library(target_filename, str(project_dir), verbose=verbose)
                if found_path:
                    UI.step("RESOLVER", f"Found {target_filename} at {found_path}")
                    resolved_payload[category].append((target_filename, found_path))
                    historically_injected.add(target_filename) 
                    new_fixes_made += 1
                else:
                    known_system_noise.add(target_filename)
                    iteration_unresolved.add(target_filename)
                    
        for module in deps['hidden_imports']:
            if module in historically_injected:
                continue
            UI.step("PARSER", f" Missing Python module {module}")
            resolved_payload['hidden_imports'].append(module)
            historically_injected.add(module)
            new_fixes_made += 1

        if new_fixes_made == 0 and not iteration_unresolved:
            print("")
            if returncode != 0:
                UI.error("CORE", f"DEPENDENCIES SECURE, BUT APPLICATION CRASHED (Code {returncode})")
            else:
                UI.success("CORE", "SYSTEM NOISE ISOLATED. EXECUTABLE IS FULLY SAFE FOR PRODUCTION!")
            break

        if iteration_unresolved == unresolved_from_previous and iteration_unresolved:
            print("")
            UI.error("CORE", f"FATAL: Unresolvable dependencies detected:")
            break
            
        unresolved_from_previous = iteration_unresolved
        
        total_patches = sum(len(v) for v in resolved_payload.values())
        if not fixer.patch_spec_file(str(spec_file), resolved_payload):
            UI.error("CORE", "Fixer failed to patch the .spec file. Pipeline aborted.")
            break
        else:
            UI.step("FIXER", f"Spec file patched with {total_patches} new entries. Ready to recompile.")
            
        if not compiler.build(str(spec_file),iteration=iteration,verbose=verbose):
            UI.error("CORE", "Compiler failed to build the executable. Pipeline aborted.")
            break
        else:
            UI.step("COMPILER", "Build successful. Checking for remaining issues...")
        iteration += 1