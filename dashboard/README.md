# WhiteMagic Dashboard

Visual analytics and real-time monitoring for WhiteMagic memory system.

## Features

### Phase 1 (v2.2.7) ✅
- Wu Xing Wheel - Workflow phase visualization
- Token Efficiency Chart - Usage over time
- Session Timeline - Activity log
- Memory Stats - Count, types, tags

### Phase 2 (v2.2.8+)
- Real-time monitoring
- Concept graph (force-directed)
- Advanced metrics
- Interactive consolidation

## Tech Stack

- **Framework**: Next.js 14
- **Visualization**: D3.js
- **Styling**: TailwindCSS
- **Components**: Custom + lucide-react icons
- **TypeScript**: Full type safety

## Development

```bash
cd dashboard
npm install
npm run dev
```

Visit http://localhost:3000

## API Integration

Dashboard connects to WhiteMagic API at `http://localhost:8000` by default.

Configure via environment variables:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Architecture

```
dashboard/
├── app/
│   ├── page.tsx              # Main dashboard
│   ├── components/
│   │   ├── WuXingWheel.tsx   # Phase wheel visualization
│   │   ├── TokenChart.tsx    # Token efficiency chart
│   │   ├── Timeline.tsx      # Session timeline
│   │   └── MemoryStats.tsx   # Memory statistics
│   └── api/
│       └── metrics/route.ts  # API proxy
├── public/                   # Static assets
└── styles/                   # Global styles
```

## Components

### Wu Xing Wheel
Circular visualization of current workflow phase based on Wu Xing (五行) theory:
- **Wood** (木): Planning, research
- **Fire** (火): Creation, execution
- **Earth** (土): Consolidation
- **Metal** (金): Refinement
- **Water** (水): Reflection

### Token Chart
Line chart showing token efficiency over time with tier indicators.

### Timeline
Chronological view of session activities with status indicators.

### Memory Stats
Summary cards showing memory counts, types, and tag distribution.

## Performance

- **Bundle size**: < 500KB
- **Load time**: < 1s
- **Updates**: Real-time (Phase 2)

##License

MIT
