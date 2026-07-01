import { useState, useRef, useEffect } from 'react';
import type { FormEvent } from 'react';
import { Terminal as TerminalIcon, ShieldAlert, Check, X, ArrowRight } from 'lucide-react';

export interface TerminalLog {
  id: string;
  type: 'info' | 'success' | 'warn' | 'error' | 'command' | 'stdout';
  message: string;
  timestamp: string;
}

export interface SecurityChallenge {
  challengeId: string;
  command: string;
  description: string;
  affected_files?: string;
  estimated_impact?: string;
}

interface TerminalProps {
  logs: TerminalLog[];
  challenge: SecurityChallenge | null;
  onApprove: (challengeId: string) => void;
  onDeny: (challengeId: string) => void;
  onExecuteCommand: (command: string) => void;
}

export const Terminal = ({
  logs,
  challenge,
  onApprove,
  onDeny,
  onExecuteCommand
}: TerminalProps) => {
  const [input, setInput] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs, challenge]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    onExecuteCommand(input);
    setInput('');
  };

  const getLogColorClass = (type: TerminalLog['type']) => {
    switch (type) {
      case 'success':
        return 'text-emerald-400';
      case 'warn':
        return 'text-amber-400';
      case 'error':
        return 'text-rose-400';
      case 'command':
        return 'text-prime-cyan font-semibold';
      case 'stdout':
        return 'text-slate-300';
      case 'info':
      default:
        return 'text-slate-400';
    }
  };

  return (
    <div className="glass-panel rounded-2xl border border-slate-800/80 flex flex-col h-[350px] overflow-hidden">
      {/* Terminal Title Bar */}
      <div className="bg-slate-950/60 px-4 py-2 border-b border-slate-800/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TerminalIcon size={14} className="text-prime-cyan" />
          <span className="text-xs font-mono font-bold tracking-wider text-slate-400 uppercase">PRIME SHELL TERMINAL</span>
        </div>
        <div className="flex gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500/30" />
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500/30" />
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/30" />
        </div>
      </div>

      {/* Terminal Console Logs */}
      <div ref={containerRef} className="flex-1 p-4 overflow-y-auto font-mono text-xs space-y-2.5 bg-black/40">
        {logs.map((log) => (
          <div key={log.id} className="flex items-start gap-2 leading-relaxed">
            <span className="text-slate-600 select-none">[{log.timestamp}]</span>
            {log.type === 'command' && <span className="text-prime-cyan select-none">&gt;_</span>}
            <span className={getLogColorClass(log.type)}>{log.message}</span>
          </div>
        ))}

        {/* Security Challenge Box (Halts Execution) */}
        {challenge && (
          <div className="mt-4 border border-rose-500/30 bg-rose-950/10 rounded-lg p-4 flex flex-col gap-3 animate-pulse-slow">
            <div className="flex items-center gap-2 text-rose-400 font-bold">
              <ShieldAlert size={16} />
              <span>SECURITY GATE CHALLENGE</span>
            </div>
            <div className="text-slate-300">
              An agent requested execution of the following system action:
            </div>
            <div className="bg-black/60 p-3 rounded border border-slate-800 font-mono text-prime-cyan break-all">
              {challenge.command}
            </div>
            <div className="text-slate-400 text-[11px] italic">
              Reason: {challenge.description}
            </div>
            {challenge.affected_files && challenge.affected_files !== 'None' && (
              <div className="text-slate-300 text-[10px] font-mono">
                Affected Resources: {challenge.affected_files}
              </div>
            )}
            {challenge.estimated_impact && challenge.estimated_impact !== 'None' && (
              <div className="text-amber-400/90 text-[10px] font-sans">
                Estimated Impact: {challenge.estimated_impact}
              </div>
            )}
            <div className="flex gap-3 mt-1">
              <button
                onClick={() => onApprove(challenge.challengeId)}
                className="flex items-center justify-center gap-1.5 flex-1 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-400 px-3 py-2 rounded font-bold transition-all text-[11px]"
              >
                <Check size={14} />
                APPROVE OPERATION
              </button>
              <button
                onClick={() => onDeny(challenge.challengeId)}
                className="flex items-center justify-center gap-1.5 flex-1 bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-400 px-3 py-2 rounded font-bold transition-all text-[11px]"
              >
                <X size={14} />
                ABORT OPERATION
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Manual Input Bar */}
      <form onSubmit={handleSubmit} className="border-t border-slate-800/80 bg-slate-950/60 p-2.5 flex items-center gap-2">
        <span className="text-prime-cyan font-bold pl-2 select-none">&gt;</span>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={challenge ? "Operations locked. Please resolve security gate..." : "Enter system automation command or query..."}
          disabled={!!challenge}
          className="flex-1 bg-transparent border-none outline-none font-mono text-xs text-white placeholder-slate-600 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!!challenge || !input.trim()}
          className="p-1.5 rounded-lg bg-prime-cyan/10 hover:bg-prime-cyan/20 border border-prime-cyan/20 text-prime-cyan disabled:opacity-30 disabled:hover:bg-transparent transition-all"
        >
          <ArrowRight size={14} />
        </button>
      </form>
    </div>
  );
};
