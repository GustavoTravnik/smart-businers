#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SmartBusiners AI Engine - CLI Launcher
Execute directly with: python run_cli.py [command]
"""
import os
import sys

# Garante suporte UTF-8 no Windows Console
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    os.environ["PYTHONIOENCODING"] = "utf-8"

from smartbusiners.cli import app

if __name__ == "__main__":
    app()
