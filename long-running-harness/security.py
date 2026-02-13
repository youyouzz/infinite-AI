"""
Security Hooks for Autonomous Coding Agent
===========================================

Pre-tool-use hooks that validate bash commands for security.
Uses an allowlist approach - only explicitly permitted commands can run.
Reference: Anthropic - Effective harnesses for long-running agents
"""

import re
import shlex


# Allowed commands for development tasks
ALLOWED_COMMANDS = {
    # File inspection
    "ls", "cat", "head", "tail", "wc", "grep",
    # File operations
    "cp", "mkdir", "chmod",
    # Directory
    "pwd",
    # Node.js development
    "npm", "node",
    # Version control
    "git",
    # Process management
    "ps", "lsof", "sleep", "pkill",
    # Script execution
    "init.sh",
}

COMMANDS_NEEDING_EXTRA_VALIDATION = {"pkill", "chmod", "init.sh"}


def split_command_segments(command_string: str) -> list[str]:
    """Split a compound command into individual command segments."""
    segments = re.split(r"\s*(?:&&|\|\|)\s*", command_string)
    result = []
    for segment in segments:
        for sub in re.split(r";", segment):
            s = sub.strip()
            if s:
                result.append(s)
    return result


def extract_commands(command_string: str) -> list[str]:
    """Extract command names from a shell command string."""
    commands = []
    # Split on ; && || and |
    for sep in [r"\s*;\s*", r"\s+&&\s+", r"\s+\|\|\s+", r"\s*\|\s*"]:
        command_string = re.sub(sep, " ", command_string)
    parts = command_string.split()
    for part in parts:
        if part and not part.startswith("-") and "=" not in part:
            cmd = part.split("/")[-1]
            if cmd.endswith(".sh"):
                cmd_to_add = cmd  # Keep init.sh as-is
            else:
                cmd_to_add = cmd.split(".")[0] if "." in cmd else cmd
            if cmd_to_add and cmd_to_add not in commands:
                commands.append(cmd_to_add)
    return commands if commands else ["unknown"]


def validate_pkill_command(command_string: str) -> tuple[bool, str]:
    """Validate pkill commands - only allow killing dev-related processes."""
    allowed_process_names = {"node", "npm", "npx", "vite", "next"}
    try:
        tokens = shlex.split(command_string)
    except ValueError:
        return False, "Could not parse pkill command"

    if not tokens:
        return False, "Empty pkill command"

    args = [t for t in tokens[1:] if not t.startswith("-")]
    if not args:
        return False, "pkill requires a process name"

    target = args[-1]
    if " " in target:
        target = target.split()[0]

    if target in allowed_process_names:
        return True, ""
    return False, f"pkill only allowed for dev processes: {allowed_process_names}"


def validate_chmod_command(command_string: str) -> tuple[bool, str]:
    """Validate chmod commands - only allow making files executable with +x."""
    try:
        tokens = shlex.split(command_string)
    except ValueError:
        return False, "Could not parse chmod command"

    if not tokens or tokens[0] != "chmod":
        return False, "Not a chmod command"

    mode = None
    files = []
    for token in tokens[1:]:
        if token.startswith("-"):
            return False, "chmod flags are not allowed"
        elif mode is None:
            mode = token
        else:
            files.append(token)

    if mode is None:
        return False, "chmod requires a mode"
    if not files:
        return False, "chmod requires at least one file"

    if not re.match(r"^[ugoa]*\+x$", mode):
        return False, f"chmod only allowed with +x mode, got: {mode}"

    return True, ""


def validate_init_script(command_string: str) -> tuple[bool, str]:
    """Validate init.sh script execution - only allow ./init.sh."""
    try:
        tokens = shlex.split(command_string)
    except ValueError:
        return False, "Could not parse init script command"

    if not tokens:
        return False, "Empty command"

    script = tokens[0]
    if script == "./init.sh" or script.endswith("/init.sh"):
        return True, ""
    return False, f"Only ./init.sh is allowed, got: {script}"


def get_command_for_validation(cmd: str, segments: list[str]) -> str:
    """Find the specific command segment that contains the given command."""
    for segment in segments:
        segment_commands = extract_commands(segment)
        if cmd in segment_commands:
            return segment
    return ""


async def bash_security_hook(input_data, tool_use_id=None, context=None):
    """
    Pre-tool-use hook that validates bash commands using an allowlist.
    Returns empty dict to allow, or {"decision": "block", "reason": "..."} to block.
    """
    if input_data.get("tool_name") != "Bash":
        return {}

    command = input_data.get("tool_input", {}).get("command", "")
    if not command:
        return {}

    commands = extract_commands(command)
    if not commands:
        return {
            "decision": "block",
            "reason": f"Could not parse command for security validation: {command}",
        }

    segments = split_command_segments(command)

    for cmd in commands:
        if cmd not in ALLOWED_COMMANDS:
            return {
                "decision": "block",
                "reason": f"Command '{cmd}' is not in the allowed commands list",
            }

        if cmd in COMMANDS_NEEDING_EXTRA_VALIDATION:
            cmd_segment = get_command_for_validation(cmd, segments) or command

            if cmd == "pkill":
                allowed, reason = validate_pkill_command(cmd_segment)
            elif cmd == "chmod":
                allowed, reason = validate_chmod_command(cmd_segment)
            elif cmd == "init.sh":
                allowed, reason = validate_init_script(cmd_segment)
            else:
                allowed, reason = True, ""

            if not allowed:
                return {"decision": "block", "reason": reason}

    return {}
