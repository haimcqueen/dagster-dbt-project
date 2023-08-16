import os
from pathlib import Path

from dagster import Definitions, OpExecutionContext
from dagster_dbt import DbtCliResource, build_schedule_from_dbt_selection, dbt_assets

# We expect the dbt project to be installed as package data.
# For details, see https://docs.python.org/3/distutils/setupscript.html#installing-package-data.
dbt_project_dir = Path(__file__).joinpath("..", "..", "dbt-project").resolve()
dbt = DbtCliResource(project_dir=os.fspath(dbt_project_dir))

# If DAGSTER_DBT_PARSE_PROJECT_ON_LOAD is set, a manifest will be created at runtime.
# Otherwise, we expect a manifest to be present in the project's target directory.
if os.getenv("DAGSTER_DBT_PARSE_PROJECT_ON_LOAD"):
    dbt_parse_invocation = dbt.cli(["parse"], manifest={}).wait()
    dbt_manifest_path = dbt_parse_invocation.target_path.joinpath("manifest.json")
else:
    dbt_manifest_path = dbt_project_dir.joinpath("target", "manifest.json")

@dbt_assets(manifest=dbt_manifest_path)
def jaffle_shop_dbt_assets(context: OpExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()


schedules = [
    build_schedule_from_dbt_selection(
        [jaffle_shop_dbt_assets],
        job_name="materialize_dbt_models",
        cron_schedule="0 0 * * *",
        dbt_select="fqn:*",
    )
]

defs = Definitions(
    assets=[jaffle_shop_dbt_assets],
    schedules=schedules,
    resources={
        "dbt": dbt,
    },
)

