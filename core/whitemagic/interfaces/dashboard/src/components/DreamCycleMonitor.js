import React from 'react';
import { CheckCircle, AlertCircle, Clock } from 'lucide-react';

export default function DreamCycleMonitor({ data, loading }) {
  if (loading) return <div className="animate-pulse h-48 bg-gray-100 rounded-lg"></div>;
  if (!data) return null;

  const { phases, current_phase, is_master } = data;
  const currentIdx = phases.indexOf(current_phase);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${is_master ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'}`} />
          <span className="text-sm font-medium text-gray-700">
            {is_master ? 'Elixir Master Active' : 'Python Standalone'}
          </span>
        </div>
        <span className="text-xs font-mono text-gray-500 uppercase tracking-widest">
          12-Phase Cycle
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {phases.map((phase, idx) => {
          const isActive = idx === currentIdx;
          const isCompleted = idx < currentIdx;
          
          return (
            <div 
              key={phase}
              className={`p-2 rounded border text-center transition-all ${
                isActive 
                  ? 'bg-purple-50 border-purple-300 shadow-sm scale-105 z-10' 
                  : isCompleted 
                    ? 'bg-green-50 border-green-100 opacity-60' 
                    : 'bg-gray-50 border-gray-100 opacity-40'
              }`}
            >
              <div className="flex justify-center mb-1">
                {isActive ? (
                  <Clock className="w-3 h-3 text-purple-600 animate-spin-slow" />
                ) : isCompleted ? (
                  <CheckCircle className="w-3 h-3 text-green-600" />
                ) : (
                  <div className="w-3 h-3" />
                )}
              </div>
              <span className={`text-[10px] font-bold uppercase truncate block ${
                isActive ? 'text-purple-700' : 'text-gray-600'
              }`}>
                {phase}
              </span>
            </div>
          );
        })}
      </div>
      
      {isActive && (
        <div className="mt-2 text-center">
          <p className="text-xs text-purple-600 italic animate-pulse">
            Executing {current_phase} phase...
          </p>
        </div>
      )}
    </div>
  );
}
