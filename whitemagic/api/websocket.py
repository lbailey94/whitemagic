"""WebSocket endpoints for live dashboard updates."""

from typing import Dict, List
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import json
import asyncio


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept new connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove connection."""
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                dead_connections.append(connection)
        
        # Clean up dead connections
        for conn in dead_connections:
            self.active_connections.remove(conn)


manager = ConnectionManager()


async def emit_cycle_complete(cycles: int, patterns: int, duration: float):
    """Emit cycle completion event."""
    await manager.broadcast({
        "event": "cycle_complete",
        "data": {
            "cycles": cycles,
            "patterns": patterns,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
    })


async def emit_pattern_discovered(pattern: dict):
    """Emit pattern discovery event."""
    await manager.broadcast({
        "event": "pattern_discovered",
        "data": {
            "pattern": pattern,
            "timestamp": datetime.now().isoformat()
        }
    })


async def emit_metrics_update(metrics: dict):
    """Emit metrics update."""
    await manager.broadcast({
        "event": "metrics_update",
        "data": metrics
    })


async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo back for ping/pong
            await websocket.send_json({"status": "ok"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
