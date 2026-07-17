#!/usr/bin/env python3

"""
CLI Utility Functions
"""

import os
import shutil
import sys


def require_root():

    if os.geteuid() != 0:
        print("Error: Nestor requires root privileges.")
        print("Run using:\n")
        print("    sudo nestor ...")
        sys.exit(1)


def check_loader(loader_path):

    if not loader_path.exists():
        raise FileNotFoundError(
            f"Loader not found:\n{loader_path}"
        )


def terminal_width():

    return shutil.get_terminal_size(
        fallback=(80, 20)
    ).columns


def separator(char="="):

    print(char * terminal_width())