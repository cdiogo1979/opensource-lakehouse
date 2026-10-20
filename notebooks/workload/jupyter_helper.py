# %% [markdown]
# # Jupyter startup helper
#
# Run this script from `init_environment.py` with `%run ./jupyter_helper.py`.
# It locates the repository, selects the development config, starts Spark, and
# exposes `spark` and `config` in the calling notebook's namespace.

# %%
import os
import sys
from pathlib import Path


working_directory = Path(os.getcwd()).resolve()
repository_root = next(
    (
        candidate
        for candidate in (working_directory, *working_directory.parents)
        if (candidate / "notebooks" / "common" / "job_runtime.py").is_file()
        and (candidate / "configs" / "dev.yml").is_file()
    ),
    None,
)
if repository_root is None:
    raise FileNotFoundError(
        "Start Jupyter from the lakehouse repository or one of its subdirectories."
    )

sys.path.insert(0, str(repository_root))
os.environ["LAKEHOUSE_ENVIRONMENT"] = "dev"

from notebooks.common.job_runtime import start_spark_job

spark, config = start_spark_job("init_environment")
