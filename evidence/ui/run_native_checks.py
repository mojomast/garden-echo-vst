#!/usr/bin/env python3
"""Compile UI-only checks against the existing native build, without CMake edits."""
from pathlib import Path
import os
import shlex
import subprocess

root = Path(__file__).resolve().parents[2]
build = root / os.environ.get("GARDEN_UI_BUILD_DIR", "build/astra-ui")
commands = subprocess.check_output(["ninja", "-t", "commands", "GardenEcho_Standalone"], cwd=build, text=True).splitlines()
compile_line = next(line for line in commands if " -c " in line and line.endswith("/src/PluginEditor.cpp"))
compile_args = shlex.split(compile_line)
compile_args[compile_args.index("-o") + 1] = "NativeChecks.o"
compile_args[compile_args.index("-c") + 1] = str(root / "evidence/ui/NativeChecks.cpp")
compile_args += ["-I" + str(root / "src")]
for flag in ["-MT", "-MF"]:
    if flag in compile_args:
        idx = compile_args.index(flag)
        del compile_args[idx:idx + 2]
subprocess.run(compile_args, cwd=build, check=True)
link_line = next(line for line in commands if " -o " in line and 'Standalone/Garden Echo"' in line)
args = shlex.split(link_line)
start = args.index("&&") + 1
args = args[start:args.index("&&", start)]
args = [arg for arg in args if not arg.endswith(".o") and "--dependency-file=" not in arg]
args[args.index("-o") + 1] = "NativeChecks"
args.insert(1, "NativeChecks.o")
subprocess.run(args, cwd=build, check=True)
home = build / "checks-home"
home.mkdir(exist_ok=True)
subprocess.run(["xvfb-run", "-a", str(build / "NativeChecks")], cwd=root, check=True,
               env=dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home)))
