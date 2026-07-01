import { useState, useEffect, useRef } from 'react';
import type { FormEvent } from 'react';
import { 
  Activity, ShieldAlert, ShieldCheck, Play, Square, 
  RefreshCw, Terminal, Check, X, AlertTriangle, 
  Cpu, HardDrive, Network, Battery, Clock, FileText, Ban
} from 'lucide-react';

interface StatsPayload {
  timestamp: string;
  cpu: { percent: number; cores: number; temp: string };
  memory: { percent: number; used_gb: number; total_gb: number };
  disk: { percent: number; used_gb: number; total_gb: number };
  network: { upload_kb_s: number; download_kb_s: number };
  gpu: string;
  battery: { percent: number; power_plugged: boolean; secs_left: number } | null;
  uptime_seconds: number;
  top_processes: Array<{ pid: number; name: string; cpu_percent: number; memory_percent: number }>;
}

interface ApprovalRequest {
  id: string;
  command: string;
  description: string;
  risk_level: string;
  status: string;
  affected_files?: string;
  estimated_impact?: string;
  created_at: string;
}

interface TaskRecord {
  id: string;
  command: string;
  status: string;
  log_content: string;
  exit_code: number | null;
  start_time: string;
  finish_time: string | null;
}

interface AuditLog {
  id: string;
  timestamp: string;
  user_request: string;
  generated_command: string;
  approval_result: string;
  execution_duration: number | null;
  exit_code: number | null;
  error_message: string | null;
}

