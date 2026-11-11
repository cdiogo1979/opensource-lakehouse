"""Import path for the tpch notebooks, as in the workload_foundation suite."""

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
for _folder in (REPOSITORY_ROOT / "notebooks" / "workload" / "tpch" / "bronze", REPOSITORY_ROOT / "notebooks" / "workload" / "tpch" / "silver"):
    sys.path.insert(0, str(_folder))
sys.path.insert(0, str(REPOSITORY_ROOT / "notebooks" / "common"))
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
