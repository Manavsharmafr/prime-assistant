import subprocess
import uuid
import os
import shlex
from typing import Dict, Optional, Tuple


class CommandRunnerService:
    def __init__(self):
        # Maps challenge_id to command details
        self.challenges: Dict[str, Dict[str, str]] = {}

    def register_challenge(self, command: str, description: str) -> str:
        """Register a command execution challenge and return its unique ID."""
        challenge_id = str(uuid.uuid4())
        self.challenges[challenge_id] = {
            "command": command,
            "description": description
        }
        return challenge_id

    def get_challenge(self, challenge_id: str) -> Optional[Dict[str, str]]:
        """Retrieve registered challenge details."""
        return self.challenges.get(challenge_id)

    def remove_challenge(self, challenge_id: str):
        """Remove a challenge once processed."""
        if challenge_id in self.challenges:
            del self.challenges[challenge_id]

    def execute_command_raw(self, command: str) -> Tuple[int, str, str]:
        """Directly run a system shell command safely, returning code, stdout, and stderr."""
        try:
            # On Windows, we run via powershell or cmd
            # We want to run with shell=True because Windows uses built-in shell commands (like dir, start)
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=os.environ.copy()
            )
            stdout, stderr = process.communicate(timeout=30)
            return process.returncode, stdout, stderr
        except subprocess.TimeoutExpired as e:
            return -1, "", f"Operation timed out: {str(e)}"
        except Exception as e:
            return -1, "", f"Execution failure: {str(e)}"

    def execute_approved_challenge(self, challenge_id: str) -> Tuple[int, str, str]:
        """Execute a challenge command that has been approved."""
        challenge = self.get_challenge(challenge_id)
        if not challenge:
            return -1, "", "Challenge not found or expired."

        command = challenge["command"]
        self.remove_challenge(challenge_id)
        return self.execute_command_raw(command)


command_runner = CommandRunnerService()
