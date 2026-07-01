import { useState, useEffect } from 'react';
import { 
  Play, 
  Pause, 
  XOctagon, 
  Plus, 
  Trash2, 
  GitMerge, 
  RefreshCw, 
  Calendar, 
  Bot
} from 'lucide-react';

const API_BASE_URL = 'http://127.0.0.1:8000';

interface Workflow {
  id: string;
  name: string;
  status: string;
  current_step: number;
  steps: string; // JSON string array
  schedule_cron: string | null;
  next_run_at: string | null;
  created_at: string;
}

export const WorkflowDashboard = () => {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(false);

  // Builder state
  const [workflowName, setWorkflowName] = useState('');
  const [steps, setSteps] = useState<string[]>(['echo Starting Workflow', 'dir']);
  const [cronExpression, setCronExpression] = useState('');

  const fetchWorkflows = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE_URL}/api/workflows`);
      if (resp.ok) {
        const data = await resp.json();
        setWorkflows(data || []);
      }
    } catch (err) {
      console.error('Failed to list workflows:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateWorkflow = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workflowName.trim()) return;
    try {
      const resp = await fetch(`${API_BASE_URL}/api/workflows/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: workflowName,
          steps: steps.filter(s => s.trim() !== ''),
          schedule_cron: cronExpression || null
        })
      });
      if (resp.ok) {
        setWorkflowName('');
        setSteps(['echo Starting Workflow', 'dir']);
        setCronExpression('');
        fetchWorkflows();
      }
    } catch (err) {
      console.error('Failed to instantiate workflow:', err);
    }
  };

  const handlePause = async (id: string) => {
    await fetch(`${API_BASE_URL}/api/workflows/${id}/pause`, { method: 'POST' });
    fetchWorkflows();
  };

  const handleResume = async (id: string) => {
    await fetch(`${API_BASE_URL}/api/workflows/${id}/resume`, { method: 'POST' });
    fetchWorkflows();
  };

  const handleCancel = async (id: string) => {
    await fetch(`${API_BASE_URL}/api/workflows/${id}/cancel`, { method: 'POST' });
    fetchWorkflows();
  };

  const handleTriggerAgent = async () => {
    await fetch(`${API_BASE_URL}/api/workflows/trigger-agent`, { method: 'POST' });
    fetchWorkflows();
  };

  const handleTriggerScheduler = async () => {
    await fetch(`${API_BASE_URL}/api/workflows/trigger-scheduler`, { method: 'POST' });
    fetchWorkflows();
  };

  const addStepField = () => setSteps([...steps, '']);
  const removeStepField = (idx: number) => setSteps(steps.filter((_, i) => i !== idx));
  const updateStepField = (idx: number, val: string) => {
    const copy = [...steps];
    copy[idx] = val;
    setSteps(copy);
  };

  useEffect(() => {
    fetchWorkflows();
  }, []);

  return (
    <div className="glass-panel p-6 rounded-2xl flex flex-col lg:flex-row gap-6 overflow-hidden h-full flex-1">
      {/* Left Column: Workflow Builder */}
      <div className="w-full lg:w-5/12 flex flex-col gap-4 border-r border-slate-800/40 pr-6">
        <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
          <GitMerge className="text-prime-cyan" size={18} />
          <span className="text-xs font-mono font-bold uppercase tracking-widest text-white">WORKFLOW BUILDER</span>
        </div>

        <form onSubmit={handleCreateWorkflow} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-[9px] font-mono text-slate-500 font-bold uppercase">WORKFLOW NAME</label>
            <input
              type="text"
              value={workflowName}
              onChange={(e) => setWorkflowName(e.target.value)}
              placeholder="e.g. Daily Backup System"
              className="bg-slate-950/80 border border-slate-850 rounded-lg px-3 py-2 text-xs text-white font-mono focus:border-prime-cyan outline-none"
              required
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <div className="flex justify-between items-center">
              <label className="text-[9px] font-mono text-slate-500 font-bold uppercase">EXECUTION STEPS</label>
              <button
                type="button"
                onClick={addStepField}
                className="text-[8px] font-mono font-bold text-prime-cyan bg-prime-cyan/10 border border-prime-cyan/20 px-1.5 py-0.5 rounded hover:bg-prime-cyan/20 transition-all flex items-center gap-0.5"
              >
                <Plus size={8} /> ADD STEP
              </button>
            </div>
            
            <div className="flex flex-col gap-2 max-h-[180px] overflow-y-auto pr-1">
              {steps.map((step, idx) => (
                <div key={idx} className="flex gap-2">
                  <span className="text-[10px] font-mono text-slate-600 flex items-center w-4 justify-end">{idx + 1}.</span>
                  <input
                    type="text"
                    value={step}
                    onChange={(e) => updateStepField(idx, e.target.value)}
                    placeholder="e.g. echo build task"
                    className="flex-1 bg-slate-950/80 border border-slate-850 rounded-lg px-3 py-1.5 text-xs text-white font-mono focus:border-prime-cyan outline-none"
                    required
                  />
                  {steps.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeStepField(idx)}
                      className="p-1.5 rounded-lg border border-slate-800 bg-slate-900/60 text-slate-500 hover:text-red-400 hover:border-red-400/30 transition-all"
                    >
                      <Trash2 size={12} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[9px] font-mono text-slate-500 font-bold uppercase flex items-center gap-1">
              <Calendar size={10} /> SCHEDULER CRON (OPTIONAL)
            </label>
            <input
              type="text"
              value={cronExpression}
              onChange={(e) => setCronExpression(e.target.value)}
              placeholder="e.g. @daily, @hourly or standard cron expression"
              className="bg-slate-950/80 border border-slate-850 rounded-lg px-3 py-2 text-xs text-white font-mono focus:border-prime-cyan outline-none"
            />
          </div>

          <button
            type="submit"
            className="bg-prime-cyan text-slate-950 font-mono font-bold text-[10px] py-2 px-4 rounded-lg flex items-center justify-center gap-1.5 hover:bg-white transition-all shadow-[0_0_15px_rgba(0,240,255,0.2)] mt-2"
          >
            <Plus size={12} /> INSTANTIATE WORKFLOW
          </button>
        </form>
      </div>

      {/* Right Column: Execution Monitoring & Control Panel */}
      <div className="flex-1 flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <div className="flex items-center gap-2">
            <Bot className="text-prime-purple animate-pulse" size={18} />
            <span className="text-xs font-mono font-bold uppercase tracking-widest text-white">AUTONOMOUS MONITORING</span>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleTriggerAgent}
              className="text-[9px] font-mono font-bold text-prime-cyan bg-prime-cyan/10 border border-prime-cyan/20 px-2.5 py-1 rounded hover:bg-prime-cyan/20 transition-all flex items-center gap-1"
              title="Force execute one step of pending workflows"
            >
              <Bot size={10} /> RUN AGENT LOOP
            </button>
            <button
              onClick={handleTriggerScheduler}
              className="text-[9px] font-mono font-bold text-slate-400 bg-slate-900 border border-slate-800 px-2.5 py-1 rounded hover:text-white transition-all flex items-center gap-1"
              title="Force evaluate cron schedule timings"
            >
              <Calendar size={10} /> EVAL SCHEDULER
            </button>
            <button
              onClick={fetchWorkflows}
              className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition-colors"
            >
              <RefreshCw size={12} />
            </button>
          </div>
        </div>

        {/* Workflows List */}
        <div className="flex-1 overflow-y-auto max-h-[360px] pr-1 flex flex-col gap-3">
          {workflows.map((wf) => {
            const stepsList = JSON.parse(wf.steps) as string[];
            return (
              <div key={wf.id} className="bg-slate-900/40 border border-slate-850 p-4 rounded-xl flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <div className="flex flex-col">
                    <span className="text-xs font-mono font-bold text-white">{wf.name}</span>
                    <span className="text-[8px] font-mono text-slate-500 uppercase mt-0.5">ID: {wf.id}</span>
                  </div>

                  <span className={`text-[8px] font-mono font-bold px-2 py-0.5 rounded border ${
                    wf.status === 'completed' 
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : wf.status === 'failed'
                      ? 'bg-red-500/10 text-red-400 border-red-500/20 animate-pulse'
                      : wf.status === 'paused'
                      ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      : 'bg-prime-cyan/10 text-prime-cyan border-prime-cyan/20'
                  }`}>
                    {wf.status.toUpperCase()}
                  </span>
                </div>

                {/* Progress bar */}
                <div className="flex flex-col gap-1">
                  <div className="flex justify-between text-[8px] font-mono text-slate-500 font-bold">
                    <span>STEP {wf.current_step} OF {stepsList.length}</span>
                    <span>{Math.round((wf.current_step / stepsList.length) * 100)}%</span>
                  </div>
                  <div className="w-full h-1 bg-slate-950 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-prime-cyan transition-all duration-500" 
                      style={{ width: `${(wf.current_step / stepsList.length) * 100}%` }}
                    />
                  </div>
                </div>

                {/* Steps Details */}
                <div className="bg-black/20 p-2.5 rounded-lg border border-slate-950 flex flex-col gap-1">
                  <span className="text-[8px] font-mono text-slate-500 font-bold">ACTIVE COMMAND</span>
                  <p className="text-[10px] font-mono text-slate-300">
                    {stepsList[wf.current_step] || 'Workflow execution complete.'}
                  </p>
                </div>

                {/* Controls */}
                <div className="flex justify-between items-center pt-1 border-t border-slate-800/30">
                  <div className="flex items-center gap-2 text-[9px] font-mono text-slate-500">
                    {wf.schedule_cron && (
                      <span className="flex items-center gap-1"><Calendar size={10} /> {wf.schedule_cron}</span>
                    )}
                  </div>

                  <div className="flex gap-2">
                    {wf.status === 'running' || wf.status === 'pending' ? (
                      <button
                        onClick={() => handlePause(wf.id)}
                        className="p-1 px-2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 transition-all text-[8px] font-mono font-bold flex items-center gap-0.5"
                      >
                        <Pause size={8} /> PAUSE
                      </button>
                    ) : wf.status === 'paused' ? (
                      <button
                        onClick={() => handleResume(wf.id)}
                        className="p-1 px-2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition-all text-[8px] font-mono font-bold flex items-center gap-0.5"
                      >
                        <Play size={8} /> RESUME
                      </button>
                    ) : null}

                    {wf.status !== 'completed' && wf.status !== 'cancelled' && wf.status !== 'failed' && (
                      <button
                        onClick={() => handleCancel(wf.id)}
                        className="p-1 px-2 rounded bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 transition-all text-[8px] font-mono font-bold flex items-center gap-0.5"
                      >
                        <XOctagon size={8} /> CANCEL
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

          {workflows.length === 0 && !loading && (
            <div className="text-slate-500 text-center font-mono text-[10px] py-16">
              No workflows registered in database. Use builder form to instantiate new workflows.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
