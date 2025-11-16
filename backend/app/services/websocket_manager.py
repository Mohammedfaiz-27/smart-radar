"""
WebSocket connection manager for real-time updates
"""
import json
from typing import List
from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific WebSocket connection"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
            
        message_str = json.dumps(message)
        disconnected_connections = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                print(f"Error broadcasting to connection: {e}")
                disconnected_connections.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected_connections:
            self.disconnect(connection)

    async def broadcast_new_post(self, post_data: dict):
        """Broadcast new post to all clients"""
        message = {
            "type": "new_post",
            "data": post_data
        }
        await self.broadcast(message)

    async def broadcast_alert(self, alert_data: dict):
        """Broadcast alert to all clients"""
        message = {
            "type": "alert",
            "data": alert_data
        }
        await self.broadcast(message)

    async def broadcast_message(self, message: dict):
        """Generic method to broadcast any message - used by Celery tasks"""
        await self.broadcast(message)

    async def broadcast_campaign_detected(self, campaign_data: dict):
        """Broadcast new campaign detection"""
        message = {
            "type": "campaign_detected",
            "data": campaign_data
        }
        await self.broadcast(message)

    async def broadcast_campaign_escalation(self, escalation_data: dict):
        """Broadcast campaign escalation alert"""
        message = {
            "type": "campaign_escalation",
            "data": escalation_data,
            "priority": "high"
        }
        await self.broadcast(message)

    async def broadcast_campaign_update(self, campaign_data: dict):
        """Broadcast campaign update"""
        message = {
            "type": "campaign_update",
            "data": campaign_data
        }
        await self.broadcast(message)

    async def broadcast_campaign_resolved(self, campaign_data: dict):
        """Broadcast campaign resolution"""
        message = {
            "type": "campaign_resolved",
            "data": campaign_data
        }
        await self.broadcast(message)

# Global WebSocket manager instance
websocket_manager = WebSocketManager()