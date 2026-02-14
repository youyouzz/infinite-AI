#!/usr/bin/env python3
"""
Autonomous Coding Agent Demo - Long-Running Agent Harness
=========================================================

A minimal harness demonstrating long-running autonomous coding with Claude.
Implements the two-agent pattern (Initializer + Coding) from Anthropic's article:
https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

Example Usage:
    python autonomous_agent_demo.py --project-dir ./my_project
    python autonomous_agent_demo.py --project-dir ./my_project --max-iterations 5
"""
import argparse
import asyncio
import os
from pathlib import Path

from agent import run_autonomous_agent

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Autonomous Coding Agent - Long-running agent harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Phase 0: analyze requirement, output refined_requirements.md for review
  python autonomous_agent_demo.py --project-dir ./my_app

  # After reviewing refined_requirements.md, approve and start development
  python autonomous_agent_demo.py --project-dir ./my_app --approved

  # Limit iterations for testing
  python autonomous_agent_demo.py --project-dir ./my_app --max-iterations 5

Environment:
  ANTHROPIC_API_KEY  Your Anthropic API key (required)
        """,
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path("./generations/autonomous_demo_project"),
        help="Directory for the project",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum number of agent iterations (default: unlimited)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Claude model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--approved",
        action="store_true",
        help="Confirm refined requirements and start development (Initializer). Use after reviewing refined_requirements.md.",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("\nGet your API key from: https://console.anthropic.com/")
        print("\nThen set it:")
        print("  export ANTHROPIC_API_KEY='your-api-key-here'")
        return

    project_dir = args.project_dir
    if not project_dir.is_absolute() and "generations" not in str(project_dir):
        project_dir = Path("generations") / project_dir

    try:
        asyncio.run(
            run_autonomous_agent(
                project_dir=project_dir,
                model=args.model,
                max_iterations=args.max_iterations,
                approved=args.approved,
            )
        )
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        print("To resume, run the same command again")
    except Exception as e:
        print(f"\nFatal error: {e}")
        raise


if __name__ == "__main__":
    main()
