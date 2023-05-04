import asyncio
import websockets
import json
class Client:
	def __init__(self):
		self.server = None
		self.websocket = None

	async def connect(self, uri):
		self.websocket = await websockets.connect(uri)
		

	async def send_message(self, message):
		await self.websocket.send(message)

	async def receive_message(self):
		try:
			message = await self.websocket.recv()
			print('Received message: {}'.format(message))
			return message
		except websockets.exceptions.ConnectionClosed:
			print('Connection with server closed')

	async def on_disconnect(self):
		print('Disconnected from server')

	async def disconnect(self):
		await self.websocket.close()

async def main():
	
	# Create prompt request
	prompt_text = """This is a chat between an AI and a human. The AI is very friendly and will try to help you with your problems. In English"""
	history_text = """This is the history of the chat( if there is any):
{history}"""
	chat_text = {
		'user_name':"""### {user_name}: {user_text}""",
		'ai_name':"""### {ai_name}: {ai_text}"""
	}
	complete_prompt = """{prompt}
{history}
Chat:
{chat1}
{chat2}"""
	complete_prompt = complete_prompt.format(prompt=prompt_text, history=history_text, chat1=chat_text['user_name'], chat2=chat_text['ai_name'])
	
	request = {
		'chat_text': chat_text,
		'complete_prompt': complete_prompt,
		'args':{
			'history':""
		},
		'names':{
			'user_name':'Human',
			'ai_name':'AI'
		},
		'chat': {
			'user_text':' Hello my friend!',
			'ai_text':' '
		}
	}
	# convert to json
	request = json.dumps(request)
	client = Client()
	await client.connect('ws://localhost:9001')
	
	await client.send_message(request)
	print('Sent message: {}'.format(request))
	response = await client.receive_message()

	if response:
		response = json.loads(response)
		print(response)
if __name__ == '__main__':
	asyncio.get_event_loop().run_until_complete(main())