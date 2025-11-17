'use client';

interface Session {
  id: string;
  name: string;
  status: string;
  timestamp: string;
}

export default function Timeline({ sessions }: { sessions: Session[] }) {
  const statusColors = {
    active: 'bg-green-500',
    paused: 'bg-yellow-500',
    completed: 'bg-blue-500',
    cancelled: 'bg-red-500',
  };

  return (
    <div className="space-y-4 max-h-64 overflow-y-auto">
      {sessions.length === 0 ? (
        <p className="text-gray-500 text-center py-8">No sessions yet</p>
      ) : (
        sessions.map(session => (
          <div key={session.id} className="flex items-center space-x-4 border-l-4 border-cyan-500 pl-4 py-2">
            <div className={`w-3 h-3 rounded-full ${statusColors[session.status as keyof typeof statusColors] || 'bg-gray-500'}`} />
            <div className="flex-1">
              <h3 className="font-semibold">{session.name}</h3>
              <p className="text-sm text-gray-400">{session.timestamp}</p>
            </div>
            <span className="text-xs px-2 py-1 rounded bg-gray-700">{session.status}</span>
          </div>
        ))
      )}
    </div>
  );
}
