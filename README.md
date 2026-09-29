# deptracer — Auto-Fix PyInstaller Dependency Hell

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)]()
[![Linux](https://img.shields.io/badge/Platform-Linux-green)]()

## The Problem

You bundle a Python app with PyInstaller. It works on your machine. You ship it to a customer's clean machine. It crashes:

```
ImportError: libmagic.so: cannot open shared object file: No such file or directory
```

or

```
FileNotFoundError: [Errno 2] No such file or directory: 'model.pt'
```

**PyInstaller doesn't know about dependencies you haven't explicitly told it.**

## The Solution

**deptracer** automatically discovers missing dependencies and patches your binary.

```bash
deptracer build /path/to/project app app.spec
```

That's it. Your binary now works everywhere.

---

## What deptracer Does

1. **Compiles** your Python app with PyInstaller
2. **Traces** all system calls using `strace` in a sandbox
3. **Identifies** missing files (binaries, models, configs)
4. **Locates** them on your system
5. **Patches** PyInstaller's spec to bundle them
6. **Recompiles** and repeats until everything is bundled
7. **Tests** in an isolated sandbox to verify self-containment

All automatically. No manual spec editing.

---

## What It Bundles

- **Binary Dependencies**: `.so`, `.dll`, `.dylib` (C/C++ libraries)
- **ML Models**: `.pt`, `.onnx`, `.h5` (PyTorch, ONNX, TensorFlow)
- **Data Files**: `.json`, `.yaml`, `.npy`, `.csv` (configs, datasets)
- **Media**: `.wav`, `.jpg`, `.png` (audio, images)

---

## Installation

```bash
pip install deptracer
```

### Requirements

- **Linux** (x86_64 or arm64)
- **Python 3.8+**
- **PyInstaller 5.0+**
- `strace` (usually pre-installed)
- `bwrap` (for sandboxing)

```bash
# On Ubuntu/Debian:
sudo apt-get install strace bubblewrap

# On Fedora/RHEL:
sudo dnf install strace bubblewrap

# On Alpine:
apk add strace bubblewrap
```

---

## Quick Start

### 1. Build your app normally

```bash
# Create your Python app
cat > my_app.py << 'EOF'
import magic  # Needs libmagic.so

def detect_file(path):
    mime = magic.Magic(mime=True)
    return mime.from_file(path)

if __name__ == '__main__':
    print(detect_file('/etc/passwd'))
EOF

# Generate PyInstaller spec
pyinstaller --onefile my_app.py
```

### 2. Use deptracer

```bash
deptracer build . my_app my_app.spec
```

### 3. Done!

```bash
./dist/my_app
# Works! Even on machines without libmagic installed
```

---

## Real-World Example: File Type Detective

Here's a complete example that uses:
- Binary dependencies: `libmagic.so`
- Data dependencies: magic database files
- ML dependencies: None (but easily extensible)

### The Application

```python
import magic
import sys

class FileTypeDetective:
    def __init__(self):
        self.detector = magic.Magic(mime=True)
    
    def detect(self, file_path):
        return self.detector.from_file(file_path)

def main():
    detective = FileTypeDetective()
    
    test_files = [
        '/etc/passwd',      # Text file
        '/bin/bash',        # ELF binary
        '/usr/share/doc',   # Directory
    ]
    
    for path in test_files:
        try:
            file_type = detective.detect(path)
            print(f"{path}: {file_type}")
        except Exception as e:
            print(f"{path}: Error - {e}")

if __name__ == '__main__':
    main()
```

### Without deptracer (fails):

```bash
$ pyinstaller --onefile app.py
$ ./dist/app
Traceback (most recent call last):
  File "magic.py", line 1, in <module>
    from ctypes import find_library
ImportError: libmagic.so.1: cannot open shared object file
```

### With deptracer (works):

```bash
$ deptracer build . app app.spec

[CORE] INITIATING SWEEP ITERATION: 1
[TRACER] Initiating Zero-Trust Isolation Sandbox...
[PARSER] Found missing: libmagic.so.1
[RESOLVER] Located: /usr/lib/libmagic.so.1
[FIXER] Patching app.spec...
[COMPILER] Recompiling...

[CORE] EXECUTABLE IS FULLY SAFE FOR PRODUCTION!

$ ./dist/app
/etc/passwd: text/plain
/bin/bash: application/x-executable
/usr/share/doc: inode/directory
```

---

## Advanced Features

### Multi-Level Dependencies

deptracer handles complex dependency chains:

```
Application
  ├─ libA.so (found, bundled)
  │   └─ libB.so (not found yet)
  │       └─ libC.so (not found yet)
  └─ model.pt (found, bundled)
      └─ config.json (found, bundled)

Iteration 1: Finds and bundles libA.so
Iteration 2: Finds and bundles libB.so
Iteration 3: Finds and bundles libC.so
Iteration 4: Clean! ✅
```

### Plugin Systems

If your app discovers plugins at runtime:

```python
import glob
import ctypes

for plugin_path in glob.glob('plugins/*.so'):
    plugin = ctypes.CDLL(plugin_path)  # deptracer catches this!
```

deptracer will find and bundle all dynamically-loaded plugins.

### Version-Specific Libraries

If you have multiple versions of a library:

```
/usr/lib/libcustom.so.1     (old)
/usr/lib/libcustom.so.2     (new)
/home/user/vendor/lib/libcustom.so  (your version)
```

deptracer intelligently selects the correct version based on load order.

---

## How It Works

### Step 1: Tracer (Sandbox Execution)

deptracer runs your binary in a Bubblewrap sandbox, tracing all system calls:

```
strace -e trace=file -o trace.log ./dist/app

Trace output:
openat(AT_FDCWD, "/usr/lib/libmagic.so.1", O_RDONLY) = 3 ✅ found
openat(AT_FDCWD, "/tmp/_MEI.../libmagic.so.1", O_RDONLY) = -1 ENOENT ❌ missing
```

### Step 2: Parser (Dependency Detection)

Parses strace output to identify missing files:

```python
# Finds:
# - Binary libraries (.so, .dll, .dylib)
# - ML models (.pt, .onnx, .h5)
# - Data files (.json, .yaml, .csv)
# - Media (.wav, .jpg, .png)

# Filters out:
# - System libraries (already available)
# - Python internals (_ctypes, _socket, etc)
# - Architecture-specific variants (glibc-hwcaps)
```

### Step 3: Resolver (File Location)

Searches your system for missing files:

```python
Search order:
1. Project directory
2. Project lib/ subdirectory
3. Project build/ subdirectory
4. System paths (/usr/lib, /lib64, etc)
5. Deep search (find /, with timeout)
```

### Step 4: Fixer (Spec Patching)

Patches PyInstaller spec to bundle dependencies:

```python
# For binaries:
a.binaries += [
    ('/usr/lib/libmagic.so.1', '/usr/lib/libmagic.so.1', 'BINARY')
]

# For data:
a.datas += [
    ('/home/user/.cache/magic.mgc', 'magic/'),
]
```

### Step 5: Compiler (Rebuild)

Recompiles with PyInstaller and repeats until clean.

---

## Troubleshooting

### Binary crashes with "library not found"

Run deptracer again:

```bash
deptracer build . app app.spec
```

It will find any remaining missing dependencies.

### "File not found" errors during bundling

Check if the file exists on your system:

```bash
# deptracer will show which file is missing
# Find it manually:
find / -name "libmagic.so*" 2>/dev/null

# If not found, install it:
sudo apt-get install libmagic1
```

### Binary is too large

deptracer bundles all dependencies. This is by design — the binary must be self-contained.

Typical sizes:
- Simple app: 5-10MB
- With ML models: 50-200MB
- With heavy dependencies: 500MB+

### Performance issues

deptracer traces all system calls. On slow systems:
- Tracing can take 10-30 seconds
- Use `-v` flag for verbose output to see progress

---

## Advanced Usage

### Custom Search Paths

```python
# In your project, create deptracer_config.py:
SEARCH_PATHS = [
    '/opt/custom/lib',
    '/home/user/vendor',
    '/usr/local/lib',
]
```

### Exclude System Libraries

```bash
# Skip bundling system libraries
deptracer build . app app.spec --exclude-system
```

### Verbose Output

```bash
# See all steps:
deptracer build . app app.spec -v
```

---

## Architecture

deptracer is designed to be **language-agnostic**. Currently supports:
- ✅ **Python** (PyInstaller)

Planned (v0.2+):
- 🚧 **C/C++** (ELF binaries with RPATH patching)
- 🚧 **Java** (JAR bundling)
- 🚧 **Windows** (DLL bundling)

---

## Performance

Typical build time with deptracer:

| Scenario | Time |
|----------|------|
| Simple app (1-2 libs) | 15-30s |
| Medium app (5-10 libs) | 30-60s |
| Complex app (20+ libs) | 1-3 minutes |
| With ML models | 2-10 minutes |

Most time is spent in PyInstaller recompilation, not deptracer.

---

## Testing

Run the regression suite:

```bash
# Full test suite with 9 test cases
python regression_suite.py

# Includes:
# - Simple chains (libA.so)
# - Deep nesting (vendor/deep/nested/)
# - Circular symlinks
# - Plugin systems
# - Real project test (python-libmagic)
```

---

## Contributing

deptracer is open source. Contributions welcome!

- **Bug reports**: GitHub Issues
- **Feature requests**: GitHub Discussions
- **Code**: Pull requests welcome

---

## License

MIT License — See LICENSE file for details

---

## Acknowledgments

deptracer uses:
- `strace` for system call tracing
- `bwrap` (Bubblewrap) for sandboxing
- `patchelf` for binary patching
- `PyInstaller` for Python bundling


##  TatHack Prelim Challenge

This repository is your starting point. There are two things to work on, and you're free to lean into either or both:

**1. Fix what's broken.** Don't trust that a feature works just because it doesn't throw an error — test it against a real scenario (build an app with a genuine runtime dependency, run the patched binary on a clean environment) and check what actually got bundled, not just whether deptracer printed success.

**2. Build what's missing.** Pick one or more ideas from the list below — or bring your own. We're not scoring on how many features you bolt on; we're scoring on whether what you build is genuinely useful, correctly wired end-to-end, and whether you can explain the trade-offs you made.

---

##  Where You Can Take This

deptracer is a working prototype, not a finished product. Here's where the biggest opportunities are — pick what's interesting, you don't need to attempt all of it:

### Cross-Platform & Language Support
- Windows support — DLL bundling (planned 0.3)
- macOS support — dylib bundling + codesigning (planned 0.3)
- C/C++ binaries — RPATH patching for non-Python ELF executables (planned 0.2)
- Java — JAR bundling

### Reliability & Scale
- **Timeouts on the trace and build steps.** `tracer.run_and_trace()` calls `process.communicate()` with no timeout today, so a traced app that stalls (e.g. waiting on a hung API call) blocks the whole pipeline forever instead of failing cleanly.
- **An overall time/iteration budget.** Each PyInstaller rebuild can take 30–60s+, and the sweep loop has no cap on iterations or wall-clock time — a dependency chain that surfaces one file per iteration can run for hours with nothing stopping it short of the OS killing the process.
- Resume from the last successful iteration instead of re-sweeping from scratch on every run.
- Parallelize independent dependency lookups instead of resolving one at a time.

### Product & Experience
- A dry-run mode that reports what would be bundled without actually rebuilding.
- Richer diagnostics in `deptracer explain` — it currently reads one flat state log; a structured history of every iteration would make debugging a failed build much easier.
- Progress reporting that names which specific dependency is being hunted, not just a generic spinner.

### Environment & Dependency Coverage
- Support conda/poetry/pipenv layouts, not just `site-packages`.
- Fully wire the custom search paths config (see Advanced Usage) into the resolver.
- License compliance — flag GPL/LGPL-licensed binaries before they get silently bundled into a shipped binary.

### Integrations
- A GitHub Action that runs the sweep on every release build.
- CI-friendly structured (JSON) output instead of only colored terminal output.

The goal is a binary that actually runs on a clean machine — not one that just prints "safe for production."

---

## TL;DR

```bash
# Install
pip install deptracer

# Bundle your app
deptracer build . my_app my_app.spec

# Ship it!
./dist/my_app  # Works everywhere
```

That's it. Your dependencies are handled automatically.

**Ship with confidence; With Love Sooryagayathri and Arvind** 
