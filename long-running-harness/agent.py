"""
Agent Session Logic
===================

Core agent interaction functions for running autonomous coding sessions.
Reference: Anthropic - Effective harnesses for long-running agents
https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
"""

import asyncio
from pathlib import Path
from typing import Optional

from claude_code_sdk import ClaudeSDKClient

from client import create_client
from progress import print_session_header, print_progress_summary
from prompts import (
    get_initializer_prompt,
    get_coding_prompt,
    get_requirements_refinement_prompt,
    copy_spec_to_project,
    use_refined_spec_as_app_spec,
)

AUTO_CONTINUE_DELAY_SECONDS = 3
REFINED_SPEC_FILE = "refined_requirements.md"


async def run_agent_session(
    client: ClaudeSDKClient,
    message: str,
    project_dir: Path,
) -> tuple[str, str]:
    """
    Run a single agent session using Claude Agent SDK.

    Returns:
        (status, response_text) where status is:
        - "continue" if agent should continue working
        - "error" if an error occurred
    """
    print("Sending prompt to Claude Agent SDK...\n")

    try:
        await client.query(message)

        response_text = ""
        async for msg in client.receive_response():
            msg_type = type(msg).__name__

            if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                for block in msg.content:
                    block_type = type(block).__name__

                    if block_type == "TextBlock" and hasattr(block, "text"):
                        response_text += block.text
                        print(block.text, end="", flush=True)
                    elif block_type == "ToolUseBlock" and hasattr(block, "name"):
                        print(f"\n[Tool: {block.name}]", flush=True)
                        if hasattr(block, "input"):
                            input_str = str(block.input)
                            if len(input_str) > 200:
                                print(f" Input: {input_str[:200]}...", flush=True)
                            else:
                                print(f" Input: {input_str}", flush=True)

            elif msg_type == "UserMessage" and hasattr(msg, "content"):
                for block in msg.content:
                    if type(block).__name__ == "ToolResultBlock":
                        result_content = getattr(block, "content", "")
                        is_error = getattr(block, "is_error", False)

                        if "blocked" in str(result_content).lower():
                            print(f" [BLOCKED] {result_content}", flush=True)
                        elif is_error:
                            print(f" [Error] {str(result_content)[:500]}", flush=True)
                        else:
                            print(" [Done]", flush=True)

        print("\n" + "-" * 70 + "\n")
        return "continue", response_text

    except Exception as e:
        print(f"Error during agent session: {e}")
        return "error", str(e)


def _print_review_instructions(project_dir: Path) -> None:
    """Print instructions for user to review refined requirements and re-run with --approved."""
    refined_path = project_dir / REFINED_SPEC_FILE
    print("\n" + "=" * 70)
    print(" 需求已生成，请审阅")
    print("=" * 70)
    print(f"\n详细需求文档已写入: {refined_path.resolve()}")
    print("\n请审阅该文件。您可以直接编辑以修改或补充需求。")
    print("审阅满意后，使用以下命令确认并开始开发（生成 feature_list 与初始化）：")
    print(f"\n  python autonomous_agent_demo.py --project-dir {project_dir} --approved\n")
    print("=" * 70)


async def run_autonomous_agent(
    project_dir: Path,
    model: str,
    max_iterations: Optional[int] = None,
    approved: bool = False,
) -> None:
    """
    Run the autonomous agent loop.

    Phases:
    - Phase 0 (Requirements Refinement): No refined_requirements.md → run analyst, then exit for user review.
    - Phase 1 (Initializer): refined_requirements.md exists and approved → run initializer (feature_list, init.sh, git).
    - Phase 2 (Coding): feature_list.json exists → run coding agent in a loop.
    """
    print("\n" + "=" * 70)
    print(" AUTONOMOUS CODING AGENT - Long-Running Harness")
    print("=" * 70)
    print(f"\nProject directory: {project_dir}")
    print(f"Model: {model}")
    print(f"Max iterations: {max_iterations or 'Unlimited'}")
    print(f"Approved (use refined spec): {approved}")
    print()

    project_dir.mkdir(parents=True, exist_ok=True)

    tests_file = project_dir / "feature_list.json"
    refined_file = project_dir / REFINED_SPEC_FILE

    # --- Phase 0: Requirements refinement (before feature_list exists) ---
    if not tests_file.exists():
        if not refined_file.exists():
            # Run Requirements Analyst: analyze app_spec → write refined_requirements.md
            print("Phase 0: 需求分析与完善（用户将审阅后再进入开发）")
            print("=" * 70 + "\n")
            copy_spec_to_project(project_dir)
            client = create_client(project_dir, model)
            print_session_header(
                1, is_initializer=False, session_type_override="REQUIREMENTS ANALYST"
            )
            prompt = get_requirements_refinement_prompt()
            async with client:
                await run_agent_session(client, prompt, project_dir)
            _print_review_instructions(project_dir)
            return
        if not approved:
            _print_review_instructions(project_dir)
            return
        # approved and refined exists: use refined as app_spec and run Initializer
        use_refined_spec_as_app_spec(project_dir)
        is_first_run = True
    else:
        is_first_run = False
        print("Continuing existing project")
        print_progress_summary(project_dir)

    # --- Phase 1 (Initializer) + Phase 2 (Coding) loop ---
    iteration = 0

    while True:
        iteration += 1

        if max_iterations and iteration > max_iterations:
            print(f"\nReached max iterations ({max_iterations})")
            break

        print_session_header(iteration, is_first_run)

        client = create_client(project_dir, model)

        if is_first_run:
            print("\n" + "=" * 70)
            print(" NOTE: Initializer session may take 10-20+ minutes (generating 200 test cases).")
            print("=" * 70 + "\n")
            prompt = get_initializer_prompt()
            is_first_run = False
        else:
            prompt = get_coding_prompt()

        async with client:
            status, response = await run_agent_session(client, prompt, project_dir)

        if status == "continue":
            print(f"\nAgent will auto-continue in {AUTO_CONTINUE_DELAY_SECONDS}s...")
            print_progress_summary(project_dir)
            await asyncio.sleep(AUTO_CONTINUE_DELAY_SECONDS)
        elif status == "error":
            print("\nSession encountered an error. Will retry...")
            await asyncio.sleep(AUTO_CONTINUE_DELAY_SECONDS)

        if max_iterations and iteration >= max_iterations:
            break
        await asyncio.sleep(1)

    print("\n" + "=" * 70)
    print(" SESSION COMPLETE")
    print("=" * 70)
    print_progress_summary(project_dir)
    print(f"\nTo run generated app: cd {project_dir.resolve()} && ./init.sh")
    print("\nDone!")
