"""Run monitor Lambda locally: python check_lambda.py

Set LLM_API_KEY environment variable (or update Settings defaults) before running.
"""
from __future__ import annotations

import json


def main() -> None:
    from monitor_lambda.domains.monitor.jobs.handler import handler

    result = handler({}, context=object())
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()