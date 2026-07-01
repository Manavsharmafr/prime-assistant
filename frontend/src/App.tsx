import { useState, useEffect, useRef } from 'react';
import { JarvisCore } from './components/JarvisCore';
import { Terminal } from './components/Terminal';
import type { TerminalLog, SecurityChallenge } from './components/Terminal';
import { SystemStats } from './components/SystemStats';
import { Research } from './components/Research';
import type { ResearchReport } from './components/Research';
import MemoryCenter from './components/MemoryCenter';
import SystemControlCenter from './components/SystemControlCenter';
import { PluginManagerDashboard } from './components/PluginManagerDashboard';
import { VoiceConsole } from './components/VoiceConsole';
import { DeveloperWorkspace } from './components/DeveloperWorkspace';
import { PrimeSpeechEngine } from './utils/speech';
import { Cpu, Wifi, WifiOff, BookOpen, Brain, Terminal as TerminalIcon, Activity, Puzzle, Code2 } from 'lucide-react';

const API_BASE_URL = 'http://127.0.0.1:8000';

export default function App() {
  // Application State
  const [activeTab, setActiveTab] = useState<'console' | 'memory' | 'system' | 'plugins' | 'developer'>('console');
  const [status, setStatus] = useState<'idle' | 'processing' | 'listening' | 'speaking'>('idle');
  const [isMuted, setIsMuted] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  
  const [stats, setStats] = useState<any>(null);
  const [logs, setLogs] = useState<TerminalLog[]>([
    {
      id: 'init',
      type: 'info',
      message: 'Prime Assistant Interface Loaded. System diagnostics initialising...',
      timestamp: new Date().toLocaleTimeString()
    }
  ]);
  const [challenge, setChallenge] = useState<SecurityChallenge | null>(null);
  const [reports, setReports] = useState<ResearchReport[]>([]);
  const [activeReportId, setActiveReportId] = useState<string | null>(null);

  // Speech Engine Ref
  const speechEngineRef = useRef<PrimeSpeechEngine | null>(null);

  const [agentState, setAgentState] = useState<any>({
    state: 'idle',
    model: 'offline',
    activeTool: undefined,
    reasoning: undefined,
    plan: undefined
  });

  useEffect(() => {
    if (!isConnected) return;
    
    const tasksWs = new WebSocket('ws://127.0.0.1:8000/api/ws/tasks');
    tasksWs.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === 'agent_state') {
          setAgentState({
            state: message.state,
            model: message.model,
            activeTool: message.active_tool,
            reasoning: message.reasoning,
            plan: message.plan
          });
          
          // Sync with Jarvis status
          if (message.state === 'planning' || message.state === 'executing') {
            setStatus('processing');
          } else if (message.state === 'idle') {
            setStatus('idle');
          }
        }
      } catch (err) {
        console.error("Error parsing WS task state:", err);
      }
    };

    return () => tasksWs.close();
  }, [isConnected]);

  // Add items to console logs helper
  const addLog = (message: string, type: TerminalLog['type'] = 'info') => {
    setLogs((prev) => [
      ...prev,
      {
        id: Math.random().toString(36).substring(7),
        type,
        message,
        timestamp: new Date().toLocaleTimeString()
      }
    ]);
  };

  // 1. Initialize Speech Engine
  useEffect(() => {
    speechEngineRef.current = new PrimeSpeechEngine();
    speechEngineRef.current.setCallbacks(
      (text, isFinal) => {
        if (isFinal) {
          addLog(`Voice Input detected: "${text}"`, 'command');
          handleCommandExecution(text);
        }
      },
      (newStatus) => {
        setStatus(newStatus);
      }
    );
  }, []);

  // 2. Poll Backend connection & telemetry stats
  useEffect(() => {
    let statInterval: ReturnType<typeof setInterval>;
    
    const checkConnectionAndStats = async () => {
      try {
        const statsRes = await fetch(`${API_BASE_URL}/api/system/stats`);
        if (statsRes.ok) {
          const statsData = await statsRes.json();
          setStats(statsData);
          if (!isConnected) {
            setIsConnected(true);
            addLog('Established connection with Prime Backend.', 'success');
          }
        }
      } catch (err) {
        if (isConnected) {
          setIsConnected(false);
          addLog('Lost connection to Prime Backend server. Falling back to local simulations.', 'warn');
        }
        // Fallback simulation stats
        setStats({
          cpu: { percent: Math.sin(Date.now() / 10000) * 10 + 25, cores: 8 },
          memory: { percent: 45, used_gb: 7.2, total_gb: 16.0 },
          disk: { percent: 62, used_gb: 310, total_gb: 500 }
        });
      }
    };

    checkConnectionAndStats();
    statInterval = setInterval(checkConnectionAndStats, 3000);

    return () => clearInterval(statInterval);
  }, [isConnected]);

  // 3. Command execution routing logic
  const handleCommandExecution = async (rawCommand: string) => {
    setStatus('processing');
    addLog(`Processing: "${rawCommand}"...`, 'info');

    // Speech feedback if not muted
    if (!isMuted && speechEngineRef.current) {
      speechEngineRef.current.speak(`Processing request: ${rawCommand.slice(0, 40)}`);
    }

    // Attempt backend agent invocation
    try {
      if (isConnected) {
        const response = await fetch(`${API_BASE_URL}/api/agents/command`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: rawCommand })
        });
        
        if (response.ok) {
          const data = await response.json();
          
          // Check if request triggered a security gate challenge
          if (data.status === 'challenge_required') {
            setChallenge({
              challengeId: data.challenge_id,
              command: data.command,
              description: data.description,
              affected_files: data.affected_files,
              estimated_impact: data.estimated_impact
            });
            addLog(`OPERATION LOCKED: Security authorization required for: "${data.command}"`, 'warn');
            setStatus('idle');
          } else {
            addLog(data.result || 'Command executed successfully.', 'success');
            
            // Speak back output
            if (!isMuted && speechEngineRef.current && data.speech_response) {
              speechEngineRef.current.speak(data.speech_response);
            }

            // If a research report was returned, add it
            if (data.report) {
              const newReport: ResearchReport = {
                id: data.report.id,
                title: data.report.title,
                summary: data.report.summary,
                content: data.report.content,
                sources: data.report.sources || [],
                timestamp: new Date().toLocaleDateString()
              };
              setReports(prev => [newReport, ...prev]);
              setActiveReportId(newReport.id);
            }
            setStatus('idle');
          }
        } else {
          addLog(`Server responded with error: ${response.statusText}`, 'error');
          setStatus('idle');
        }
      } else {
        // Connected offline mock simulation responses
        setTimeout(() => {
          simulateOfflineResponse(rawCommand);
        }, 1500);
      }
    } catch (e) {
      addLog(`Communication failed: ${String(e)}`, 'error');
      setStatus('idle');
    }
  };

  // Offline Simulation Responses (Premium interface responsiveness)
  const simulateOfflineResponse = (cmd: string) => {
    const text = cmd.toLowerCase();
    
    if (text.includes('search') || text.includes('research') || text.includes('find info')) {
      const mockReport: ResearchReport = {
        id: Math.random().toString(36).substring(7),
        title: `Research Report: ${cmd}`,
        summary: `This is a compiled report summarizing offline data for: "${cmd}"`,
        content: `### Summary of Findings\n- Active local services are functioning.\n- Offline simulation indicates successful routing.\n- Integrations can be unlocked by running the backend server locally.\n\n### Performance telemetry\nAll CPU/Memory modules are running in green parameters.`,
        sources: [
          { title: "Gemini AI Workspace Documentation", url: "https://ai.google.dev" },
          { title: "FastAPI Reference Framework", url: "https://fastapi.tiangolo.com" }
        ],
        timestamp: new Date().toLocaleDateString()
      };
      setReports(prev => [mockReport, ...prev]);
      setActiveReportId(mockReport.id);
      addLog(`Offline Search complete: compiled mock report.`, 'success');
      if (!isMuted && speechEngineRef.current) {
        speechEngineRef.current.speak("Research report compiled successfully.");
      }
    } else if (text.includes('open') || text.includes('run') || text.includes('delete') || text.includes('make')) {
      // Simulate security gate challenge
      setChallenge({
        challengeId: 'mock-challenge-123',
        command: `powershell.exe -Command "Start-Process ${cmd.split(' ')[1] || 'notepad.exe'}"`,
        description: `Requested by phrase "${cmd}"`,
        affected_files: "notepad.exe / cmd process handles",
        estimated_impact: "Starts a new local editor GUI application session"
      });
      addLog(`OPERATION HALTED: Local command execution requires manual user authorization.`, 'warn');
    } else {
      const resp = `Command "${cmd}" received. Backend is offline, but interface simulation indicates command parsing is correct.`;
      addLog(resp, 'info');
      if (!isMuted && speechEngineRef.current) {
        speechEngineRef.current.speak(resp);
      }
    }
    setStatus('idle');
  };

  // 4. Security Challenge Handling
  const handleApproveChallenge = async (id: string) => {
    addLog(`Authorising operation [Challenge: ${id}]...`, 'info');
    setChallenge(null);

    if (isConnected) {
      try {
        const res = await fetch(`${API_BASE_URL}/api/agents/challenges/${id}/approve`, {
          method: 'POST'
        });
        if (res.ok) {
          const data = await res.json();
          addLog(`Operation completed successfully: ${data.stdout || ''}`, 'success');
          if (data.stderr) {
            addLog(`Error log: ${data.stderr}`, 'warn');
          }
        }
      } catch (err) {
        addLog(`Failed to send authorization: ${String(err)}`, 'error');
      }
    } else {
      // Simulate success in offline mockup
      setTimeout(() => {
        addLog(`Offline Simulation: Command executed successfully on Windows kernel.`, 'success');
        if (!isMuted && speechEngineRef.current) {
          speechEngineRef.current.speak("Operation executed successfully.");
        }
      }, 800);
    }
  };

  const handleDenyChallenge = async (id: string) => {
    addLog(`Aborting operation [Challenge: ${id}] by user decision.`, 'error');
    setChallenge(null);

    if (isConnected) {
      try {
        await fetch(`${API_BASE_URL}/api/agents/challenges/${id}/deny`, {
          method: 'POST'
        });
      } catch (err) {
        console.error(err);
      }
    }
  };

  // Toggle Voice Output
  const handleMuteToggle = () => {
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    if (nextMuted && speechEngineRef.current) {
      speechEngineRef.current.stopSpeaking();
    }
    addLog(nextMuted ? 'Jarvis synthesized audio outputs disabled.' : 'Jarvis synthesized audio outputs active.', 'info');
  };

  // Toggle Listening Core
  const handleVoiceTrigger = () => {
    if (!speechEngineRef.current) return;

    if (status === 'listening') {
      speechEngineRef.current.stopListening();
    } else {
      // Chrome requires a user-gesture like clicking before allowing microphone
      speechEngineRef.current.startListening();
      addLog('Continuous voice detection channel open.', 'info');
    }
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden text-slate-100 font-sans">
      {/* Top Navigation Bar */}
      <header className="glass-panel px-6 py-4 flex items-center justify-between border-b border-slate-800/40 bg-slate-950/20 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-3.5 h-3.5 rounded-full bg-prime-cyan opacity-25 animate-ping absolute" />
            <Cpu className="text-prime-cyan relative" size={20} />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-bold tracking-widest text-white font-mono leading-none flex items-center gap-2">
              PRIME <span className="text-[10px] bg-prime-cyan/10 border border-prime-cyan/30 text-prime-cyan px-1.5 py-0.5 rounded">V1.0</span>
            </span>
            <span className="text-[10px] text-slate-500 font-mono mt-0.5">LOCAL OPERATING INTELLIGENCE</span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 bg-slate-900/40 border border-slate-800/80 p-1 rounded-xl">
          <button
            onClick={() => setActiveTab('console')}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[11px] font-mono font-bold tracking-wider transition-all ${
              activeTab === 'console'
                ? 'bg-prime-cyan/10 text-prime-cyan border border-prime-cyan/20 shadow-[0_0_8px_rgba(0,240,255,0.08)]'
                : 'text-slate-400 hover:text-white border border-transparent'
            }`}
          >
            <TerminalIcon size={12} />
            CONSOLE
          </button>
          <button
            onClick={() => setActiveTab('memory')}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[11px] font-mono font-bold tracking-wider transition-all ${
              activeTab === 'memory'
                ? 'bg-prime-purple/10 text-prime-purple border border-prime-purple/20 shadow-[0_0_8px_rgba(189,0,255,0.08)]'
                : 'text-slate-400 hover:text-white border border-transparent'
            }`}
          >
            <Brain size={12} />
            MEMORY CENTER
          </button>
          <button
            onClick={() => setActiveTab('system')}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[11px] font-mono font-bold tracking-wider transition-all ${
              activeTab === 'system'
                ? 'bg-prime-cyan/10 text-prime-cyan border border-prime-cyan/20 shadow-[0_0_8px_rgba(0,240,255,0.08)]'
                : 'text-slate-400 hover:text-white border border-transparent'
            }`}
          >
            <Activity size={12} />
            SYSTEM CONTROLS
          </button>
          
          <button
            onClick={() => setActiveTab('plugins')}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[11px] font-mono font-bold tracking-wider transition-all ${
              activeTab === 'plugins'
                ? 'bg-prime-purple/10 text-prime-purple border border-prime-purple/20 shadow-[0_0_8px_rgba(189,0,255,0.08)]'
                : 'text-slate-400 hover:text-white border border-transparent'
            }`}
          >
            <Puzzle size={12} />
            EXTENSIONS
          </button>
          
          <button
            onClick={() => setActiveTab('developer')}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[11px] font-mono font-bold tracking-wider transition-all ${
              activeTab === 'developer'
                ? 'bg-prime-cyan/10 text-prime-cyan border border-prime-cyan/20 shadow-[0_0_8px_rgba(0,240,255,0.08)]'
                : 'text-slate-400 hover:text-white border border-transparent'
            }`}
          >
            <Code2 size={12} />
            COCKPIT
          </button>
        </div>

        {/* Global telemetry states */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 bg-slate-900/60 border border-slate-800 px-3 py-1.5 rounded-xl font-mono text-[10px]">
            <BookOpen size={12} className="text-prime-purple" />
            <span className="text-slate-400">Reports:</span>
            <span className="text-white font-bold">{reports.length}</span>
          </div>
          
          <div className="flex items-center gap-2">
            {isConnected ? (
              <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-mono bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-xl">
                <Wifi size={14} />
                ONLINE
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs text-amber-500 font-mono bg-amber-500/5 border border-amber-500/10 px-3 py-1.5 rounded-xl">
                <WifiOff size={14} />
                LOCAL EMULATOR
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Layout Grid */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 overflow-hidden bg-gradient-to-b from-black/20 to-black/40">
        
        {/* Left Telemetries/Core Section (4 columns) */}
        <section className="lg:col-span-4 flex flex-col gap-6 overflow-y-auto">
          <JarvisCore
            status={status}
            isMuted={isMuted}
            onMuteToggle={handleMuteToggle}
            onVoiceTrigger={handleVoiceTrigger}
            agentState={agentState}
          />
          <SystemStats stats={stats} securityMode={true} />
        </section>

        {/* Right Console/Research Operations Section (8 columns) */}
        <section className="lg:col-span-8 flex flex-col gap-6 overflow-hidden">
          {activeTab === 'console' ? (
            <>
              <Terminal
                logs={logs}
                challenge={challenge}
                onApprove={handleApproveChallenge}
                onDeny={handleDenyChallenge}
                onExecuteCommand={handleCommandExecution}
              />
              <VoiceConsole
                status={status}
                isMuted={isMuted}
                onVoiceTrigger={handleVoiceTrigger}
                onMuteToggle={handleMuteToggle}
              />
              <Research
                reports={reports}
                activeReportId={activeReportId}
                onSelectReport={(id) => setActiveReportId(id)}
              />
            </>
          ) : activeTab === 'memory' ? (
            <MemoryCenter />
          ) : activeTab === 'system' ? (
            <SystemControlCenter />
          ) : activeTab === 'plugins' ? (
            <PluginManagerDashboard />
          ) : (
            <DeveloperWorkspace />
          )}
        </section>
      </main>
    </div>
  );
}
