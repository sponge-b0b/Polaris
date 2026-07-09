from __future__ import annotations

import asyncio
import json

from core.workflow.bootstrap.workflow_module import create_workflow_module
from core.workflow.examples.example_workflow import ExampleWorkflow


async def main() -> None:
    workflow_module = create_workflow_module(
        workflow_definitions=[
            ExampleWorkflow(),
        ],
        workflow_tags={
            "example_workflow": ("example", "demo"),
        },
        overwrite=True,
    )

    runtime = workflow_module.start()

    result = await runtime.facade.run_workflow(
        workflow_name="example_workflow",
        mode="live",
        archive_on_completion=True,
        checkpoint_on_completion=True,
    )

    print(
        json.dumps(
            result.to_dict(),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    asyncio.run(
        main(),
    )
