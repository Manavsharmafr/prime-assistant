import { useState, useEffect } from 'react';
import { 
  Mic, 
  MicOff, 
  Eye, 
  RefreshCw, 
  Volume2
} from 'lucide-react';

const API_BASE_URL = 'http://127.0.0.1:8000';

interface VoiceConsoleProps {
  status: 'idle' | 'processing' | 'listening' | 'speaking';
  isMuted: boolean;
  onVoiceTrigger: () => void;
  onMuteToggle: () => void;
}

export const VoiceConsole = ({
  status,
  isMuted,
  onVoiceTrigger,
  onMuteToggle
}: VoiceConsoleProps) => {
  const [screenshot, setScreenshot] = useState<string | null>(null);
  const [autoRefreshScreen, setAutoRefreshScreen] = useState(false);
  const [wakeWordEnabled, setWakeWordEnabled] = useState(true);
  const [screenSummary, setScreenSummary] = useState<string>('');
  const [loadingSummary, setLoadingSummary] = useState(false);

  const fetchScreenshot = async () => {
    try {
      const resp = await fetch(`${API_BASE_URL}/api/desktop/screenshot`);
      if (resp.ok) {
        const data = await resp.json();
        setScreenshot(data.image);
      }
    } catch (err) {
      console.error('Failed to capture screen:', err);
    }
  };

  const handleSummarizeScreen = async () => {
    setLoadingSummary(true);
    try {
      const resp = await fetch(`${API_BASE_URL}/api/agents/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: 'vision summarize' })
      });
      if (resp.ok) {
        const data = await resp.json();
        setScreenSummary(data.result || 'No summary compiled.');
      }
    } catch (err) {
      setScreenSummary('Failed to compile vision summary.');
    } finally {
      setLoadingSummary(false);
    }
  };

  useEffect(() => {
    fetchScreenshot();
  }, []);

  useEffect(() => {
    if (!autoRefreshScreen) return;
    fetchScreenshot();
    const interval = setInterval(fetchScreenshot, 4000);
    return () => clearInterval(interval);
  }, [autoRefreshScreen]);

  return (
    <div className="glass-panel p-6 rounded-2xl flex flex-col lg:flex-row gap-6 overflow-hidden">
      {/* Left Column: Voice Commands & Telemetry */}
      <div className="w-full lg:w-1/2 flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Mic className="text-prime-purple animate-pulse" size={18} />
            <span className="text-xs font-mono font-bold tracking-widest text-white">VOICE INTELLIGENCE Console</span>
          </div>
          <span className={`h-2 w-2 rounded-full ${status === 'listening' ? 'bg-red-500 animate-ping' : 'bg-slate-700'}`} />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="bg-slate-900/50 border border-slate-850 p-4 rounded-xl flex flex-col gap-2">
            <span className="text-slate-500 text-[8px] font-mono uppercase tracking-wider font-bold">WAKE WORD DETECTOR</span>
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-slate-200">"HEY PRIME"</span>
              <button 
                onClick={() => setWakeWordEnabled(!wakeWordEnabled)}
                className={`w-9 h-5 rounded-full p-0.5 transition-colors focus:outline-none ${
                  wakeWordEnabled ? 'bg-prime-cyan' : 'bg-slate-800'
                }`}
              >
                <div className={`w-4 h-4 rounded-full bg-slate-950 transition-transform ${
                  wakeWordEnabled ? 'translate-x-4' : 'translate-x-0'
                }`} />
              </button>
            </div>
          </div>

          <div className="bg-slate-900/50 border border-slate-850 p-4 rounded-xl flex flex-col gap-2">
            <span className="text-slate-500 text-[8px] font-mono uppercase tracking-wider font-bold">AUDIO RESPONSES</span>
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-slate-200">{isMuted ? 'MUTED' : 'ENABLED'}</span>
              <button
                onClick={onMuteToggle}
                className={`p-1.5 rounded-lg border transition-all ${
                  !isMuted 
                    ? 'bg-prime-cyan/10 text-prime-cyan border-prime-cyan/30' 
                    : 'bg-slate-850 text-slate-400 border-slate-800'
                }`}
              >
                {isMuted ? <MicOff size={12} /> : <Volume2 size={12} />}
              </button>
            </div>
          </div>
        </div>

        <div className="bg-slate-900/30 border border-slate-850 p-4 rounded-xl flex flex-col gap-3 flex-1 justify-center items-center text-center">
          <span className="text-slate-500 text-[8px] font-mono uppercase tracking-wider font-bold">PUSH TO TALK TRIGGER</span>
          <button
            onClick={onVoiceTrigger}
            className={`w-20 h-20 rounded-full border-2 flex items-center justify-center transition-all ${
              status === 'listening'
                ? 'bg-red-500/25 border-red-500 text-red-400 animate-pulse shadow-[0_0_20px_rgba(239,68,68,0.3)]'
                : 'bg-prime-purple/15 border-prime-purple text-prime-purple hover:bg-prime-purple/30 shadow-[0_0_20px_rgba(189,0,255,0.2)]'
            }`}
          >
            <Mic size={32} />
          </button>
          <span className="text-[10px] text-slate-400 font-mono">
            {status === 'listening' ? 'LISTENING... SAY "STOP" TO INTERRUPT' : 'CLICK TO INITIATE VOICE DIALOGUE'}
          </span>
        </div>
      </div>

      {/* Right Column: Screen Perception Preview */}
      <div className="w-full lg:w-1/2 flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Eye className="text-prime-cyan" size={18} />
            <span className="text-xs font-mono font-bold tracking-widest text-white">SCREEN PERCEPTION PREVIEW</span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setAutoRefreshScreen(!autoRefreshScreen)}
              className={`px-2 py-0.5 rounded text-[8px] font-mono font-bold transition-all ${
                autoRefreshScreen 
                  ? 'bg-prime-cyan/15 text-prime-cyan border border-prime-cyan/30' 
                  : 'bg-slate-850 text-slate-400 border border-transparent'
              }`}
            >
              AUTO-STREAM
            </button>
            <button 
              onClick={fetchScreenshot}
              className="p-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition-colors"
            >
              <RefreshCw size={10} />
            </button>
          </div>
        </div>

        {/* Screenshot view block */}
        <div className="relative border border-slate-850 rounded-xl overflow-hidden aspect-video bg-black/40 flex items-center justify-center">
          {screenshot ? (
            <img src={screenshot} alt="System screen preview" className="w-full h-full object-cover" />
          ) : (
            <div className="text-slate-500 font-mono text-[10px] flex items-center gap-1.5 animate-pulse">
              <RefreshCw size={12} className="animate-spin" /> CAPTURING WORKSPACE SCREENSHOT...
            </div>
          )}
        </div>

        {/* Screen summary report trigger */}
        <div className="bg-slate-900/40 border border-slate-850 p-3.5 rounded-xl flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-slate-500 text-[8px] font-mono uppercase tracking-wider font-bold">SCREEN COMPREHENSION REPORT</span>
            <button
              onClick={handleSummarizeScreen}
              disabled={loadingSummary}
              className="text-[9px] font-mono font-bold text-prime-cyan bg-prime-cyan/10 border border-prime-cyan/20 px-2 py-0.5 rounded hover:bg-prime-cyan/20 transition-all"
            >
              {loadingSummary ? 'SUMMARIZING...' : 'SUMMARIZE ACTIVE SCREEN'}
            </button>
          </div>
          <div className="bg-black/20 border border-slate-900/60 p-2.5 rounded-lg min-h-[44px]">
            <p className="text-[10px] text-slate-300 font-mono leading-relaxed">
              {screenSummary || 'No screen summary compiled. Click button to analyze what Prime currently sees.'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
