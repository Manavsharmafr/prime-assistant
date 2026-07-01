import { useState, useEffect } from 'react';
import { 
  Puzzle, 
  Settings, 
  CheckCircle, 
  AlertTriangle, 
  Power, 
  Link2, 
  Plus, 
  Terminal, 
  Save
} from 'lucide-react';

const API_BASE_URL = 'http://127.0.0.1:8000';

interface Plugin {
  id: string;
  name: string;
  description: string;
  version: string;
  enabled: boolean;
  health_status: 'healthy' | 'degraded' | 'offline';
  required_permissions: string[];
  actions: string[];
  config: Record<string, any>;
}

interface MCPServer {
  id: string;
  name: string;
  url: string;
  status: string;
  tools: Array<{ name: string; description: string; parameters: Record<string, any> }>;
}

export const PluginManagerDashboard = () => {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [mcpServers, setMcpServers] = useState<MCPServer[]>([]);
  const [selectedPlugin, setSelectedPlugin] = useState<Plugin | null>(null);
  const [editConfig, setEditConfig] = useState<string>('');
  
  // MCP Registration State
  const [mcpName, setMcpName] = useState('');
  const [mcpUrl, setMcpUrl] = useState('');
  
  // Tab within Dashboard
  const [subTab, setSubTab] = useState<'manager' | 'accounts' | 'mcp' | 'health'>('manager');

  const fetchPluginsAndMCP = async () => {
    try {
      const pResp = await fetch(`${API_BASE_URL}/api/plugins`);
      if (pResp.ok) {
        setPlugins(await pResp.json());
      }
      const mResp = await fetch(`${API_BASE_URL}/api/plugins/mcp`);
      if (mResp.ok) {
        setMcpServers(await mResp.json());
      }
    } catch (err) {
      console.error('Failed to load plugin data:', err);
    }
  };

  useEffect(() => {
    fetchPluginsAndMCP();
  }, []);

  const handleTogglePlugin = async (id: string, currentlyEnabled: boolean) => {
    const action = currentlyEnabled ? 'disable' : 'enable';
    try {
      const resp = await fetch(`${API_BASE_URL}/api/plugins/${id}/${action}`, {
        method: 'POST'
      });
      if (resp.ok) {
        fetchPluginsAndMCP();
      }
    } catch (err) {
      console.error(`Failed to toggle plugin ${id}:`, err);
    }
  };

  const handleSaveConfig = async () => {
    if (!selectedPlugin) return;
    try {
      const parsedConfig = JSON.parse(editConfig);
      const resp = await fetch(`${API_BASE_URL}/api/plugins/${selectedPlugin.id}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: parsedConfig })
      });
      if (resp.ok) {
        setSelectedPlugin(null);
        fetchPluginsAndMCP();
      }
    } catch (err) {
      alert('Invalid JSON config format.');
    }
  };

  const handleRegisterMCPServer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mcpName || !mcpUrl) return;
    try {
      const resp = await fetch(`${API_BASE_URL}/api/plugins/mcp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: mcpName, url: mcpUrl })
      });
      if (resp.ok) {
        setMcpName('');
        setMcpUrl('');
        fetchPluginsAndMCP();
      }
    } catch (err) {
      console.error('Failed to register MCP server:', err);
    }
  };

  const getHealthBadge = (status: string) => {
    switch (status) {
      case 'healthy':
        return (
          <span className="flex items-center gap-1 text-[10px] text-emerald-400 font-mono bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded">
            <CheckCircle size={10} /> HEALTHY
          </span>
        );
      case 'degraded':
        return (
          <span className="flex items-center gap-1 text-[10px] text-amber-400 font-mono bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded">
            <AlertTriangle size={10} /> DEGRADED
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 text-[10px] text-rose-400 font-mono bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 rounded">
            <AlertTriangle size={10} /> OFFLINE
          </span>
        );
    }
  };

  return (
    <div className="glass-panel p-6 rounded-2xl flex flex-col gap-6 overflow-hidden h-full flex-1">
      {/* Tab Navigation header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <Puzzle className="text-prime-cyan" size={20} />
          <span className="text-sm font-mono font-bold tracking-widest text-white">EXTENSIONS & PLUGINS</span>
        </div>
        <div className="flex gap-2">
          {(['manager', 'accounts', 'mcp', 'health'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setSubTab(tab)}
              className={`px-3 py-1 rounded-lg text-[10px] font-mono font-bold uppercase transition-all ${
                subTab === tab
                  ? 'bg-prime-cyan/15 text-prime-cyan border border-prime-cyan/30'
                  : 'text-slate-400 hover:text-white border border-transparent'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Subtab content details */}
      <div className="flex-1 overflow-y-auto pr-1">
        {subTab === 'manager' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {plugins.map((plugin) => (
              <div key={plugin.id} className="bg-slate-900/50 border border-slate-850 p-4 rounded-xl flex flex-col justify-between gap-4 transition-all hover:border-slate-800/80">
                <div className="flex flex-col gap-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="text-xs font-mono font-bold text-white tracking-wide">{plugin.name}</h4>
                      <span className="text-[9px] text-slate-500 font-mono">v{plugin.version}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {getHealthBadge(plugin.health_status)}
                      <button
                        onClick={() => handleTogglePlugin(plugin.id, plugin.enabled)}
                        className={`p-1.5 rounded-lg border transition-all ${
                          plugin.enabled
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}
                        title={plugin.enabled ? "Disable Plugin" : "Enable Plugin"}
                      >
                        <Power size={12} />
                      </button>
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">{plugin.description}</p>
                </div>

                <div className="border-t border-slate-850 pt-3 flex items-center justify-between">
                  <button
                    onClick={() => {
                      setSelectedPlugin(plugin);
                      setEditConfig(JSON.stringify(plugin.config, null, 2));
                    }}
                    className="flex items-center gap-1.5 text-[10px] font-mono font-bold text-prime-cyan hover:text-white transition-colors"
                  >
                    <Settings size={12} /> CONFIGURE KEYS
                  </button>
                  <span className="text-[9px] text-slate-500 font-mono">
                    {plugin.actions.length} ACTIONS
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {subTab === 'accounts' && (
          <div className="flex flex-col gap-4">
            <h3 className="text-xs font-mono font-bold text-white tracking-wide border-b border-slate-850 pb-2">CONNECTED OAUTH ACCOUNTS</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                { name: 'Google Workspace', id: 'google', connected: true, scope: 'Gmail, Docs, Drive' },
                { name: 'GitHub Integration', id: 'github_oauth', connected: false, scope: 'Repo Read/Write' },
                { name: 'LinkedIn Professional', id: 'linkedin_oauth', connected: false, scope: 'Profile Analytics' },
                { name: 'Notion Sync', id: 'notion_oauth', connected: true, scope: 'Workspace Read/Write' },
              ].map((acc) => (
                <div key={acc.id} className="bg-slate-900/50 border border-slate-850 p-4 rounded-xl flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Link2 className={acc.connected ? 'text-prime-cyan' : 'text-slate-500'} size={20} />
                    <div>
                      <h4 className="text-xs font-mono font-bold text-slate-200">{acc.name}</h4>
                      <p className="text-[9px] text-slate-500 font-mono mt-0.5">{acc.scope}</p>
                    </div>
                  </div>
                  <button
                    className={`px-3 py-1.5 rounded-lg text-[9px] font-mono font-bold transition-all ${
                      acc.connected
                        ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/25'
                        : 'bg-prime-cyan/15 text-prime-cyan border border-prime-cyan/30 hover:bg-prime-cyan/30'
                    }`}
                  >
                    {acc.connected ? 'DISCONNECT' : 'AUTHORIZE'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {subTab === 'mcp' && (
          <div className="flex flex-col lg:flex-row gap-6 h-full">
            {/* Left side registration */}
            <div className="w-full lg:w-1/3 flex flex-col gap-4">
              <h3 className="text-xs font-mono font-bold text-white tracking-wide border-b border-slate-850 pb-2">REGISTER MCP SERVER</h3>
              <form onSubmit={handleRegisterMCPServer} className="flex flex-col gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-[9px] font-mono text-slate-500 font-bold uppercase">Server Name</label>
                  <input
                    type="text"
                    value={mcpName}
                    onChange={(e) => setMcpName(e.target.value)}
                    placeholder="e.g. Postgres DB MCP"
                    className="bg-slate-950/80 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white font-mono focus:border-prime-cyan outline-none"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-[9px] font-mono text-slate-500 font-bold uppercase">Endpoint URL</label>
                  <input
                    type="text"
                    value={mcpUrl}
                    onChange={(e) => setMcpUrl(e.target.value)}
                    placeholder="e.g. http://127.0.0.1:9091"
                    className="bg-slate-950/80 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white font-mono focus:border-prime-cyan outline-none"
                  />
                </div>
                <button
                  type="submit"
                  className="bg-prime-cyan text-slate-950 font-mono font-bold text-[10px] py-2 px-3 rounded-lg flex items-center justify-center gap-1.5 hover:bg-white transition-all shadow-[0_0_15px_rgba(0,240,255,0.2)]"
                >
                  <Plus size={14} /> CONNECT SERVER
                </button>
              </form>
            </div>

            {/* Right side connection lists */}
            <div className="flex-1 flex flex-col gap-4">
              <h3 className="text-xs font-mono font-bold text-white tracking-wide border-b border-slate-850 pb-2">CONNECTED SERVER NODES</h3>
              <div className="flex flex-col gap-4 overflow-y-auto">
                {mcpServers.map((srv) => (
                  <div key={srv.id} className="bg-slate-900/40 border border-slate-850 p-4 rounded-xl flex flex-col gap-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-xs font-mono font-bold text-white">{srv.name}</h4>
                        <span className="text-[9px] text-slate-500 font-mono">{srv.url}</span>
                      </div>
                      <span className="text-[9px] text-emerald-400 font-mono bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded">
                        CONNECTED
                      </span>
                    </div>

                    <div className="border-t border-slate-850 pt-2 flex flex-col gap-1.5">
                      <span className="text-[8px] font-mono text-slate-500 uppercase tracking-wider font-bold">Discovered MCP Tools ({srv.tools.length})</span>
                      <div className="flex flex-wrap gap-1.5">
                        {srv.tools.map((tool) => (
                          <div key={tool.name} className="bg-black/30 border border-slate-850 px-2.5 py-1 rounded-lg flex flex-col gap-0.5 max-w-[200px]">
                            <span className="text-[9px] font-mono font-bold text-prime-cyan">{tool.name}</span>
                            <span className="text-[8px] text-slate-400 line-clamp-1">{tool.description}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {subTab === 'health' && (
          <div className="flex flex-col gap-4">
            <h3 className="text-xs font-mono font-bold text-white tracking-wide border-b border-slate-850 pb-2">PLUGIN SYSTEM METRICS</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-slate-900/50 border border-slate-850 p-4 rounded-xl flex flex-col gap-1">
                <span className="text-slate-500 text-[8px] font-mono uppercase font-bold">Total Plugins Loaded</span>
                <span className="text-2xl font-mono font-bold text-white">{plugins.length}</span>
              </div>
              <div className="bg-slate-900/50 border border-slate-850 p-4 rounded-xl flex flex-col gap-1">
                <span className="text-slate-500 text-[8px] font-mono uppercase font-bold">Active Integrations</span>
                <span className="text-2xl font-mono font-bold text-prime-cyan">
                  {plugins.filter(p => p.enabled).length}
                </span>
              </div>
              <div className="bg-slate-900/50 border border-slate-850 p-4 rounded-xl flex flex-col gap-1">
                <span className="text-slate-500 text-[8px] font-mono uppercase font-bold">System Health Score</span>
                <span className="text-2xl font-mono font-bold text-emerald-400">100%</span>
              </div>
            </div>

            <div className="mt-2 bg-slate-900/50 border border-slate-850 rounded-xl p-4 flex flex-col gap-2.5">
              <span className="text-slate-400 font-mono text-[10px] font-bold flex items-center gap-1.5">
                <Terminal size={12} className="text-prime-cyan" /> EXTENSION EVENT LOGGER
              </span>
              <div className="bg-black/30 border border-slate-850 p-3 rounded-lg max-h-[160px] overflow-y-auto font-mono text-[9px] text-slate-500 flex flex-col gap-1">
                <div>[08:41:50] [SYSTEM] plugin manager framework loaded.</div>
                <div>[08:41:51] [SYSTEM] loaded default plugin configuration records.</div>
                <div>[08:41:51] [GITHUB] initialized GitHub actions in mock mode.</div>
                <div>[08:41:52] [NOTION] connection checked. status=healthy.</div>
                <div>[08:41:52] [MCP] Postgres Database Server tools synced successfully.</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Edit Config Modal */}
      {selectedPlugin && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel max-w-md w-full p-6 rounded-2xl flex flex-col gap-4 border border-slate-800">
            <div>
              <h3 className="text-xs font-mono font-bold text-white tracking-wide">CONFIGURE {selectedPlugin.name.toUpperCase()}</h3>
              <p className="text-[10px] text-slate-500 font-mono mt-0.5">Edit keys, tokens, and custom settings as JSON payload.</p>
            </div>
            
            <textarea
              value={editConfig}
              onChange={(e) => setEditConfig(e.target.value)}
              className="bg-slate-950/80 border border-slate-800 rounded-lg p-3 text-[10px] text-slate-200 font-mono h-40 focus:border-prime-cyan outline-none"
            />

            <div className="flex gap-3 justify-end mt-2">
              <button
                onClick={() => setSelectedPlugin(null)}
                className="px-4 py-2 border border-slate-800 text-[10px] font-mono font-bold text-slate-400 rounded-lg hover:text-white transition-colors"
              >
                CANCEL
              </button>
              <button
                onClick={handleSaveConfig}
                className="bg-prime-cyan text-slate-950 font-mono font-bold text-[10px] py-2 px-4 rounded-lg flex items-center gap-1.5 hover:bg-white transition-all shadow-[0_0_15px_rgba(0,240,255,0.2)]"
              >
                <Save size={12} /> SAVE CONFIG
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
