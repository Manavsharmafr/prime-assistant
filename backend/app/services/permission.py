import re
from typing import Tuple, Dict

class PermissionService:
    def __init__(self):
        # Compiled regexes for safety checks
        self.blocked_patterns = [
            re.compile(r'\bformat\b', re.IGNORECASE),
            re.compile(r'\breg\b', re.IGNORECASE), # Block all registry commands
            re.compile(r'\bnet\b\s+user\b', re.IGNORECASE),
            re.compile(r'\bnet\b\s+localgroup\b', re.IGNORECASE),
            re.compile(r'\b(?:useradd|usermod|userdel|groupadd|groupdel|groupmod)\b', re.IGNORECASE),
            re.compile(r'\bsecedit\b', re.IGNORECASE),
            re.compile(r'\bauditpol\b', re.IGNORECASE),
            re.compile(r'\bSet-ExecutionPolicy\b', re.IGNORECASE),
            re.compile(r'\bdiskpart\b', re.IGNORECASE),
            re.compile(r'\bbcdedit\b', re.IGNORECASE),
            re.compile(r'\bbootcfg\b', re.IGNORECASE),
            re.compile(r'\bdel\b\s+/s\b', re.IGNORECASE),
            re.compile(r'\brmdir\b\s+/s\b', re.IGNORECASE),
            re.compile(r'\brm\b\s+-[rf]*[dRf]+\b', re.IGNORECASE),  # rm -rf, rm -r
            re.compile(r'\bmkfs\b', re.IGNORECASE),
            re.compile(r'\bshutdown\b', re.IGNORECASE), # Block all shutdown commands
        ]
        
        self.safe_patterns = [
            re.compile(r'^code(?:\s+.*)?$', re.IGNORECASE),
            re.compile(r'^calc(?:\s+.*)?$', re.IGNORECASE),
            re.compile(r'^(?:dir|ls)(?:\s+.*)?$', re.IGNORECASE),
            re.compile(r'^(?:type|cat)(?:\s+.*)?$', re.IGNORECASE),
            re.compile(r'^echo(?:\s+.*)?$', re.IGNORECASE),
            re.compile(r'^systeminfo(?:\s+.*)?$', re.IGNORECASE),
            re.compile(r'^whoami(?:\s+.*)?$', re.IGNORECASE),
            re.compile(r'^hostname(?:\s+.*)?$', re.IGNORECASE),
            re.compile(r'^pwd(?:\s+.*)?$', re.IGNORECASE),
            re.compile(r'^ping(?:\s+.*)?$', re.IGNORECASE),
        ]

    def check_permission(self, command: str) -> Tuple[str, str]:
        """Classify a given shell command string.
        
        Returns:
            Tuple[str, str]: (risk_level, justification)
            risk_level can be 'safe', 'confirmation_required', or 'blocked'.
        """
        cmd_stripped = command.strip()
        if not cmd_stripped:
            return "safe", "Empty command"

        # 1. Check for blocked patterns
        for pattern in self.blocked_patterns:
            if pattern.search(cmd_stripped):
                return "blocked", f"Command matched blocked safety rule: {pattern.pattern}"

        # 2. Check for safe patterns
        # Note: safe patterns are matched from the start to make sure random arguments or chaining aren't snuck in
        for pattern in self.safe_patterns:
            if pattern.match(cmd_stripped):
                return "safe", f"Command matched auto-exec permission rule: {pattern.pattern}"

        # 3. Default fallback is confirmation required
        return "confirmation_required", "Command execution requires explicit user validation"

    def analyze_command(self, command: str) -> Dict[str, str]:
        """Analyze a command to return its risk level, justification, estimated affected files, and estimated impact."""
        risk_level, justification = self.check_permission(command)
        
        affected_files = "None"
        estimated_impact = "None"
        
        if risk_level == "blocked":
            affected_files = "System resources / Protected files"
            estimated_impact = "High risk security violation (blocked)"
        elif risk_level == "safe":
            affected_files = "Read-only access to query files/directory"
            estimated_impact = "Low risk diagnostic lookup"
        else:
            # confirmation required
            cmd_stripped = command.strip().lower()
            if any(keyword in cmd_stripped for keyword in ["npm install", "pip install", "winget", "choco"]):
                affected_files = "Workspace dependencies configuration / System packages"
                estimated_impact = "Install and verify external dependency packages"
            elif any(keyword in cmd_stripped for keyword in ["git commit", "git push", "git merge", "git pull", "git add", "git checkout"]):
                affected_files = "Git repository local and remote history"
                estimated_impact = "Updates source repository state"
            elif any(keyword in cmd_stripped for keyword in ["del ", "rm ", "ren ", "rename ", "mv ", "move "]):
                # try to extract file arguments if possible
                tokens = command.split()
                files = [t for t in tokens[1:] if not t.startswith("-") and not t.startswith("/")]
                affected_files = ", ".join(files) if files else "Specified files in workspace"
                estimated_impact = "Modify, rename, or delete files in local workspace"
            else:
                affected_files = "Potentially workspace files or shell context"
                estimated_impact = "Shell automation script execution"
                
        return {
            "risk_level": risk_level,
            "justification": justification,
            "affected_files": affected_files,
            "estimated_impact": estimated_impact
        }


permission_service = PermissionService()
