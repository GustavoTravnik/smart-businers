#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SmartBusiners AI Engine - Web GUI Launcher
Execute directly with: python run_gui.py
"""
import uvicorn
from smartbusiners.gui.server import start_gui

if __name__ == "__main__":
    start_gui()
