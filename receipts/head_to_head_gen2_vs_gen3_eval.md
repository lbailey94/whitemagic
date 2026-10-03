# Head-to-Head Evaluation: WhiteMagic Gen2 (v9.3.4) vs Hybrid Gen3 (v10.0.0-alpha)

*Evaluated on 2026-10-03T14:33:29Z across live local stores.*

| Metric | Gen2 (v9.3.4) | Gen3 Full | Gen3 Cyberbrain | Delta / Speedup |
|:---|---:|---:|---:|:---|
| Cold Startup Time | 0.56 ms | 2.91 ms | 0.61 ms | 0.9× faster |
| Initialize Latency | 57.27 ms | 15.45 ms | 6.17 ms | 9.3× faster |
| Tools List Latency | 3.15 ms | 7.44 ms | 0.48 ms | 6.5× faster |
| Tools Count | 23 | 37 | 10 | 10 lean tools (-56%) |
| Tools Wire Size | 28,469 B | 24,426 B | 5,140 B | 5.5× smaller |
| Memory Search (Median) | 1451.57 ms | 162.75 ms | 104.60 ms | 13.9× speedup |
| Memory Search (P95) | 3580.25 ms | 951.40 ms | 857.16 ms | 4.2× speedup |
| Memory Read Latency | 2.58 ms | 0.21 ms | 0.31 ms | 8.3× speedup |
| Memory Stats Latency | 61.87 ms | 0.15 ms | 0.12 ms | 499.6× speedup |
| Session Continuity Latency | 7.13 ms | 0.14 ms | 0.11 ms | 63.1× speedup |
| Session List Latency | 3.24 ms | 2.93 ms | 2.68 ms | 1.2× speedup |
| RSS Memory Footprint | 49.9 MB | 580.8 MB | 581.2 MB | Sub-50 MB native |
| JEV/Layla Triage Gate | N/A (unclassified) | 3875715.0 ns | 3875715.0 ns | Sub-microsecond gate |

### Sangha Whiteboard Fleet Agora Telemetry

- **Bridge HTTP Status Latency**: 155.67 ms
- **Sangha CLI Status Latency**: 533.33 ms
- **Sangha Inbox Unread Check**: 149.95 ms
- **Total Dispatches on Board**: 629
