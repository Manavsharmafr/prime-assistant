import os
import re
import ast
import difflib
import subprocess
from typing import Dict, Any, List, Optional
from app.core.config import settings

class DeveloperWorkspaceService:
    def __init__(self):
        path = settings.PRIME_WORKSPACE_PATH
        has_files = False
        if os.path.exists(path):
            for _, _, files in os.walk(path):
                if files:
                    has_files = True
                    break
        if not has_files:
            possible_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if os.path.exists(possible_path):
                path = possible_path
            else:
                os.makedirs(path, exist_ok=True)
        self.workspace_path = path

    def index_project(self) -> Dict[str, Any]:
        """Scan workspace recursively and compile symbol metrics (classes, functions, imports)."""
        symbols = []
        file_count = 0
        total_size = 0

        for root, _, files in os.walk(self.workspace_path):
            # Ignore standard dependency/build folders
            if any(p in root for p in [".venv", "node_modules", "dist", "build", ".git", "__pycache__"]):
                continue
            
            for file in files:
                file_count += 1
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.workspace_path)
                try:
                    size = os.path.getsize(full_path)
                    total_size += size

                    # If Python file, execute AST parsing
                    if file.endswith(".py"):
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            node = ast.parse(f.read(), filename=full_path)
                            for child in ast.iter_child_nodes(node):
                                if isinstance(child, ast.ClassDef):
                                    symbols.append({
                                        "name": child.name,
                                        "type": "class",
                                        "file": rel_path,
                                        "line": child.lineno
                                    })
                                elif isinstance(child, ast.FunctionDef):
                                    symbols.append({
                                        "name": child.name,
                                        "type": "function",
                                        "file": rel_path,
                                        "line": child.lineno
                                    })
                except Exception as e:
                    print(f"Failed to parse symbols for {file}: {str(e)}")

        return {
            "status": "success",
            "file_count": file_count,
            "total_size_bytes": total_size,
            "symbols": symbols
        }

    def search_code(self, query: str, match_case: bool = False, use_regex: bool = False) -> List[Dict[str, Any]]:
        """Grep match query across files, returning paths, line numbers, and snippet contents."""
        results = []
        flags = 0 if match_case else re.IGNORECASE

        try:
            pattern = re.compile(query, flags) if use_regex else None
        except Exception as e:
            return [{"error": f"Invalid regex query pattern: {str(e)}", "file": "", "line": 0, "content": ""}]

        for root, _, files in os.walk(self.workspace_path):
            if any(p in root for p in [".venv", "node_modules", "dist", "build", ".git", "__pycache__"]):
                continue

            for file in files:
                # Limit searches to text code formats
                if not any(file.endswith(ext) for ext in [".py", ".ts", ".tsx", ".css", ".html", ".js", ".json", ".md"]):
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.workspace_path)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        for idx, line in enumerate(f, 1):
                            matched = False
                            if use_regex and pattern:
                                if pattern.search(line):
                                    matched = True
                            else:
                                if match_case:
                                    if query in line:
                                        matched = True
                                else:
                                    if query.lower() in line.lower():
                                        matched = True
                            
                            if matched:
                                results.append({
                                    "file": rel_path,
                                    "line": idx,
                                    "content": line.strip()
                                })
                except Exception:
                    pass

        return results[:100] # Cap results at top 100 entries

    def generate_diff(self, file_path: str, new_content: str) -> Dict[str, Any]:
        """Generate a unified diff comparison showing proposed edits."""
        clean_path = os.path.normpath(file_path)
        if not os.path.isabs(clean_path):
            clean_path = os.path.join(self.workspace_path, clean_path)

        if not os.path.exists(clean_path):
            return {"status": "error", "message": f"File not found: {file_path}"}

        try:
            with open(clean_path, "r", encoding="utf-8", errors="ignore") as f:
                old_content = f.read()

            diff = list(difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}"
            ))
            return {
                "status": "success",
                "diff": "".join(diff),
                "has_changes": len(diff) > 0
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_git_status(self) -> Dict[str, Any]:
        """Fetch uncommitted diffs and repository branch information."""
        try:
            # Check if git is active
            if not os.path.exists(os.path.join(self.workspace_path, ".git")):
                return {"status": "inactive", "branch": "none", "changes": []}

            # Get active branch name
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.workspace_path,
                stderr=subprocess.DEVNULL
            ).decode().strip()

            # Get changed files
            status_out = subprocess.check_output(
                ["git", "status", "--porcelain"],
                cwd=self.workspace_path,
                stderr=subprocess.DEVNULL
            ).decode().strip()

            changes = []
            if status_out:
                for line in status_out.splitlines():
                    parts = line.strip().split(maxsplit=1)
                    if len(parts) == 2:
                        changes.append({"state": parts[0], "file": parts[1]})

            return {
                "status": "active",
                "branch": branch,
                "changes": changes
            }
        except Exception:
            return {"status": "error", "branch": "none", "changes": []}

developer_workspace = DeveloperWorkspaceService()
