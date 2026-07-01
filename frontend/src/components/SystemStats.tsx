import type { ReactNode } from 'react';
import { Cpu, Database, HardDrive, Shield } from 'lucide-react';

interface StatItemProps {
  label: string;
  value: string | number;
  percentage: number;
  icon: ReactNode;
  color: 'cyan' | 'purple';
}

const StatItem = ({ label, value, percentage, icon, color }: StatItemProps) => {
  const isCyan = color === 'cyan';
  const progressColor = isCyan ? 'bg-prime-cyan' : 'bg-prime-purple';
  const glowColor = isCyan ? 'shadow-[0_0_10px_rgba(0,240,255,0.5)]' : 'shadow-[0_0_10px_rgba(189,0,255,0.5)]';
  const textColor = isCyan ? 'text-prime-cyan' : 'text-prime-purple';

  return (
    <div className="glass-card-interactive p-4 rounded-xl flex flex-col gap-3">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <span className={textColor}>{icon}</span>
          <span>{label}</span>
        </div>
        <span className={`text-sm font-mono font-bold ${textColor}`}>
          {value}
        </span>
      </div>
      <div className="w-full bg-slate-800/50 rounded-full h-1.5 overflow-hidden border border-slate-700/30">
        <div
          className={`h-full rounded-full transition-all duration-500 ease-out ${progressColor} ${glowColor}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

interface SystemStatsProps {
  stats: {
    cpu?: { percent: number; cores: number };
    memory?: { percent: number; used_gb: number; total_gb: number };
    disk?: { percent: number; used_gb: number; total_gb: number };
  } | null;
  securityMode: boolean;
}

export const SystemStats = ({ stats }: SystemStatsProps) => {
  const cpuPercent = stats?.cpu?.percent ?? 0;
  const memoryPercent = stats?.memory?.percent ?? 0;
  const diskPercent = stats?.disk?.percent ?? 0;

  const memoryLabel = stats?.memory 
    ? `${stats.memory.used_gb} / ${stats.memory.total_gb} GB`
    : '0 / 0 GB';
  const diskLabel = stats?.disk
    ? `${stats.disk.used_gb} / ${stats.disk.total_gb} GB`
    : '0 / 0 GB';

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-sm font-bold tracking-wider text-slate-400 uppercase font-mono px-1 flex justify-between items-center">
        <span>System Telemetry</span>
        <span className="flex items-center gap-1.5 text-xs text-prime-cyan">
          <span className="h-1.5 w-1.5 rounded-full bg-prime-cyan animate-ping" />
          Live
        </span>
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatItem
          label="CPU Utilisation"
          value={`${cpuPercent.toFixed(1)}%`}
          percentage={cpuPercent}
          icon={<Cpu size={16} />}
          color="cyan"
        />
        <StatItem
          label="Memory Usage"
          value={memoryLabel}
          percentage={memoryPercent}
          icon={<Database size={16} />}
          color="purple"
        />
        <StatItem
          label="Disk Space"
          value={diskLabel}
          percentage={diskPercent}
          icon={<HardDrive size={16} />}
          color="cyan"
        />
      </div>

      <div className="glass-card-interactive p-4 rounded-xl flex items-center justify-between border-slate-800">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/25`}>
            <Shield size={18} />
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-200">Security Gate Core</div>
            <div className="text-xs text-slate-400">Requires confirmation for operations</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20 shadow-[0_0_8px_rgba(16,185,129,0.15)]">
            ACTIVE
          </span>
        </div>
      </div>
    </div>
  );
};
