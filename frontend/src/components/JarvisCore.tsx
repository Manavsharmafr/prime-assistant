import { Mic, MicOff, Volume2 } from 'lucide-react';

interface JarvisCoreProps {
  status: 'idle' | 'processing' | 'listening' | 'speaking';
  isMuted: boolean;
  onMuteToggle: () => void;
  onVoiceTrigger: () => void;
  agentState?: {
    state: string;
    model: string;
    activeTool?: string;
    reasoning?: string;
    plan?: Array<{ task: string; tool: string; arguments: any }>;
  };
}

export const JarvisCore = ({
  status,
  isMuted,
  onMuteToggle,
  onVoiceTrigger,
  agentState
}: JarvisCoreProps) => {
  const getCoreColorClass = () => {
    switch (status) {
      case 'listening':
        return 'from-red-500/80 to-pink-500/80 shadow-[0_0_30px_rgba(239,68,68,0.5)] border-red-400';
      case 'processing':
        return 'from-prime-purple to-indigo-500 shadow-[0_0_30px_rgba(189,0,255,0.5)] border-prime-purple';
      case 'speaking':
        return 'from-emerald-400 to-teal-500 shadow-[0_0_30px_rgba(16,185,129,0.5)] border-emerald-400';
      case 'idle':
      default:
        return 'from-prime-cyan to-blue-500 shadow-[0_0_30px_rgba(0,240,255,0.4)] border-prime-cyan';
    }
  };

  const getStatusLabel = () => {
    switch (status) {
      case 'listening':
        return 'LISTENING';
      case 'processing':
        return 'THINKING';
      case 'speaking':
        return 'SPEAKING';
      case 'idle':
      default:
        return 'STANDBY';
    }
  };

  return (
    <div className="glass-panel p-6 rounded-2xl flex flex-col items-center justify-center gap-6 relative overflow-hidden">
      {/* Background grids */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-slate-900/10 via-transparent to-transparent pointer-events-none" />

      {/* Main Reactor Widget */}
      <div className="relative w-44 h-44 flex items-center justify-center cursor-pointer" onClick={onVoiceTrigger}>
        {/* Outer Tech Ring 1 (Dashed rotation) */}
        <div className={`absolute inset-0 rounded-full border border-dashed border-slate-700/50 ${
          status === 'processing' ? 'animate-spin' : ''
        }`} style={{ animationDuration: '20s' }} />

        {/* Outer Tech Ring 2 (Dashed opposite rotation) */}
        <div className={`absolute w-[90%] h-[90%] rounded-full border border-dashed border-slate-500/20 ${
          status === 'processing' ? 'animate-spin' : ''
        }`} style={{ animationDuration: '10s', animationDirection: 'reverse' }} />

        {/* Pulsing visual glow background */}
        <div className={`absolute w-[70%] h-[70%] rounded-full opacity-20 blur-md bg-gradient-to-tr ${getCoreColorClass()}`} />

        {/* Action Ring */}
        <div className={`absolute w-[75%] h-[75%] rounded-full border-2 border-slate-800 transition-all duration-300 flex items-center justify-center`}>
          {/* Reactor core element */}
          <div className={`w-20 h-20 rounded-full bg-gradient-to-tr ${getCoreColorClass()} flex items-center justify-center border transition-all duration-500`}>
            {status === 'listening' ? (
              <Mic className="text-white animate-pulse" size={32} />
            ) : status === 'speaking' ? (
              <Volume2 className="text-white" size={32} />
            ) : (
              <div className="w-6 h-6 rounded-full bg-white/20 animate-ping" />
            )}
          </div>
        </div>

        {/* Waveform overlays for active statuses */}
        {status === 'speaking' && (
          <div className="absolute w-[115%] h-[115%] rounded-full border border-emerald-500/30 animate-ping" style={{ animationDuration: '1.8s' }} />
        )}
        {status === 'listening' && (
          <div className="absolute w-[110%] h-[110%] rounded-full border border-red-500/30 animate-pulse" />
        )}
      </div>

      {/* Controller Buttons & Mode Labels */}
      <div className="flex flex-col items-center gap-2 z-10 w-full">
        <span className={`text-xs font-mono font-bold tracking-widest ${
          status === 'listening' ? 'text-red-400' :
          status === 'processing' ? 'text-prime-purple' :
          status === 'speaking' ? 'text-emerald-400' : 'text-prime-cyan'
        } glow-text-cyan`}>
          PRIME CORE // {getStatusLabel()}
        </span>
        
        <div className="flex items-center gap-3 mt-1 bg-slate-900/60 border border-slate-800/80 px-4 py-1.5 rounded-full backdrop-blur-md">
          <button 
            onClick={onMuteToggle}
            className={`p-1 rounded-full hover:bg-slate-800 transition-colors ${isMuted ? 'text-rose-400' : 'text-slate-400 hover:text-white'}`}
            title={isMuted ? "Unmute Voice Responses" : "Mute Voice Responses"}
          >
            {isMuted ? <MicOff size={16} /> : <Mic size={16} />}
          </button>
          <span className="w-px h-3 bg-slate-800" />
          <button 
            onClick={onVoiceTrigger} 
            className="text-xs font-mono font-bold text-slate-300 hover:text-prime-cyan transition-colors"
          >
            {status === 'listening' ? 'STOP LISTENING' : 'TALK TO PRIME'}
          </button>
        </div>
      </div>

      {/* AI Orchestrator Telemetry Panel */}
      {agentState && (
        <div className="w-full mt-2 pt-4 border-t border-slate-800/60 font-mono text-[10px] text-slate-400 flex flex-col gap-3 z-10">
          <div className="flex items-center justify-between text-xs border-b border-slate-900 pb-1.5">
            <span className="font-bold text-white tracking-wider flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-prime-purple animate-pulse" />
              ORCHESTRATOR STATUS
            </span>
            <span className="text-[10px] text-prime-cyan bg-prime-cyan/5 border border-prime-cyan/30 px-2 py-0.5 rounded font-bold">
              {agentState.model.toUpperCase()}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <span className="text-slate-500 uppercase tracking-widest block text-[8px]">Agent State</span>
              <span className={`font-bold ${agentState.state !== 'idle' ? 'text-prime-purple animate-pulse' : 'text-slate-300'}`}>
                {agentState.state.toUpperCase()}
              </span>
            </div>
            <div>
              <span className="text-slate-500 uppercase tracking-widest block text-[8px]">Active Tool</span>
              <span className="font-bold text-prime-cyan">
                {agentState.activeTool ? agentState.activeTool.toUpperCase() : 'NONE'}
              </span>
            </div>
          </div>

          {agentState.reasoning && (
            <div className="bg-slate-900/60 border border-slate-800 p-2.5 rounded-xl text-slate-300">
              <span className="text-slate-500 uppercase tracking-widest block text-[8px] mb-1 font-bold">Reasoning Progress</span>
              <span className="font-sans text-[11px] leading-relaxed">{agentState.reasoning}</span>
            </div>
          )}

          {agentState.plan && agentState.plan.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <span className="text-slate-500 uppercase tracking-widest block text-[8px] font-bold">Execution Plan</span>
              <div className="flex flex-col gap-1 bg-black/20 border border-slate-900/50 p-2 rounded-xl max-h-[120px] overflow-y-auto">
                {agentState.plan.map((step, idx) => (
                  <div key={idx} className="flex items-center gap-2 border-b border-slate-900/40 pb-1 last:border-none">
                    <span className={`w-3.5 h-3.5 rounded-full flex items-center justify-center text-[8px] font-bold ${
                      agentState.activeTool === step.tool && agentState.state !== 'idle'
                        ? 'bg-prime-cyan text-slate-950 animate-pulse'
                        : 'bg-slate-800 text-slate-400'
                    }`}>
                      {idx + 1}
                    </span>
                    <span className="truncate flex-1 text-slate-300">{step.task}</span>
                    <span className="text-[8px] bg-slate-900 px-1 rounded text-slate-500">{step.tool}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
