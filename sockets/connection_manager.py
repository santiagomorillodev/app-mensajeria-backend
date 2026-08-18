from fastapi import WebSocket
from typing import Dict, Set, Any


class ConnectionManager:

    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}


    async def connect( self, user_id: int, websocket: WebSocket):
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)

        print(f"🟢 Usuario {user_id} conectado")


    def disconnect( self, user_id: int, websocket: WebSocket):

        if user_id not in self.active_connections:
            return

        self.active_connections[user_id].discard(websocket)

        if not self.active_connections[user_id]:
            del self.active_connections[user_id]

        print(f"🔴 Usuario {user_id} desconectado")


    async def send_personal_message( self, message: Dict[str, Any], user_id: int):

        connections = self.active_connections.get( user_id, set())

        for websocket in list(connections):
            try:
                await websocket.send_json(message)
            except Exception as error:
                print(f"Error enviando a usuario {user_id}:",error)

                self.disconnect( user_id, websocket)


    async def send_to_users( self, message: Dict[str, Any], user_ids: list[int]):

        for user_id in set(user_ids):
            await self.send_personal_message( message, user_id)


    async def broadcast( self, message: Dict[str, Any]):

        for user_id in list( self.active_connections.keys() ):

            await self.send_personal_message( message, user_id )