"""
Set system dependent paths in this file.

Add your system's path in this file and rename it paths_template.py -> paths.py
"""

import os
import sys

LATEX_SKELETON_PATH = ""
PRODUCTION_PATH = ""

for path in [LATEX_SKELETON_PATH, PRODUCTION_PATH]:
    if os.path.exists(path):
        pass
    else:
        sys.exit(f"Path '{path}' does not exist.")
