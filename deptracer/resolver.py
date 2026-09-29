# linux_core/resolver.py
import subprocess
import os
import time
import re
import site

STATE_LOG = ".akdeptracer_state"

def set_pipeline_state(stage, error, fix):
    with open(STATE_LOG, "w") as f:
        f.write(f"{stage}|{error}|{fix}")

def safe_realpath(path: str, max_depth=10) -> str:
    """Follows symlinks safely to prevent infinite circular loop crashes."""
    seen = set()
    current = path
    
    for _ in range(max_depth):
        if current in seen:
            print(f"[RESOLVER] Circular symlink detected at {current}. Aborting resolution.")
            set_pipeline_state("RESOLVER", "Circular symlink detected.", "Check for circular symlinks in the filesystem.")
            return path
        seen.add(current)
        
        if os.path.islink(current):
            current = os.readlink(current)
            if not os.path.isabs(current):
                current = os.path.join(os.path.dirname(path), current)
        else:
            return os.path.abspath(current)
            
    print(f"[RESOLVER] Symlink depth exceeded at {path}")
    set_pipeline_state("RESOLVER", "Symlink resolution depth exceeded.", "Check for circular symlinks or excessive nesting.")
    return os.path.abspath(path)

def hunt_missing_library(file_name, project_dir=".", max_retries=3, verbose=False):
    """Smart Hunt: Handles hard links, versioning, flaky network retries, and Python Envs."""
    
    base_name = re.sub(r'\.so(\.\d+)*$', '.so', file_name)
    variants = [
        file_name,
        base_name,
        base_name + ".1",
        base_name + ".0",
    ]
    
    search_results = []
    
    safe_zones = [
        os.path.abspath(project_dir),
        os.path.abspath(os.path.join(project_dir, "lib")),
        os.path.abspath(os.path.join(project_dir, "build/lib"))
    ]
    try:
        safe_zones.extend(site.getsitepackages())
        safe_zones.append(site.getusersitepackages())
    except Exception:
        pass
    
    for attempt in range(max_retries):
        for variant in variants:
            
            # Phase 1: Fast direct path checking within Safe Zones
            for search_dir in safe_zones:
                if not os.path.exists(search_dir):
                    continue
                if verbose:
                    print(f"    \033[90m[RESOLVER-VERBOSE] Scanning dir: {search_dir} for {variant}\033[0m")
                candidate = os.path.join(search_dir, variant)
                if os.path.exists(candidate) and os.access(candidate, os.R_OK):
                    real_target = safe_realpath(candidate)
                    
                    if os.path.islink(candidate):
                        print(f"[RESOLVER] Symlink: {candidate} → {real_target}")
                    else:
                        stat_info = os.stat(candidate)
                        
                    if variant not in [res[0] for res in search_results]:
                        search_results.append((variant, real_target))

            for zone in safe_zones:
                if not os.path.exists(zone):
                    continue
                if verbose:
                    print(f"    \033[90m[RESOLVER-VERBOSE] Initiating deep scan in safe zone: {zone} for {variant}...\033[0m")

                command = [
                    "find", zone, "-type", "f", "-name", variant, "-readable", "-print", "-quit"
                ]
                
                try:
                    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=30)
                    found_path = result.stdout.strip()
                    if found_path and os.access(found_path, os.R_OK):
                        real_target = safe_realpath(found_path)
                        
                        if os.path.islink(found_path):
                            print(f"[RESOLVER] Symlink: {found_path} → {real_target}")
                        else:
                            stat_info = os.stat(found_path)
                            
                        if variant not in [res[0] for res in search_results]:
                            search_results.append((variant, real_target))
                except Exception as e:
                    pass
        
        if search_results:
            break
            
        if attempt < max_retries - 1:
            print(f"[RESOLVER] Target unreadable/missing. Retrying {attempt+1}/{max_retries}...")
            set_pipeline_state("RESOLVER",  "File not found or unreadable.", "Check file existence, permissions, and system load. ")
            time.sleep(1)

    if len(search_results) > 1:
        print(f"[RESOLVER] Multiple versions found:")
        set_pipeline_state("RESOLVER", "Multiple file variants found.", "Manually verify which version is correct for your application.")
        for i, (variant, path) in enumerate(search_results):
            print(f"  [{i}] {variant} → {path}")
        for variant, path in search_results:
            if os.path.abspath(project_dir) not in path:
                return path
        return search_results[0][1]
    elif search_results:
        return search_results[0][1]
        
    print(f"[RESOLVER] Target: {file_name} not found in Safe Zones. (Likely System OS Noise).")
    set_pipeline_state("RESOLVER", "File not found.", "Check file existence and search paths.")
    return None