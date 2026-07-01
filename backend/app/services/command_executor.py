import asyncio
import os
import subprocess
from typing import Callable


class CommandExecutionService:
    async def run_command_async(
        self,
        command: str,
        task_id: str,
        on_log: Callable[[str], None],
        on_finished: Callable[[int, str], None]
    ) -> asyncio.subprocess.Process:
        """Asynchronously executes shell commands, streaming output lines via callback."""
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )

        # Read output stream asynchronously
        async def read_stream():
            accumulated_logs = []
            try:
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    line_str = line.decode('utf-8', errors='replace')
                    accumulated_logs.append(line_str)
                    on_log(line_str)
            except Exception as e:
                err_str = f"\n[Execution Error while reading stream: {str(e)}]\n"
                accumulated_logs.append(err_str)
                on_log(err_str)

            # Wait for exit status
            exit_code = await process.wait()
            on_finished(exit_code, "".join(accumulated_logs))

        # Run stream reader in background task
        asyncio.create_task(read_stream())
        return process

    def cancel_process(self, pid: int) -> bool:
        """Recursively terminate running processes and their children on Windows."""
        try:
            if os.name == 'nt':
                # Use taskkill /F /T /PID on Windows to recursively kill process tree
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )
            else:
                os.kill(pid, 9)
            return True
        except Exception as e:
            print(f"Failed to cancel process {pid}: {str(e)}")
            return False


command_executor = CommandExecutionService()
