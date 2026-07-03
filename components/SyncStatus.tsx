/**
 * Sync Status — Shows real-time sync state
 */

"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { getSyncClient, type SyncStats } from "@/lib/ws-sync";
import { Wifi, WifiOff, RefreshCw, AlertCircle } from "lucide-react";

export function SyncStatus() {
  const { user } = useAuth();
  const [stats, setStats] = useState<SyncStats>({
    connected: false,
    lastSync: null,
    pendingOps: 0,
    receivedOps: 0,
    conflicts: 0,
  });

  useEffect(() => {
    if (!user) return;

    const client = getSyncClient(user.id);
    client.onStatsChange((newStats) => setStats(newStats));
    client.connect();

    return () => {
      client.disconnect();
    };
  }, [user?.id]);

  if (!user) return null;

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-gray-800 text-xs">
      {stats.connected ? (
        <>
          <Wifi className="w-3 h-3 text-green-400" />
          <span className="text-green-400">Synced</span>
        </>
      ) : (
        <>
          <WifiOff className="w-3 h-3 text-yellow-400" />
          <span className="text-yellow-400">Offline</span>
        </>
      )}

      {stats.pendingOps > 0 && (
        <>
          <RefreshCw className="w-3 h-3 text-blue-400 animate-spin" />
          <span className="text-blue-400">{stats.pendingOps} pending</span>
        </>
      )}

      {stats.conflicts > 0 && (
        <>
          <AlertCircle className="w-3 h-3 text-red-400" />
          <span className="text-red-400">{stats.conflicts} conflicts</span>
        </>
      )}

      {stats.lastSync && (
        <span className="text-gray-500">
          Last: {stats.lastSync.toLocaleTimeString()}
        </span>
      )}
    </div>
  );
}
