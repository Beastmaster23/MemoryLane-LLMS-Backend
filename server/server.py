from typing import Callable
import websockets
import asyncio
import json
SERVER_CODES = {
    'SUCCESS': 23,
    'ERROR': -1,
    'RUNNING': 0
}

class Server:
	def __init__(self):
		self.clients: dict= {}
		self.id: int = 0
		self.on_message : Callable[[int, str], None] = lambda client_id, message: None
		self.on_error : Callable[[int, str], None] = lambda client_id, error: None
		self.on_send : Callable[[int, str], None] = lambda client_id, message: None
		self.on_connect : Callable[[int], None] = lambda client_id: None
		self.on_disconnect : Callable[[int], None] = lambda client_id: None
		self.server_handler : Callable[[Server, websockets.WebSocketServerProtocol, str, int], int] = lambda server, ws, uri, client_id: 0
	async def register(self, ws):
		client_id = self.id
		self.clients[self.id] = ws
		self.on_connect(self.id)
		print("Client {} connected".format(ws.remote_address))
		self.id += 1
		return client_id

	async def unregister(self, client_id):
		if client_id in self.clients:
			del self.clients[client_id]
			self.on_disconnect(client_id)
			print("Client {} disconnected from server".format(client_id))
		else:
			raise ValueError("Client {} not found".format(client_id))
		
	async def send_to_clients(self, message):
		for id, client in self.clients.items():
			await client.send(message)
			self.on_send(id, message)
	
	async def send_to_client(self, client_id, message):
		if client_id in self.clients.keys():
			await self.clients[client_id].send(message)
			self.on_send(client_id, message)
		else:
			raise ValueError("Client {} not found".format(client_id))
		
	async def receive(self, client_id):
		if client_id in self.clients.keys():
			message = await self.clients[client_id].recv()
			self.on_message(client_id, message)
			return message
		else:
			raise ValueError("Client {} not found".format(client_id))
		
	async def ws_handler(self, ws, uri):
		"""Handles the websocket connection
			will loop forever until the connection is closed by the client or until server_handler 
		"""
		client_id = await self.register(ws)
		try:
			while True:
				error=await self.server_handler(self, ws, uri, client_id)
				if error != SERVER_CODES['RUNNING']:
					break
				if error == SERVER_CODES['ERROR']:
					self.on_error(ws.remote_address, "Server handler returned an error")
					await self.send_to_client(client_id, "Server handler returned an error")
					break
		except websockets.exceptions.ConnectionClosed:
			print("Connection with client {} closed".format(ws.remote_address))
			self.on_error(ws.remote_address, "Connection closed unexpectedly by client")
			self.on_disconnect(ws.remote_address)
		finally:
			await self.unregister(client_id)

	async def disconnect(self, client_id):
		if client_id in self.clients:
			await self.clients[client_id].close()
			await self.unregister(client_id)
		else:
			raise ValueError("Client {} not found".format(client_id))

	def start(self, host, port, handler):
		self.server_handler = handler
		start_server = websockets.serve(self.ws_handler, host, port)
		asyncio.get_event_loop().run_until_complete(start_server)
		asyncio.get_event_loop().run_forever()
	
	def stop(self):
		asyncio.get_event_loop().stop()

"""
    Every time a client connects, they must send a dictionary with the following keys and some are optional:
    complete_prompt (required): str - the complete prompt to send to the AI
    chat_text (required): dict - the chat format string to send to the AI
        1. user_name: str - the user side of the chat format string
		    Ex: ### {user_name}: {user_text}
		2. ai_name: str - the ai side of the chat format string
			Ex: ### {ai_name}: {ai_text}
	chat (required): dict - the chat to send to the AI
		1. user_text: str - the user's text
		2. ai_text: str - the ai's text
	names (required): dict - the names for the user and the ai
		1. user_name: str - the user's name
		2. ai_name: str - the ai's name
	args: dict - the arguments to send to the AI (optional) (history is required)
		1. history (required): str - the history of the conversation

    The server will then send back a dictionary with the following keys:
    status: int | SERVER_CODES - the status code [23: success, -1: error, 0: running]
    token: str - the token that got generated
    error: str - the error message if there was an error
"""

class PromptRequest:
    """A request for a prompt."""

    def __init__(self, complete_prompt, chat_text: dict={'user': '', 'ai': ''},
		 names:dict={'user_name': 'user', 'ai_name': 'ai'}, chat:dict={'user_text': '', 'ai_text': ''}, args:dict=None):
        """Initialize the prompt request."""
        self.args = args
        self.names = names
        self.complete_prompt = complete_prompt
        self.chat_text = chat_text
        self.chat = chat

    def to_json(self):
        dict={'args': self.args, 'names': self.names, 'complete_prompt': self.complete_prompt, 'chat_text': self.chat_text, 'chat': self.chat}
        return json.dumps(dict)
    def __str__(self):
        """Return the string representation of the prompt request."""
        return f"PromptRequest(args={self.args}, names={self.names}, complete_prompt={self.complete_prompt}, chat_text={self.chat_text})"

    def __repr__(self):
        """Return the string representation of the prompt request."""
        return self.__str__()

class PromptResponse:
    """A response to a prompt."""

    def __init__(self, status: int, token: str|None=None, prompt: str|None=None, error: str|None=None, chat:dict={'user_text': '', 'ai_text': ''}):
        """Initialize the prompt response."""
        self.status = status
        self.token = token
        self.prompt = prompt
        self.chat=chat
        self.error = error
	
    def to_json(self):
        dict={'status': self.status, 'token': self.token, 'prompt': self.prompt, 'error': self.error, 'chat': self.chat}
        return json.dumps(dict)

    def __str__(self):
        """Return the string representation of the prompt response."""
        return f"PromptResponse(status={self.status}, token={self.token}, error={self.error})"

    def __repr__(self):
        """Return the string representation of the prompt response."""
        return self.__str__()


if __name__ == '__main__':
	print("Please run a server file instead")