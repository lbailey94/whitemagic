"use client";

import { useEffect, useState } from "react";

export default function OfflineFallback() {
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    setIsOnline(navigator.onLine);

    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0a1a] flex items-center justify-center p-4">
      <div className="max-w-md w-full text-center">
        {/* Logo */}
        <div className="mb-8">
          <div className="w-24 h-24 mx-auto rounded-full bg-gradient-to-br from-purple-600 to-cyan-500 flex items-center justify-center">
            <svg
              viewBox="0 0 100 100"
              className="w-16 h-16"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <circle cx="50" cy="50" r="40" stroke="#7c3aed" strokeWidth="2" opacity="0.5" />
              <circle cx="50" cy="50" r="25" stroke="#06b6d4" strokeWidth="2" opacity="0.4" />
              <circle cx="50" cy="50" r="10" fill="#f59e0b" />
              <polygon
                points="50,15 58,40 85,40 63,55 72,80 50,65 28,80 37,55 15,40 42,40"
                fill="#7c3aed"
                opacity="0.8"
              />
            </svg>
          </div>
        </div>

        {/* Title */}
        <h1 className="text-3xl font-bold text-white mb-2">WhiteMagic</h1>
        <p className="text-gray-400 mb-8">Cognitive Operating System</p>

        {/* Status */}
        {isOnline ? (
          <div className="bg-green-900/30 border border-green-700/50 rounded-lg p-4 mb-6">
            <p className="text-green-400">You are online. Loading application...</p>
          </div>
        ) : (
          <div className="bg-yellow-900/30 border border-yellow-700/50 rounded-lg p-4 mb-6">
            <p className="text-yellow-400">You are offline. Some features may be unavailable.</p>
            <p className="text-yellow-300/70 text-sm mt-2">
              Cached memories and dashboard data are still accessible.
            </p>
          </div>
        )}

        {/* Quick Actions */}
        <div className="grid grid-cols-2 gap-3 mb-8">
          <button
            onClick={() => window.location.href = "/dashboard"}
            className="bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/30 rounded-lg p-3 text-purple-300 transition-colors"
          >
            <div className="text-lg font-medium">Dashboard</div>
            <div className="text-xs text-purple-400/70">View memories</div>
          </button>
          <button
            onClick={() => window.location.href = "/"}
            className="bg-cyan-600/20 hover:bg-cyan-600/30 border border-cyan-500/30 rounded-lg p-3 text-cyan-300 transition-colors"
          >
            <div className="text-lg font-medium">Home</div>
            <div className="text-xs text-cyan-400/70">Main site</div>
          </button>
        </div>

        {/* System Info */}
        <div className="text-xs text-gray-500 space-y-1">
          <p>WhiteMagic v22.2.0</p>
          <p>484 tools · 28 Ganas · 5D Holographic Memory</p>
        </div>
      </div>
    </div>
  );
}
