import argparse
import asyncio
import json
from pathlib import Path

from pwps_agent_api.workflow.auto import run_auto_draft


async def _async_main() -> None:
    parser = argparse.ArgumentParser(description="Run the pWPS Auto Draft MVP workflow.")
    parser.add_argument("--input", required=True, help="Natural-language pWPS request.")
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory where JSON outputs will be written.",
    )
    args = parser.parse_args()

    result = await run_auto_draft(args.input, args.output_dir)
    print(
        json.dumps(
            {
                "run_id": result.state.run_id,
                "output_dir": str(args.output_dir),
                "outputs": {name: str(path) for name, path in sorted(result.output_paths.items())},
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
