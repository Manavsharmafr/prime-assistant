import { useState } from 'react';
import { FileText, Link2, Search, ExternalLink, Calendar } from 'lucide-react';

export interface ResearchReport {
  id: string;
  title: string;
  summary: string;
  content: string;
  sources: { title: string; url: string }[];
  timestamp: string;
}

interface ResearchProps {
  reports: ResearchReport[];
  activeReportId: string | null;
  onSelectReport: (id: string) => void;
}

export const Research = ({
  reports,
  activeReportId,
  onSelectReport
}: ResearchProps) => {
  const [tab, setTab] = useState<'report' | 'sources'>('report');
  
  const activeReport = reports.find(r => r.id === activeReportId) || reports[0];

  return (
    <div className="glass-panel rounded-2xl border border-slate-800/80 flex flex-col h-[530px] overflow-hidden">
      {/* Title Bar */}
      <div className="bg-slate-950/60 px-4 py-3 border-b border-slate-800/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Search size={16} className="text-prime-purple" />
          <span className="text-sm font-bold tracking-wider text-slate-300 font-mono">RESEARCH CENTER</span>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Reports Directory (Left Sidebar) */}
        <div className="w-1/3 border-r border-slate-800/60 bg-black/10 overflow-y-auto flex flex-col p-3 gap-2">
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest px-2 pb-1 block border-b border-slate-800/40">Reports Log</span>
          {reports.length === 0 ? (
            <div className="text-slate-600 text-xs italic text-center p-6 mt-8 font-mono">
              No research runs compiled yet
            </div>
          ) : (
            reports.map((report) => (
              <button
                key={report.id}
                onClick={() => onSelectReport(report.id)}
                className={`w-full text-left p-3 rounded-xl border transition-all duration-200 flex flex-col gap-1.5 ${
                  (activeReport && activeReport.id === report.id)
                    ? 'bg-prime-purple/10 border-prime-purple/35 text-white shadow-[0_0_12px_rgba(189,0,255,0.05)]'
                    : 'bg-slate-900/30 border-transparent hover:bg-slate-900/60 hover:border-slate-800 text-slate-400'
                }`}
              >
                <div className="flex items-start gap-2">
                  <FileText size={14} className={activeReport?.id === report.id ? 'text-prime-purple' : 'text-slate-500'} />
                  <span className="text-xs font-semibold line-clamp-1 flex-1 font-sans">{report.title}</span>
                </div>
                <span className="text-[10px] font-mono text-slate-500 flex items-center gap-1.5 pl-5">
                  <Calendar size={10} />
                  {report.timestamp}
                </span>
              </button>
            ))
          )}
        </div>

        {/* Report Content Panel (Right Detail View) */}
        <div className="flex-1 flex flex-col overflow-hidden bg-black/20">
          {activeReport ? (
            <>
              {/* Tab selector */}
              <div className="flex border-b border-slate-800/60 bg-slate-950/30">
                <button
                  onClick={() => setTab('report')}
                  className={`px-5 py-3 text-xs font-mono font-bold tracking-wider border-b-2 transition-all ${
                    tab === 'report'
                      ? 'border-prime-purple text-white bg-prime-purple/5'
                      : 'border-transparent text-slate-400 hover:text-white'
                  }`}
                >
                  RESEARCH REPORT
                </button>
                <button
                  onClick={() => setTab('sources')}
                  className={`px-5 py-3 text-xs font-mono font-bold tracking-wider border-b-2 transition-all ${
                    tab === 'sources'
                      ? 'border-prime-purple text-white bg-prime-purple/5'
                      : 'border-transparent text-slate-400 hover:text-white'
                  }`}
                >
                  VERIFIED SOURCES ({activeReport.sources?.length ?? 0})
                </button>
              </div>

              {/* View Content */}
              <div className="flex-1 p-5 overflow-y-auto font-sans leading-relaxed text-sm text-slate-300">
                {tab === 'report' ? (
                  <div className="space-y-4">
                    <h2 className="text-lg font-bold text-white tracking-tight border-b border-slate-800/50 pb-2">
                      {activeReport.title}
                    </h2>
                    
                    <div className="bg-prime-purple/5 border border-prime-purple/20 p-4 rounded-xl text-slate-300 text-xs italic">
                      <span className="font-bold text-prime-purple font-mono block not-italic mb-1 uppercase tracking-wider text-[10px]">EXECUTIVE SUMMARY</span>
                      {activeReport.summary}
                    </div>

                    <div className="prose prose-invert max-w-none text-xs leading-relaxed space-y-3 font-mono whitespace-pre-wrap">
                      {activeReport.content}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest block pb-1 border-b border-slate-800/40 mb-3">Crawled Web References</span>
                    {activeReport.sources.length === 0 ? (
                      <div className="text-slate-500 text-xs italic">No external sources cited.</div>
                    ) : (
                      activeReport.sources.map((source, idx) => (
                        <a
                          key={idx}
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center justify-between p-3 rounded-xl border border-slate-800/50 bg-slate-900/20 hover:bg-slate-900/50 hover:border-slate-700/80 group transition-all"
                        >
                          <div className="flex items-center gap-2.5">
                            <div className="p-1.5 rounded bg-slate-800 text-slate-400 group-hover:text-prime-purple group-hover:bg-prime-purple/10 transition-colors">
                              <Link2 size={14} />
                            </div>
                            <div className="flex flex-col gap-0.5">
                              <span className="text-xs font-semibold text-slate-300 group-hover:text-white transition-colors">{source.title}</span>
                              <span className="text-[10px] font-mono text-slate-500 max-w-[280px] truncate">{source.url}</span>
                            </div>
                          </div>
                          <ExternalLink size={12} className="text-slate-600 group-hover:text-slate-400 transition-colors" />
                        </a>
                      ))
                    )}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
              <FileText size={32} className="text-slate-700 mb-2" />
              <div className="text-slate-500 text-sm font-semibold">No Research Loaded</div>
              <div className="text-slate-600 text-xs mt-1 max-w-[240px]">
                Tell Prime to search the web or compile research folders to populate this space.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
