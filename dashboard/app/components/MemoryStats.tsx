'use client';

interface MemoryStatsProps {
  stats: {
    totalMemories?: number;
    shortTerm?: number;
    longTerm?: number;
    topTags?: Array<{ tag: string; count: number }>;
  };
}

export default function MemoryStats({ stats }: MemoryStatsProps) {
  return (
    <div className="space-y-6">
      {/* Count Cards */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Total" value={stats.totalMemories || 0} color="text-cyan-400" />
        <StatCard label="Short-Term" value={stats.shortTerm || 0} color="text-green-400" />
        <StatCard label="Long-Term" value={stats.longTerm || 0} color="text-blue-400" />
      </div>

      {/* Top Tags */}
      <div>
        <h3 className="text-sm font-semibold text-gray-400 mb-2">Top Tags</h3>
        <div className="space-y-2">
          {stats.topTags && stats.topTags.length > 0 ? (
            stats.topTags.slice(0, 5).map(({ tag, count }) => (
              <div key={tag} className="flex items-center justify-between">
                <span className="text-sm">{tag}</span>
                <div className="flex items-center space-x-2">
                  <div className="w-32 h-2 bg-gray-700 rounded">
                    <div
                      className="h-full bg-cyan-500 rounded"
                      style={{ width: `${(count / (stats.topTags?.[0]?.count || 1)) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-400">{count}</span>
                </div>
              </div>
            ))
          ) : (
            <p className="text-gray-500 text-sm">No tags yet</p>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="bg-gray-700 rounded p-3 text-center">
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-gray-400 mt-1">{label}</div>
    </div>
  );
}
