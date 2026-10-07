"""
Pytest configuration for HedgeDoc.
Ensures HedgeDoc root and parent workspace directory are in sys.path.
"""

import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
HEDGEDOC_ROOT = CURRENT_DIR.parent
WORKSPACE_ROOT = HEDGEDOC_ROOT.parent

for p in [str(WORKSPACE_ROOT), str(HEDGEDOC_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)
