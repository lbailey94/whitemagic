'use client';

import { useState, useEffect } from 'react';
import WuXingWheel from './components/WuXingWheel';
import TokenChart from './components/TokenChart';
import Timeline from './components/Timeline';
import MemoryStats from './components/MemoryStats';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch initial data
    fetchStats();

    // Refresh every 5 seconds (Phase 2: real-time)
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  async function fetchStats() {
    try {
      const response = await fetch('/api/metrics');
      const data = await response.json();
      setStats(data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="text-white text-xl">Loading WhiteMagic Dashboard...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      {/* Header */}
      <header className="mb-8">
        <h1 className="text-4xl font-bold text-cyan-400">🪄 WhiteMagic Dashboard</h1>
        <p className="text-gray-400 mt-2">Visual Analytics & Real-Time Monitoring</p>
      </header>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Wu Xing Wheel - Top Left */}
        <div className="bg-gray-800 rounded-lg p-6 shadow-xl">
          <h2 className="text-2xl font-semibold mb-4">Workflow Phase</h2>
          <WuXingWheel currentPhase={stats?.currentPhase || 'WOOD'} />
        </div>

        {/* Token Efficiency - Top Right */}
        <div className="bg-gray-800 rounded-lg p-6 shadow-xl">
          <h2 className="text-2xl font-semibold mb-4">Token Efficiency</h2>
          <TokenChart data={stats?.tokenData || []} />
        </div>

        {/* Session Timeline - Bottom Left */}
        <div className="bg-gray-800 rounded-lg p-6 shadow-xl">
          <h2 className="text-2xl font-semibold mb-4">Session Timeline</h2>
          <Timeline sessions={stats?.sessions || []} />
        </div>

        {/* Memory Stats - Bottom Right */}
        <div className="bg-gray-800 rounded-lg p-6 shadow-xl">
          <h2 className="text-2xl font-semibold mb-4">Memory Statistics</h2>
          <MemoryStats stats={stats?.memoryStats || {}} />
        </div>
      </div>

      {/* Footer */}
      <footer className="mt-8 text-center text-gray-500 text-sm">
        <p>WhiteMagic v2.2.7 | Dashboard Phase 1 | Updates every 5s</p>
      </footer>
    </div>
  );
}
