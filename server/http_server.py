import json
import logging
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from langchain import PromptTemplate, LLMChain
from langchain.callbacks.base import CallbackManager

"""
The server that will handle the requests.
URL: http://localhost:9000
	GET /prompt - get a prompt by sending a PromptRequest as a json
		Args:
			complete_prompt (required): str - the complete prompt to send to the AI
			chat_text (required): dict - the chat text to send to the AI
				1. user_name: str - the user's text
				2. ai_name: str - the ai's text
			names (required): dict - the names for the user and the ai
				1. user_name: str - the user's name
				2. ai_name: str - the ai's name
			args: dict - the arguments to send to the AI (optional) (history is required)
				1. history (required): str - the history of the conversation
            save (optional): bool - whether to save the prompt to the database (default: False)
            memory (optional): bool - whether to use the memory (default: False)
	POST /settings - change the settings
        Args:
            model_name (optional): str - the name of the model to use for the AI (default: vicuna-7b)
                (vicuna-7b, pygmalion-7b)
            vectorstore_name (optional): str - the name of the vectorstore to use for the AI (default: weaviate)
                (weaviate is the only vectorstore supported at the moment)
"""
SERVER_CODES = {
    'SUCCESS': 23,
    'ERROR': -1,
    'RUNNING': 0
}

class HttpRequestHandler(BaseHTTPRequestHandler):
	"""The HTTP request handler."""
	llm=None
	vectorstore=None
	callback_manager=None
	def do_POST(self):
		"""Handle a POST request."""
		logging.info("POST request received")
		logging.info(f"Path: {self.path}")
		try:
			if re.search("/settings", self.path):
				# Get the settings request from the content
				content_length = int(self.headers['Content-Length'])
				post_data = self.rfile.read(content_length)
				settings_request = json.loads(post_data)
				# Save the settings in json file
				with open('settings.json', 'w') as f:
					json.dump(settings_request, f)

				self.send_response(200, "OK")
				self.end_headers()
				self.wfile.write(json.dumps({'status': SERVER_CODES['SUCCESS']}).encode())
			else:
				self.send_response(404)
				self.end_headers()
				self.wfile.write(json.dumps({'status': SERVER_CODES['ERROR']}).encode())
		except Exception as e:
			logging.error(e)
			self.send_response(500, "Internal Server Error or Invalid Request")
			self.end_headers()
			self.wfile.write(json.dumps({'status': SERVER_CODES['ERROR'], 'error': "Internal Server Error or Invalid Request"}).encode())
        
	def do_GET(self):
		"""Handle a GET request."""
		logging.info("GET request received")
		logging.info(f"Path: {self.path}")
		try:
			if re.search("/prompt", self.path):
				# Get the prompt request from the content
				content_length = int(self.headers['Content-Length'])
				post_data = self.rfile.read(content_length)
				prompt_request = json.loads(post_data)
				prompt_request=validate_prompt_request(prompt_request)
				prompt_response=run_chain(prompt_request, self.llm, self.vectorstore, self.callback_manager)
				self.send_response(200, "OK")
				self.send_header("Content-type", "application/json")
				self.end_headers()
				self.wfile.write(prompt_response.to_json().encode())
			else:
				self.send_response(404)
			self.end_headers()
		except Exception as e:
			logging.error(e)
			self.send_response(500, "Internal Server Error or Invalid Request")
			self.end_headers()
			self.wfile.write(json.dumps({'status': SERVER_CODES['ERROR'], 'error': "Internal Server Error or Invalid Request"}).encode())
        

class PromptRequest:
    """A request for a prompt."""

    def __init__(self, complete_prompt, chat_text: dict={'user': '', 'ai': ''},
		 names:dict={'user_name': 'user', 'ai_name': 'ai'}, chat:dict={'user_text': '', 'ai_text': ''}, args:dict=None,
		 save: bool=False, memory:bool=False):
        """Initialize the prompt request."""
        self.args = args
        self.names = names
        self.complete_prompt = complete_prompt
        self.chat_text = chat_text
        self.chat = chat
        self.save = save
        self.memory = memory

    def to_json(self):
        dict={'args': self.args, 'names': self.names, 'complete_prompt': self.complete_prompt, 'chat_text': self.chat_text, 'chat': self.chat
                , 'save': self.save, 'memory': self.memory}
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

def validate_prompt_request(prompt_dictionary: dict) -> PromptRequest:
    """Validate the prompt request."""
    
    # Check if the completed prompt is a string and in the dictionary
    if "complete_prompt" not in prompt_dictionary or not isinstance(prompt_dictionary["complete_prompt"], str):
        raise ValueError("Prompt must be a string")
    prompt = prompt_dictionary["complete_prompt"]
    # Check if the chat text is a dictionary
    if "chat_text" not in prompt_dictionary or not isinstance(prompt_dictionary["chat_text"], dict):
        raise ValueError("Chat text must be a dictionary")
    chat_text = prompt_dictionary["chat_text"]
    # Check if the args is a dictionary
    if "args" not in prompt_dictionary or not isinstance(prompt_dictionary["args"], dict):
        raise ValueError("Args must be a dictionary")
    args = prompt_dictionary["args"]
    # Check if the names is a dictionary
    if "names" not in prompt_dictionary or not isinstance(prompt_dictionary["names"], dict):
        raise ValueError("Names must be a dictionary")
    names = prompt_dictionary["names"]

    # Check if the chat is a dictionary
    if "chat" not in prompt_dictionary or not isinstance(prompt_dictionary["chat"], dict):
        raise ValueError("Chat must be a dictionary")
    chat = prompt_dictionary["chat"]
    return PromptRequest(
        complete_prompt=prompt,
        chat_text=chat_text,
        args=args,
        names=names,
        chat=chat,
    )

def run_chain(prompt_request: PromptRequest, llm, vectorstore, callback_manager: CallbackManager) -> PromptResponse:
    """Run a chain."""
    
    input_variables = []
    input_variables.extend(list(prompt_request.names.keys()))
    input_variables.extend(list(prompt_request.chat.keys()))
    template = None
    if prompt_request.args is not None:
        input_variables.extend(list(prompt_request.args.keys()))
        print(input_variables)
        template = PromptTemplate(
            template=prompt_request.complete_prompt,
            input_variables=input_variables,
        )
    
    output = ""
    # Create the chain
    chain = LLMChain(
        llm=llm,
        prompt=template,
        callback_manager=callback_manager,
    )
    if prompt_request.memory:
        # Get docs from the vector store
        docs = vectorstore.similarity_search(
            prompt_request.chat_text["user_name"].format(**prompt_request.chat, **prompt_request.names),
            k=4)
        history = []
        for doc in docs:
            history.append(doc.page_content)
        prompt_request.args["history"] = history
    # Run the chain
    output = chain.run(**prompt_request.args, **prompt_request.names, **prompt_request.chat)
    chat=prompt_request.chat
    chat["ai_text"]+=output
    complete_prompt = prompt_request.complete_prompt.format(**prompt_request.args, **prompt_request.names, **prompt_request.chat)
    output=complete_prompt+output
    if prompt_request.save:
        # Create query
        chat_text = prompt_request.chat_text
        
        text = f'{chat_text["user_name"]}\n{chat_text["ai_name"]}'.format(**prompt_request.chat, **prompt_request.names)
        
        # Save the embeddings to the database
        result=vectorstore.add_texts([text])
        print(result)
    # Create the response
    response = PromptResponse(status=SERVER_CODES['SUCCESS'], prompt=output, chat=chat)
    
    # Return the response
    return response


if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO)
	logging.info("Please use a this in a different file not on its own")
	