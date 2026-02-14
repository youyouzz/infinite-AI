"""
Prompt Loading Utilities
========================

Functions for loading prompt templates from the prompts directory.
Reference: Anthropic - Effective harnesses for long-running agents
"""

import shutil
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(name: str) -> str:
    """Load a prompt template from the prompts directory."""
    prompt_path = PROMPTS_DIR / f"{name}.md"
    return prompt_path.read_text()


def get_requirements_refinement_prompt() -> str:
    """Load the requirements refinement (analyst) prompt."""
    return load_prompt("requirements_refinement_prompt")


def get_initializer_prompt() -> str:
    """Load the initializer agent prompt."""
    return load_prompt("initializer_prompt")


def get_coding_prompt() -> str:
    """Load the coding agent prompt."""
    return load_prompt("coding_prompt")


def copy_spec_to_project(project_dir: Path) -> None:
    """Copy the app spec file into the project directory for the agent to read."""
    spec_source = PROMPTS_DIR / "app_spec.txt"
    spec_dest = project_dir / "app_spec.txt"
    if not spec_dest.exists():
        shutil.copy(spec_source, spec_dest)
        print("Copied app_spec.txt to project directory")


def use_refined_spec_as_app_spec(project_dir: Path) -> bool:
    """
    Copy refined_requirements.md to app_spec.txt so Initializer uses the user-approved spec.
    Returns True if copy was done, False if refined_requirements.md does not exist.
    """
    refined = project_dir / "refined_requirements.md"
    spec_dest = project_dir / "app_spec.txt"
    if not refined.exists():
        return False
    shutil.copy(refined, spec_dest)
    print("Using refined_requirements.md as app_spec.txt for Initializer.")
    return True
