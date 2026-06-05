/**
 * Gan Ying Monitor — Real-time Resonance Event Tracking
 *
 * Ported from whitemagic-aux/whitemagic-frontend/dashboard-app/GanYingMonitor.tsx
 *
 * Displays the stream of resonance events from the Gan Ying (感应) bus:
 * - Memory events (created, recalled, consolidated)
 * - Pattern events (detected, confirmed, rejected)
 * - Garden events (activated, resonance)
 * - Emotional/virtue events (courage, truth, wonder, etc.)
 *
 * Events flow in real-time and are color-coded by type.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { useDashboardStore, type ResonanceEvent } from "@/store/dashboardStore";

// Event type color mapping
const EVENT_COLORS: Record<string, string> = {
  memory_created: "#22c55e",
  memory_recalled: "#3b82f6",
  memory_consolidated: "#a855f7",
  pattern_detected: "#eab308",
  pattern_confirmed: "#22c55e",
  pattern_rejected: "#ef4444",
  garden_activated: "#06b6d4",
  garden_resonance: "#8b5cf6",
  courage_shown: "#ef4444",
  truth_spoken: "#3b82f6",
  wonder_sparked: "#eab308",
  wisdom_integrated: "#a855f7",
  connection_deepened: "#06b6d4",
  resonance_amplified: "#8b5cf6",
  emergence_detected: "#ec4899",
  cascade_triggered: "#f97316",
  default: "#6b7280",
};

function getEventColor(eventType: string): string {
  return EVENT_COLORS[eventType] || EVENT_COLORS.default;
}

function formatEventType(eventType: string): string {
  return eventType
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function GanYingMonitor({
  maxEvents = 50,
  height = 400,
  useRealTime = false,
  apiBaseUrl = "/api/wm",
}: {
  maxEvents?: number;
  height?: number;
  useRealTime?: boolean;
  apiBaseUrl?: string;
}) {
  const { resonanceEvents, addResonanceEvent, clearResonanceEvents } = useDashboardStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (scrollRef.current && !isPaused) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [resonanceEvents, isPaused]);

  // Connect to SSE for real-time events
  useEffect(() => {
    if (!useRealTime) return;

    let eventSource: EventSource | null = null;

    try {
      eventSource = new EventSource(`${apiBaseUrl}/events/stream`);

      eventSource.onopen = () => {
        setIsConnected(true);
      };

      eventSource.addEventListener("resonance", (event) => {
        try {
          const data = JSON.parse(event.data);
          addResonanceEvent({
            event_type: data.event_type || "unknown",
            source: data.source || "sse",
            data: data.data || {},
            timestamp: data.timestamp || new Date().toISOString(),
          });
        } catch (e) {
          // Ignore parse errors
        }
      });

      eventSource.onerror = () => {
        setIsConnected(false);
        // EventSource auto-reconnects
      };
    } catch (e) {
      setIsConnected(false);
    }

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [useRealTime, apiBaseUrl, addResonanceEvent]);

  // Simulate events for demo (only when not using real-time)
  useEffect(() => {
    if (useRealTime) return;

    const eventTypes = [
      "memory_created",
      "memory_recalled",
      "pattern_detected",
      "garden_resonance",
      "courage_shown",
      "wisdom_integrated",
      "emergence_detected",
      "cascade_triggered",
    ];

    const sources = ["dream_cycle", "memory_core", "pattern_engine", "garden_joy", "gana_abundance"];

    const interval = setInterval(() => {
      if (Math.random() > 0.7) {
        const event: ResonanceEvent = {
          event_type: eventTypes[Math.floor(Math.random() * eventTypes.length)],
          source: sources[Math.floor(Math.random() * sources.length)],
          data: {
            memory_id: `mem_${Math.random().toString(36).slice(2, 10)}`,
            strength: Math.random().toFixed(3),
          },
          timestamp: new Date().toISOString(),
        };
        addResonanceEvent(event);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [useRealTime, addResonanceEvent]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-purple-500/20">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500 animate-pulse" : useRealTime ? "bg-yellow-500" : "bg-gray-500"}`} />
          <h3 className="text-sm font-medium text-white">Gan Ying (感应) Monitor</h3>
          {useRealTime && (
            <span className={`text-[10px] px-1.5 py-0.5 rounded ${isConnected ? "bg-green-500/20 text-green-400" : "bg-yellow-500/20 text-yellow-400"}`}>
              {isConnected ? "LIVE" : "CONNECTING"}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">
            {resonanceEvents.length} events
          </span>
          <button
            onClick={() => {
              clearResonanceEvents();
            }}
            className="px-2 py-1 text-xs bg-gray-500/20 hover:bg-gray-500/30 text-gray-300 rounded transition-colors"
          >
            Clear
          </button>
          <button
            onClick={() => setIsPaused(!isPaused)}
            className="px-2 py-1 text-xs bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 rounded transition-colors"
          >
            {isPaused ? "Resume" : "Pause"}
          </button>
        </div>
      </div>

      {/* Event stream */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-2 space-y-1"
        style={{ maxHeight: height - 48 }}
      >
        {resonanceEvents.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500 text-sm">
            Waiting for resonance events...
          </div>
        ) : (
          resonanceEvents.map((event, index) => {
            const color = getEventColor(event.event_type);
            return (
              <div
                key={`${event.timestamp}-${index}`}
                className="flex items-start gap-2 p-2 rounded bg-black/30 hover:bg-black/50 transition-colors text-xs"
              >
                <div
                  className="w-2 h-2 rounded-full mt-1 flex-shrink-0"
                  style={{ backgroundColor: color }}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-white truncate">
                      {formatEventType(event.event_type)}
                    </span>
                    <span className="text-gray-500">{formatTime(event.timestamp)}</span>
                  </div>
                  <div className="text-gray-400 mt-0.5">
                    Source: <span className="text-purple-400">{event.source}</span>
                  </div>
                  {event.data && Object.keys(event.data).length > 0 && (
                    <div className="text-gray-500 mt-0.5 font-mono text-[10px]">
                      {JSON.stringify(event.data).slice(0, 80)}
                      {JSON.stringify(event.data).length > 80 ? "..." : ""}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Event type legend */}
      <div className="p-2 border-t border-purple-500/20">
        <div className="flex flex-wrap gap-2">
          {Object.entries(EVENT_COLORS)
            .filter(([key]) => key !== "default")
            .slice(0, 8)
            .map(([type, color]) => (
              <div key={type} className="flex items-center gap-1">
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: color }}
                />
                <span className="text-[10px] text-gray-400">
                  {formatEventType(type)}
                </span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
