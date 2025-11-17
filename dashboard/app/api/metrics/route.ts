import { NextResponse } from 'next/server';

export async function GET() {
  // Mock data for Phase 1
  // Phase 2: Connect to real WhiteMagic API
  
  const mockData = {
    currentPhase: 'FIRE', // WOOD, FIRE, EARTH, METAL, WATER
    tokenData: [
      { timestamp: '10:00', used: 10000, total: 200000 },
      { timestamp: '10:30', used: 50000, total: 200000 },
      { timestamp: '11:00', used: 90000, total: 200000 },
      { timestamp: '11:30', used: 115000, total: 200000 },
    ],
    sessions: [
      { id: '1', name: 'v2.2.7 Week 1', status: 'completed', timestamp: '2h ago' },
      { id: '2', name: 'v2.2.7 Week 2', status: 'active', timestamp: 'Now' },
    ],
    memoryStats: {
      totalMemories: 82,
      shortTerm: 24,
      longTerm: 58,
      topTags: [
        { tag: 'v2.2.7', count: 15 },
        { tag: 'parallel', count: 12 },
        { tag: 'sessions', count: 8 },
        { tag: 'planning', count: 6 },
        { tag: 'complete', count: 5 },
      ],
    },
  };

  return NextResponse.json(mockData);
}
