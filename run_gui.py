#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SmartBusiners AI Engine - Web GUI Launcher
Execute directly with: python run_gui.py
"""
import os
import sys

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    os.environ["PYTHONIOENCODING"] = "utf-8"

from smartbusiners.gui.server import start_gui

if __name__ == "__main__":
    start_gui()
