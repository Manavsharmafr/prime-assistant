import { useState, useEffect } from 'react';
import { 
  Code2, 
  Search, 
  GitBranch, 
  RefreshCw, 
  FileCode, 
  Hash
} from 'lucide-react';

const API_BASE_URL = 'http://127.0.0.1:8000';

interface SymbolEntry {
  name: string;
  type: 'class' | 'function';
  file: string;
  line: number;
}

interface SearchMatch {
  file: string;
  line: number;
  content: string;
}

interface GitChange {
  state: string;
  file: string;
}

export const DeveloperWorkspace = () => {
  const [symbols, setSymbols] = useState<SymbolEntry[]>([]);
  const [fileCount, setFileCount] = useState(0);
  const [totalSize, setTotalSize] = useState(0);
  const [gitBranch, setGitBranch] = useState('main');
  const [gitChanges, setGitChanges] = useState<GitChange[]>([]);
  
  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [matchCase, setMatchCase] = useState(false);
  const [useRegex, setUseRegex] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchMatch[]>([]);
  const [searching, setSearching] = useState(false);
  
  // Tab index inside Developer panel
  const [subTab, setSubTab] = useState<'search' | 'symbols' | 'git'>('search');

  const fetchWorkspaceIndex = async () => {
    try {
      const resp = await fetch(`${API_BASE_URL}/api/developer/index`);
      if (resp.ok) {
        const data = await resp.json();
        setSymbols(data.symbols || []);
        setFileCount(data.file_count || 0);
        setTotalSize(data.total_size_bytes || 0);
      }
    } catch (err) {
      console.error('Failed to index project:', err);
    }
  };

  const fetchGitStatus = async () => {
    try {
      const resp = await fetch(`${API_BASE_URL}/api/developer/git`);
      if (resp.ok) {
        const data = await resp.json();
        setGitBranch(data.branch || 'main');
        setGitChanges(data.changes || []);
      }
    } catch (err) {
      console.error('Failed to query git status:', err);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const resp = await fetch(`${API_BASE_URL}/api/developer/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: searchQuery,
          match_case: matchCase,
          use_regex: useRegex
        })
      });
      if (resp.ok) {
        const data = await resp.json();
        setSearchResults(data.results || []);
      }
    } catch (err) {
      console.error('Failed to run code grep:', err);
    } finally {
      setSearching(false);
    }
  };

  useEffect(() => {
    fetchWorkspaceIndex();
    fetchGitStatus();
  }, []);

  return (
    <div className="glass-panel p-6 rounded-2xl flex flex-col gap-6 overflow-hidden h-full flex-1">
      {/* Header controls */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <Code2 className="text-prime-cyan animate-pulse" size={20} />
          <span className="text-sm font-mono font-bold tracking-widest text-white">DEVELOPER Cockpit</span>
        </div>
        
        <div className="flex gap-2">
          {(['search', 'symbols', 'git'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setSubTab(tab)}
              className={`px-3 py-1 rounded-lg text-[10px] font-mono font-bold uppercase transition-all ${
                subTab === tab
                  ? 'bg-prime-cyan/15 text-prime-cyan border border-prime-cyan/30'
                  : 'text-slate-400 hover:text-white border border-transparent'
              }`}
            >
              {tab === 'git' ? 'GIT STAGE' : tab === 'search' ? 'CODE SEARCH' : 'AST SYMBOLS'}
            </button>
          ))}
          <button 
            onClick={() => { fetchWorkspaceIndex(); fetchGitStatus(); }}
            className="p-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition-colors"
            title="Refresh workspace index"
          >
            <RefreshCw size={12} />
          </button>
        </div>
      </div>

      {/* Dynamic Tab Body */}
      <div className="flex-1 overflow-y-auto pr-1">
        {subTab === 'search' && (
          <div className="flex flex-col gap-4">
            <form onSubmit={handleSearch} className="flex gap-3">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search code files... e.g. class TaskRecord"
                className="flex-1 bg-slate-950/80 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white font-mono focus:border-prime-cyan outline-none"
              />
              <button
                type="submit"
                disabled={searching}
                className="bg-prime-cyan text-slate-950 font-mono font-bold text-[10px] py-2 px-4 rounded-lg flex items-center gap-1.5 hover:bg-white transition-all shadow-[0_0_15px_rgba(0,240,255,0.2)]"
              >
                <Search size={12} /> {searching ? 'SEARCHING...' : 'GREP'}
              </button>
            </form>

            {/* Filter checkboxes */}
            <div className="flex gap-4 font-mono text-[9px] text-slate-500">
              <label className="flex items-center gap-1.5 cursor-pointer hover:text-slate-300">
                <input
                  type="checkbox"
                  checked={matchCase}
                  onChange={(e) => setMatchCase(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-800 text-prime-cyan focus:ring-0"
                />
                MATCH CASE
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer hover:text-slate-300">
                <input
                  type="checkbox"
                  checked={useRegex}
                  onChange={(e) => setUseRegex(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-800 text-prime-cyan focus:ring-0"
                />
                REGULAR EXPRESSION (REGEX)
              </label>
            </div>

            {/* Search Matches List */}
            <div className="flex flex-col gap-2 mt-2">
              <span className="text-[8px] font-mono text-slate-500 uppercase tracking-wider font-bold">Search Matches ({searchResults.length})</span>
              <div className="flex flex-col gap-1.5 max-h-[280px] overflow-y-auto">
                {searchResults.map((match, idx) => (
                  <div key={idx} className="bg-slate-900/40 border border-slate-850 p-2.5 rounded-xl flex flex-col gap-1">
                    <div className="flex items-center justify-between text-[9px] font-mono">
                      <span className="text-slate-400 flex items-center gap-1"><FileCode size={10} className="text-prime-cyan" /> {match.file}</span>
                      <span className="text-slate-500 flex items-center gap-0.5"><Hash size={10} /> Line {match.line}</span>
                    </div>
                    <pre className="text-[10px] font-mono text-slate-200 bg-black/30 p-2 rounded border border-slate-950 overflow-x-auto">
                      <code>{match.content}</code>
                    </pre>
                  </div>
                ))}
                {searchResults.length === 0 && searchQuery && !searching && (
                  <div className="text-slate-500 text-center font-mono text-[10px] py-6">No matching code files located.</div>
                )}
              </div>
            </div>
          </div>
        )}

        {subTab === 'symbols' && (
          <div className="flex flex-col gap-4">
            {/* Project counts summary card */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-slate-900/50 border border-slate-850 p-4 rounded-xl flex flex-col gap-1">
                <span className="text-slate-500 text-[8px] font-mono uppercase font-bold">Total Workspace Modules</span>
                <span className="text-xl font-mono font-bold text-white">{fileCount}</span>
              </div>
              <div className="bg-slate-900/50 border border-slate-850 p-4 rounded-xl flex flex-col gap-1">
                <span className="text-slate-500 text-[8px] font-mono uppercase font-bold">Symbols Indexed</span>
                <span className="text-xl font-mono font-bold text-prime-cyan">{symbols.length}</span>
              </div>
              <div className="bg-slate-900/50 border border-slate-850 p-4 rounded-xl flex flex-col gap-1">
                <span className="text-slate-500 text-[8px] font-mono uppercase font-bold">Index Size</span>
                <span className="text-xl font-mono font-bold text-emerald-400">
                  {Math.round(totalSize / 1024)} KB
                </span>
              </div>
            </div>

            {/* Symbols Table list */}
            <div className="flex flex-col gap-2 mt-2">
              <span className="text-[8px] font-mono text-slate-500 uppercase tracking-wider font-bold">AST Parsed Symbols</span>
              <div className="border border-slate-850 rounded-xl overflow-hidden max-h-[280px] overflow-y-auto">
                <table className="w-full text-left font-mono text-[10px]">
                  <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-850">
                    <tr>
                      <th className="p-2.5">SYMBOL NAME</th>
                      <th className="p-2.5">TYPE</th>
                      <th className="p-2.5">FILE PATH</th>
                      <th className="p-2.5">LINE</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-850 text-slate-300">
                    {symbols.map((sym, idx) => (
                      <tr key={idx} className="hover:bg-slate-900/20">
                        <td className="p-2.5 font-bold text-prime-cyan">{sym.name}</td>
                        <td className="p-2.5">
                          <span className={`px-1.5 py-0.5 rounded text-[8px] font-bold ${
                            sym.type === 'class' ? 'bg-prime-purple/10 text-prime-purple border border-prime-purple/20' : 'bg-slate-800 text-slate-400'
                          }`}>
                            {sym.type.toUpperCase()}
                          </span>
                        </td>
                        <td className="p-2.5 truncate max-w-[200px]">{sym.file}</td>
                        <td className="p-2.5 text-slate-500">{sym.line}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {subTab === 'git' && (
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Left side form */}
            <div className="w-full lg:w-1/3 flex flex-col gap-4">
              <div className="bg-slate-900/40 border border-slate-850 p-4 rounded-xl flex flex-col gap-3">
                <span className="text-slate-500 text-[8px] font-mono uppercase tracking-wider font-bold">ACTIVE BRANCH</span>
                <div className="flex items-center gap-2">
                  <GitBranch className="text-prime-cyan" size={16} />
                  <span className="text-xs font-mono font-bold text-white uppercase">{gitBranch}</span>
                </div>
              </div>
            </div>

            {/* Right side changes list */}
            <div className="flex-1 flex flex-col gap-3">
              <span className="text-[8px] font-mono text-slate-500 uppercase tracking-wider font-bold">UNCOMMITTED STAGED/UNSTAGED CHANGES ({gitChanges.length})</span>
              <div className="flex flex-col gap-1.5 max-h-[300px] overflow-y-auto">
                {gitChanges.map((change, idx) => (
                  <div key={idx} className="bg-slate-900/40 border border-slate-850 p-3 rounded-xl flex items-center justify-between">
                    <span className="text-[10px] font-mono text-slate-300">{change.file}</span>
                    <span className={`text-[8px] font-mono font-bold px-2 py-0.5 rounded ${
                      change.state === 'M' 
                        ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' 
                        : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    }`}>
                      {change.state === 'M' ? 'MODIFIED' : 'UNTRACKED'}
                    </span>
                  </div>
                ))}
                {gitChanges.length === 0 && (
                  <div className="text-slate-500 text-center font-mono text-[10px] py-10">No uncommitted files detected. Workspace is clean.</div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