export default function SystemControlCenter() {
  const [activeSubTab, setActiveSubTab] = useState<'monitor' | 'approvals' | 'tasks' | 'audit'>('monitor');
  const [stats, setStats] = useState<StatsPayload | null>(null);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  
  // Terminal log stream dictionary (task_id -> accumulated string)
  const [liveLogs, setLiveLogs] = useState<Record<string, string>>({});
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  
  // Custom shell inputs
  const [cmdInput, setCmdInput] = useState('');
  const [userRequestDesc, setUserRequestDesc] = useState('');
  const [execResult, setExecResult] = useState<{ status: string; message: string; task_id?: string; request_id?: string } | null>(null);
  
  const statsWsRef = useRef<WebSocket | null>(null);
  const tasksWsRef = useRef<WebSocket | null>(null);

  // Fetch initial REST data
  const fetchApprovals = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/automation/approvals');
      if (res.ok) setApprovals(await res.json());
    } catch (e) { console.error("Error fetching approvals:", e); }
  };

  const fetchTasks = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/automation/tasks');
      if (res.ok) setTasks(await res.json());
    } catch (e) { console.error("Error fetching tasks:", e); }
  };

  const fetchAuditLogs = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/automation/audit');
      if (res.ok) setAuditLogs(await res.json());
    } catch (e) { console.error("Error fetching audit logs:", e); }
  };

  useEffect(() => {
    fetchApprovals();
    fetchTasks();
    fetchAuditLogs();

    // 1. Establish System Stats WebSocket
    const statsWs = new WebSocket('ws://127.0.0.1:8000/api/ws/stats');
    statsWsRef.current = statsWs;
    statsWs.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setStats(payload);
      } catch (err) { console.error("Error parsing stats frame:", err); }
    };

    // 2. Establish Tasks/Logs WebSocket
    const tasksWs = new WebSocket('ws://127.0.0.1:8000/api/ws/tasks');
    tasksWsRef.current = tasksWs;
    tasksWs.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        
        if (message.type === 'log') {
          setLiveLogs(prev => ({
            ...prev,
            [message.task_id]: (prev[message.task_id] || '') + message.data
          }));
        } else if (message.type === 'status' || message.type === 'started') {
          // Refresh list to catch new exit codes / finish times
          fetchTasks();
          fetchAuditLogs();
        } else if (message.type === 'approval_queued') {
          fetchApprovals();
        }
      } catch (err) { console.error("Error parsing task log frame:", err); }
    };

    return () => {
      if (statsWsRef.current) statsWsRef.current.close();
      if (tasksWsRef.current) tasksWsRef.current.close();
    };
  }, []);

  // Action an approval request
  const handleApprovalAction = async (id: string, action: 'approve' | 'reject') => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/automation/approvals/${id}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action })
      });
      if (res.ok) {
        fetchApprovals();
        fetchTasks();
        fetchAuditLogs();
      }
    } catch (e) { console.error("Error executing approval action:", e); }
  };

  // Cancel a running task
  const handleCancelTask = async (id: string) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/automation/tasks/${id}/cancel`, { method: 'POST' });
      if (res.ok) {
        fetchTasks();
      }
    } catch (e) { console.error("Error cancelling task:", e); }
  };

  // Run a custom manual command
  const handleRunCommand = async (e: FormEvent) => {
    e.preventDefault();
    if (!cmdInput.trim()) return;
    setExecResult(null);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/automation/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command: cmdInput,
          user_request: userRequestDesc || "Manual Command Terminal"
        })
      });
      const data = await res.json();
      setExecResult(data);
      if (data.status === 'running') {
        setSelectedTaskId(data.task_id);
        setActiveSubTab('tasks');
      } else if (data.status === 'pending_approval') {
        setActiveSubTab('approvals');
      }
      setCmdInput('');
      setUserRequestDesc('');
      fetchApprovals();
      fetchTasks();
    } catch (e) {
      console.error("Error executing custom command:", e);
      setExecResult({ status: 'failed', message: 'Failed to communicate with backend execution service.' });
    }
  };

  // Formatter for uptime
  const formatUptime = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hrs}h ${mins}m ${secs}s`;
  };

  return (
    <div className="flex flex-col h-full bg-slate-950/40 border border-slate-800/80 rounded-2xl overflow-hidden backdrop-blur-xl">
      {/* Sub Tabs Navigation */}
      <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4 bg-slate-950/60">
        <div className="flex items-center gap-2">
          <Activity className="text-prime-cyan animate-pulse" size={18} />
          <span className="text-sm font-mono font-bold tracking-widest text-white">SYSTEM CONTROLS</span>
        </div>
        <div className="flex items-center gap-1 bg-slate-900/60 p-1 rounded-xl border border-slate-800/40">
          {(['monitor', 'approvals', 'tasks', 'audit'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveSubTab(tab)}
              className={`px-3.5 py-1.5 rounded-lg font-mono text-[10px] font-bold uppercase tracking-wider transition-all ${
                activeSubTab === tab
                  ? 'bg-prime-cyan/15 text-prime-cyan border border-prime-cyan/30 shadow-[0_0_8px_rgba(0,240,255,0.06)]'
                  : 'text-slate-400 hover:text-white border border-transparent'
              }`}
            >
              {tab === 'monitor' ? 'Live Telemetry' : tab === 'approvals' ? `Safety Queue (${approvals.length})` : tab === 'tasks' ? 'Active Tasks' : 'Audit Logs'}
            </button>
          ))}
        </div>
      </div>

      {/* Main panel body */}
      <div className="flex-1 p-6 overflow-y-auto min-h-0">
        
        {/* VIEW 1: Live telemetry dashboard */}
        {activeSubTab === 'monitor' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-full">
            {/* Stats gauges */}
            <div className="lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-4">
              
              {/* CPU Status */}
              <div className="glass-panel p-5 border border-slate-800/60 rounded-2xl flex flex-col gap-4">
                <div className="flex items-center justify-between border-b border-slate-900 pb-2">
                  <div className="flex items-center gap-2 text-xs font-mono text-slate-300">
                    <Cpu size={14} className="text-prime-cyan" />
                    <span>CPU LOAD</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500">TEMP: {stats?.cpu.temp || 'N/A'}</span>
                </div>
                <div className="flex items-end justify-between">
                  <span className="text-3xl font-mono font-black text-white">{stats?.cpu.percent || 0}%</span>
                  <span className="text-[10px] font-mono text-slate-400">{stats?.cpu.cores} THREADS</span>
                </div>
                <div className="w-full bg-slate-900 h-2.5 rounded-full overflow-hidden border border-slate-800">
                  <div 
                    className="bg-gradient-to-r from-prime-cyan to-blue-500 h-full rounded-full transition-all duration-300"
                    style={{ width: `${stats?.cpu.percent || 0}%` }}
                  />
                </div>
              </div>

              {/* Memory status */}
              <div className="glass-panel p-5 border border-slate-800/60 rounded-2xl flex flex-col gap-4">
                <div className="flex items-center justify-between border-b border-slate-900 pb-2">
                  <div className="flex items-center gap-2 text-xs font-mono text-slate-300">
                    <HardDrive size={14} className="text-prime-purple" />
                    <span>RAM STABILITY</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500">
                    {stats?.memory.used_gb || 0} / {stats?.memory.total_gb || 0} GB
                  </span>
                </div>
                <div className="flex items-end justify-between">
                  <span className="text-3xl font-mono font-black text-white">{stats?.memory.percent || 0}%</span>
                  <span className="text-[10px] font-mono text-slate-400">MEM USED</span>
                </div>
                <div className="w-full bg-slate-900 h-2.5 rounded-full overflow-hidden border border-slate-800">
                  <div 
                    className="bg-gradient-to-r from-prime-purple to-pink-500 h-full rounded-full transition-all duration-300"
                    style={{ width: `${stats?.memory.percent || 0}%` }}
                  />
                </div>
              </div>

              {/* Disk usage */}
              <div className="glass-panel p-5 border border-slate-800/60 rounded-2xl flex flex-col gap-4">
                <div className="flex items-center justify-between border-b border-slate-900 pb-2">
                  <div className="flex items-center gap-2 text-xs font-mono text-slate-300">
                    <HardDrive size={14} className="text-slate-400" />
                    <span>DISK DIRECTORY (/)</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500">
                    {stats?.disk.used_gb || 0} / {stats?.disk.total_gb || 0} GB
                  </span>
                </div>
                <div className="flex items-end justify-between">
                  <span className="text-2xl font-mono font-bold text-white">{stats?.disk.percent || 0}%</span>
                  <span className="text-[10px] font-mono text-slate-400">CAPACITY</span>
                </div>
                <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-slate-800">
                  <div 
                    className="bg-slate-500 h-full rounded-full transition-all duration-300"
                    style={{ width: `${stats?.disk.percent || 0}%` }}
                  />
                </div>
              </div>

              {/* Network upload/download */}
              <div className="glass-panel p-5 border border-slate-800/60 rounded-2xl flex flex-col gap-4">
                <div className="flex items-center justify-between border-b border-slate-900 pb-2">
                  <div className="flex items-center gap-2 text-xs font-mono text-slate-300">
                    <Network size={14} className="text-emerald-400" />
                    <span>NETWORK TRAFFIC</span>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex flex-col">
                    <span className="text-[10px] font-mono text-slate-500">DOWNLOAD</span>
                    <span className="text-lg font-mono font-bold text-white">{stats?.network.download_kb_s || 0} KB/s</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] font-mono text-slate-500">UPLOAD</span>
                    <span className="text-lg font-mono font-bold text-white">{stats?.network.upload_kb_s || 0} KB/s</span>
                  </div>
                </div>
              </div>

              {/* Telemetries bottom banner */}
              <div className="glass-panel p-5 border border-slate-800/60 rounded-2xl md:col-span-2 flex flex-col gap-2 font-mono text-xs text-slate-400">
                <div className="flex items-center gap-2 text-white pb-2 border-b border-slate-900">
                  <Clock size={14} className="text-amber-400" />
                  <span>SYSTEM METRICS</span>
                </div>
                <div className="grid grid-cols-2 gap-4 pt-1">
                  <div>GPU Controller: <span className="text-white font-bold">{stats?.gpu || 'N/A'}</span></div>
                  <div>Uptime: <span className="text-white font-bold">{stats ? formatUptime(stats.uptime_seconds) : '0s'}</span></div>
                  {stats?.battery && (
                    <div className="col-span-2 flex items-center gap-2">
                      <Battery size={14} className="text-emerald-400" />
                      <span>Battery status: {stats.battery.percent}% {stats.battery.power_plugged ? '(Charging)' : '(On Battery)'}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Top processes */}
            <div className="lg:col-span-4 flex flex-col gap-4">
              <div className="glass-panel p-5 border border-slate-800/60 rounded-2xl flex-1 flex flex-col min-h-0">
                <div className="text-xs font-mono font-bold tracking-wider text-slate-300 border-b border-slate-900 pb-2 flex items-center gap-2">
                  <Activity size={14} className="text-prime-cyan" />
                  <span>PROCESS RESOURCES</span>
                </div>
                <div className="flex-1 overflow-y-auto mt-4 flex flex-col gap-3 min-h-0">
                  {stats?.top_processes.map((proc, idx) => (
                    <div key={idx} className="flex flex-col gap-1 border-b border-slate-900/30 pb-2">
                      <div className="flex items-center justify-between text-xs font-mono">
                        <span className="text-slate-300 truncate max-w-[150px]">{proc.name}</span>
                        <span className="text-slate-500 text-[10px]">PID {proc.pid}</span>
                      </div>
                      <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400 justify-between">
                        <span className="flex items-center gap-1">
                          <Cpu size={10} className="text-prime-cyan" />
                          CPU: {proc.cpu_percent}%
                        </span>
                        <span className="flex items-center gap-1">
                          <HardDrive size={10} className="text-prime-purple" />
                          RAM: {proc.memory_percent}%
                        </span>
                      </div>
                    </div>
                  ))}
                  {(!stats || stats.top_processes.length === 0) && (
                    <div className="text-center text-slate-500 font-mono text-xs mt-10">No processes monitored</div>
                  )}
                </div>
              </div>
            </div>

            {/* Command Trigger Terminal Panel */}
            <div className="lg:col-span-12 glass-panel p-5 border border-slate-800/60 rounded-2xl flex flex-col gap-4">
              <div className="text-xs font-mono font-bold tracking-wider text-slate-300 border-b border-slate-900 pb-2 flex items-center gap-2">
                <Terminal size={14} className="text-prime-cyan" />
                <span>COMMAND CONTROLLER SAFETY PASS</span>
              </div>
              
              <form onSubmit={handleRunCommand} className="flex flex-col md:flex-row gap-4 items-end">
                <div className="flex-1 flex flex-col gap-1.5 w-full">
                  <label className="text-[10px] font-mono text-slate-400">GENERATE OPERATING COMMAND</label>
                  <input
                    type="text"
                    value={cmdInput}
                    onChange={(e) => setCmdInput(e.target.value)}
                    placeholder="e.g. ping google.com, whoami, code"
                    className="bg-slate-950/60 border border-slate-800 rounded-xl px-4 py-2 text-xs font-mono text-white placeholder-slate-600 focus:outline-none focus:border-prime-cyan"
                  />
                </div>
                <div className="flex-1 flex flex-col gap-1.5 w-full">
                  <label className="text-[10px] font-mono text-slate-400">OPERATION GOAL / DESCRIPTION</label>
                  <input
                    type="text"
                    value={userRequestDesc}
                    onChange={(e) => setUserRequestDesc(e.target.value)}
                    placeholder="e.g. Check connections, Open workspace editor"
                    className="bg-slate-950/60 border border-slate-800 rounded-xl px-4 py-2 text-xs font-mono text-white placeholder-slate-600 focus:outline-none focus:border-prime-cyan"
                  />
                </div>
                <button
                  type="submit"
                  className="bg-prime-cyan/10 border border-prime-cyan/40 hover:bg-prime-cyan/20 text-prime-cyan font-mono font-bold text-xs px-6 py-2.5 rounded-xl transition-all flex items-center gap-2 h-[38px] justify-center w-full md:w-auto"
                >
                  <Play size={12} />
                  EXECUTE
                </button>
              </form>

              {execResult && (
                <div className={`p-4 rounded-xl border font-mono text-xs flex items-center gap-3 ${
                  execResult.status === 'blocked'
                    ? 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                    : execResult.status === 'pending_approval'
                    ? 'bg-amber-500/10 border-amber-500/20 text-amber-400 animate-pulse'
                    : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                }`}>
                  {execResult.status === 'blocked' ? (
                    <Ban size={16} />
                  ) : execResult.status === 'pending_approval' ? (
                    <AlertTriangle size={16} />
                  ) : (
                    <Check size={16} />
                  )}
                  <div className="flex-1">
                    <div className="font-bold uppercase tracking-wider">{execResult.status}</div>
                    <div>{execResult.message}</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* VIEW 2: Pending Approvals Safety Queue */}
        {activeSubTab === 'approvals' && (
          <div className="flex flex-col gap-4 h-full">
            <div className="border border-amber-500/20 bg-amber-500/5 p-4 rounded-xl flex items-center gap-3 text-amber-400 font-mono text-xs">
              <ShieldAlert size={18} />
              <div>
                <strong>SAFETY GATES ACTIVE:</strong> Commands targeting file structures, git operations or running script executables are hold-queued until approved. Blocked commands are rejected instantly.
              </div>
            </div>

            <div className="flex flex-col gap-4 overflow-y-auto flex-1 mt-2">
              {approvals.map((req) => (
                <div key={req.id} className="glass-panel p-5 border border-slate-800 rounded-2xl flex flex-col gap-4 bg-slate-900/10">
                  <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-slate-900 pb-2 text-xs font-mono text-slate-500 gap-2">
                    <span className="text-[10px] text-amber-400 bg-amber-400/5 border border-amber-400/25 px-2 py-0.5 rounded">
                      RISK: {req.risk_level.toUpperCase()}
                    </span>
                    <span>ID: {req.id}</span>
                    <span>Queued: {new Date(req.created_at).toLocaleString()}</span>
                  </div>
                  <div>
                    <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Goal Context</div>
                    <div className="text-sm text-slate-200 mt-1 font-sans">{req.description || 'N/A'}</div>
                  </div>
                  {req.affected_files && req.affected_files !== 'None' && (
                    <div>
                      <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Affected Resources</div>
                      <div className="text-xs text-slate-300 mt-1 font-mono">{req.affected_files}</div>
                    </div>
                  )}
                  {req.estimated_impact && req.estimated_impact !== 'None' && (
                    <div>
                      <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Estimated Impact</div>
                      <div className="text-xs text-amber-400/90 mt-1 font-sans">{req.estimated_impact}</div>
                    </div>
                  )}
                  <div className="bg-black/40 border border-slate-850 p-3.5 rounded-xl font-mono text-xs text-slate-300 select-all overflow-x-auto whitespace-pre">
                    {req.command}
                  </div>
                  <div className="flex items-center gap-3 justify-end">
                    <button
                      onClick={() => handleApprovalAction(req.id, 'reject')}
                      className="border border-slate-800 hover:bg-slate-900 text-slate-400 font-mono font-bold text-xs px-4 py-2 rounded-xl transition-all flex items-center gap-1.5"
                    >
                      <X size={12} />
                      REJECT COMMAND
                    </button>
                    <button
                      onClick={() => handleApprovalAction(req.id, 'approve')}
                      className="bg-amber-500/10 border border-amber-500/40 hover:bg-amber-500/20 text-amber-400 font-mono font-bold text-xs px-5 py-2 rounded-xl transition-all flex items-center gap-1.5"
                    >
                      <Check size={12} />
                      APPROVE & EXECUTE
                    </button>
                  </div>
                </div>
              ))}
              {approvals.length === 0 && (
                <div className="text-center font-mono text-xs text-slate-500 py-20 flex flex-col items-center gap-3">
                  <ShieldCheck size={32} className="text-emerald-400/60" />
                  <span>No command verification requests pending in the safety gate.</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* VIEW 3: Active Tasks and Live Log Stream */}
        {activeSubTab === 'tasks' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-full min-h-0">
            {/* Task list list (4 cols) */}
            <div className="lg:col-span-4 flex flex-col gap-4 min-h-0">
              <div className="glass-panel p-4 border border-slate-800 flex-1 flex flex-col min-h-0 rounded-2xl bg-slate-900/10">
                <div className="text-xs font-mono font-bold tracking-wider text-slate-300 border-b border-slate-900 pb-2 uppercase">
                  Active Executions
                </div>
                <div className="flex-1 overflow-y-auto mt-4 flex flex-col gap-2 min-h-0">
                  {tasks.map((task) => (
                    <button
                      key={task.id}
                      onClick={() => setSelectedTaskId(task.id)}
                      className={`p-3 rounded-xl border text-left font-mono transition-all flex flex-col gap-1.5 ${
                        selectedTaskId === task.id
                          ? 'bg-prime-cyan/5 border-prime-cyan/35 text-white'
                          : 'bg-slate-950/20 border-slate-900 hover:border-slate-800 text-slate-400'
                      }`}
                    >
                      <div className="flex items-center justify-between text-[10px]">
                        <span className={`px-1.5 py-0.5 rounded font-bold uppercase ${
                          task.status === 'running' 
                            ? 'text-prime-cyan bg-prime-cyan/10'
                            : task.status === 'completed'
                            ? 'text-emerald-400 bg-emerald-400/10'
                            : task.status === 'cancelled'
                            ? 'text-slate-400 bg-slate-800'
                            : 'text-rose-400 bg-rose-500/10'
                        }`}>
                          {task.status}
                        </span>
                        <span>{new Date(task.start_time).toLocaleTimeString()}</span>
                      </div>
                      <div className="text-xs font-bold truncate">{task.command}</div>
                      
                      {task.status === 'running' && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCancelTask(task.id);
                          }}
                          className="mt-1 flex items-center justify-center gap-1.5 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 text-[9px] font-bold"
                        >
                          <Square size={8} />
                          KILL PROCESS
                        </button>
                      )}
                    </button>
                  ))}
                  {tasks.length === 0 && (
                    <div className="text-center text-slate-500 font-mono text-[10px] mt-10">No tasks run yet</div>
                  )}
                </div>
              </div>
            </div>

            {/* Terminal log panel (8 cols) */}
            <div className="lg:col-span-8 flex flex-col min-h-0">
              <div className="glass-panel p-5 border border-slate-800 flex-1 flex flex-col rounded-2xl bg-black/30 min-h-0">
                <div className="flex items-center justify-between border-b border-slate-900 pb-2">
                  <span className="text-xs font-mono font-bold tracking-wider text-slate-300 uppercase flex items-center gap-2">
                    <Terminal size={14} className="text-prime-cyan" />
                    Console Output Log
                  </span>
                  {selectedTaskId && (
                    <span className="text-[10px] font-mono text-slate-500 truncate max-w-[200px]">
                      Task ID: {selectedTaskId}
                    </span>
                  )}
                </div>

                <div className="flex-1 bg-black/60 border border-slate-900 rounded-xl p-4 mt-4 font-mono text-xs text-slate-300 overflow-y-auto select-text whitespace-pre-wrap select-all min-h-0">
                  {selectedTaskId ? (
                    // Display either streamed logs or recorded log content
                    liveLogs[selectedTaskId] || 
                    tasks.find(t => t.id === selectedTaskId)?.log_content ||
                    "[Initializing stream console connection... waiting for stdout buffers]"
                  ) : (
                    <div className="flex flex-col items-center justify-center text-slate-600 h-full gap-2">
                      <FileText size={24} />
                      <span>Select a task from the list to display console records.</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* VIEW 4: Execution Audit Logs */}
        {activeSubTab === 'audit' && (
          <div className="flex flex-col h-full min-h-0">
            <div className="flex items-center justify-between border-b border-slate-900 pb-2 mb-4">
              <div className="text-xs font-mono font-bold tracking-wider text-slate-300 uppercase">
                Historical Audit Trail
              </div>
              <button 
                onClick={fetchAuditLogs}
                className="text-slate-400 hover:text-white flex items-center gap-1.5 font-mono text-[10px]"
              >
                <RefreshCw size={10} />
                REFRESH
              </button>
            </div>

            <div className="flex-1 overflow-y-auto flex flex-col gap-3 min-h-0 pr-1">
              {auditLogs.map((log) => (
                <div key={log.id} className="border border-slate-900/60 p-4 rounded-xl bg-slate-950/20 font-mono text-xs flex flex-col gap-2">
                  <div className="flex flex-wrap items-center justify-between text-[10px] text-slate-500 gap-2 border-b border-slate-950 pb-1.5">
                    <span>Timestamp: {new Date(log.timestamp).toLocaleString()}</span>
                    <span className={`px-1.5 py-0.5 rounded font-bold uppercase ${
                      log.approval_result === 'blocked_automatically'
                        ? 'text-rose-400 bg-rose-500/10'
                        : log.approval_result === 'rejected'
                        ? 'text-slate-400 bg-slate-800'
                        : 'text-emerald-400 bg-emerald-400/10'
                    }`}>
                      {log.approval_result.replace('_', ' ')}
                    </span>
                    {log.execution_duration !== null && (
                      <span>Runtime: {log.execution_duration}s</span>
                    )}
                    {log.exit_code !== null && (
                      <span>Exit Code: {log.exit_code}</span>
                    )}
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-3 pt-1">
                    <div className="md:col-span-4">
                      <span className="text-[9px] text-slate-500 uppercase font-black">User Request context</span>
                      <div className="text-slate-300 mt-0.5">{log.user_request}</div>
                    </div>
                    <div className="md:col-span-8 flex flex-col gap-1">
                      <span className="text-[9px] text-slate-500 uppercase font-black">CLI script</span>
                      <div className="bg-black/30 p-2 rounded border border-slate-900/50 text-[11px] text-slate-400 overflow-x-auto whitespace-pre">
                        {log.generated_command}
                      </div>
                    </div>
                  </div>
                  {log.error_message && (
                    <div className="text-[10px] text-rose-400 mt-1.5 p-2 rounded bg-rose-500/5 border border-rose-500/10">
                      Error details: {log.error_message}
                    </div>
                  )}
                </div>
              ))}
              {auditLogs.length === 0 && (
                <div className="text-center text-slate-500 font-mono text-xs py-20">
                  No execution audit logs found.
                </div>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
