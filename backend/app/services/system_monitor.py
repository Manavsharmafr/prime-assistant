import psutil
import time
import os
import platform
import subprocess
from typing import Dict, Any, List, Set
from fastapi import WebSocket
from datetime import datetime

class SystemMonitorService:
    def __init__(self):
        self.start_time = psutil.boot_time()
        # Keep track of previous net IO for rate calculation
        self._prev_net_io = psutil.net_io_counters()
        self._prev_net_time = time.time()

    def get_system_uptime(self) -> float:
        """Return system uptime in seconds."""
        return time.time() - self.start_time

    def get_cpu_temp(self) -> str:
        """Fetch CPU temperature when available. On Windows, uses WMI fallback."""
        if platform.system() == "Windows":
            try:
                # WMI query for thermal zone temperature (requires admin privileges sometimes, fallback if fails)
                cmd = "powershell -Command \"(Get-CimInstance -Namespace root/wmi -ClassName MsAcpi_ThermalZoneTemperature).CurrentTemperature\""
                proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, _ = proc.communicate(timeout=2)
                if proc.returncode == 0 and stdout.strip():
                    # Kelvin decikelvins to Celsius: (temp / 10) - 273.15
                    raw_temp = float(stdout.strip())
                    celsius = (raw_temp / 10.0) - 273.15
                    return f"{round(celsius, 1)}°C"
            except Exception:
                pass
        else:
            try:
                temps = psutil.sensors_temperatures()
                if "coretemp" in temps:
                    return f"{temps['coretemp'][0].current}°C"
            except Exception:
                pass
        return "N/A"

    def get_gpu_info(self) -> str:
        """Get active GPU device descriptions on Windows using WMI."""
        if platform.system() == "Windows":
            try:
                cmd = "powershell -Command \"(Get-CimInstance Win32_VideoController).Name\""
                proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, _ = proc.communicate(timeout=2)
                if proc.returncode == 0 and stdout.strip():
                    return stdout.strip().replace("\n", ", ")
            except Exception:
                pass
        return "Intel / AMD Integrated Graphics (Auto)"

    def get_network_rates(self) -> Dict[str, float]:
        """Calculate current upload/download rates in KB/s."""
        curr_net_io = psutil.net_io_counters()
        curr_time = time.time()
        
        time_delta = curr_time - self._prev_net_time
        if time_delta <= 0:
            time_delta = 1.0

        bytes_sent_diff = curr_net_io.bytes_sent - self._prev_net_io.bytes_sent
        bytes_recv_diff = curr_net_io.bytes_recv - self._prev_net_io.bytes_recv

        # Update tracking values
        self._prev_net_io = curr_net_io
        self._prev_net_time = curr_time

        # Convert to KB/s
        return {
            "upload_kb_s": round((bytes_sent_diff / 1024.0) / time_delta, 2),
            "download_kb_s": round((bytes_recv_diff / 1024.0) / time_delta, 2)
        }

    def get_running_processes(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve list of top running processes sorted by CPU usage."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                # cpu_percent can be None initially
                cpu = proc.info['cpu_percent'] or 0.0
                mem = proc.info['memory_percent'] or 0.0
                processes.append({
                    "pid": proc.info['pid'],
                    "name": proc.info['name'],
                    "cpu_percent": round(cpu, 1),
                    "memory_percent": round(mem, 1)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort by CPU usage descending
        processes.sort(key=lambda x: x["cpu_percent"], reverse=True)
        return processes[:limit]

    def get_system_status_payload(self) -> Dict[str, Any]:
        """Consolidate all telemetry statistics into a single data payload."""
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net_rates = self.get_network_rates()
        battery = psutil.sensors_battery()
        
        battery_data = None
        if battery:
            battery_data = {
                "percent": battery.percent,
                "power_plugged": battery.power_plugged,
                "secs_left": battery.secsleft
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "cores": psutil.cpu_count(logical=True),
                "temp": self.get_cpu_temp()
            },
            "memory": {
                "percent": memory.percent,
                "used_gb": round(memory.used / (1024 ** 3), 2),
                "total_gb": round(memory.total / (1024 ** 3), 2)
            },
            "disk": {
                "percent": disk.percent,
                "used_gb": round(disk.used / (1024 ** 3), 2),
                "total_gb": round(disk.total / (1024 ** 3), 2)
            },
            "network": net_rates,
            "gpu": self.get_gpu_info(),
            "battery": battery_data,
            "uptime_seconds": round(self.get_system_uptime(), 2),
            "top_processes": self.get_running_processes(limit=5)
        }


# --- WebSocket Broadcast Manager ---
class SystemMonitorWebSocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        disconnected_sockets = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected_sockets.add(connection)
                
        # Clean up stale sockets
        for conn in disconnected_sockets:
            self.disconnect(conn)


system_monitor = SystemMonitorService()
stats_ws_manager = SystemMonitorWebSocketManager()
