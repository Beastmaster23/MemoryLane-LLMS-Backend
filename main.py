from langchain.llms import LlamaCpp
from langchain import PromptTemplate, LLMChain
from langchain.callbacks.base import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Weaviate
from dotenv import load_dotenv
import os
from server.http_server import HttpRequestHandler, PromptRequest, PromptResponse, validate_prompt_request
from http.server import HTTPServer

import json
import weaviate

def setup_server()->HTTPServer:
    """Setup the server."""
    global callback_manager, llm, model_path
    # Create the callback manager
    callback_manager = CallbackManager([ StreamingStdOutCallbackHandler()])

    # Load the model
    llm = LlamaCpp(
        model_path=model_path,
        callback_manager=callback_manager,
        verbose=True,
        streaming=True,
    )

    return HTTPServer(('localhost', 9000), HttpRequestHandler)

def setup_database():
    """Setup the database."""
    global WEAVIATE_URL, client
    # Connect to weaviate
    WEAVIATE_URL = os.getenv("WEAVIATE_URL")
    client = weaviate.Client(
        url=WEAVIATE_URL,
        additional_headers={
            'X-OpenAI-Api-Key': os.getenv("OPENAI_API_KEY"),
        }
    )

    # Check if the class Chat exists
    #client.schema.delete_all()
    client.schema.get()
    chat_exists = False
    for class_ in client.schema.get()['classes']:
        if class_['class'] == 'Chat':
            chat_exists = True
            break

    if not chat_exists:
        # Create the class
        schema = {
        "classes": [
            {
                "class": "Chat",
                "description": "A chat between two people",
                "vectorizer": "text2vec-openai",
                "moduleConfig": {
                    "text2vec-openai": {
                    "model": "ada",
                    "modelVersion": "002",
                    "type": "text"
                    }
                },
                "properties": [
                    {
                        "dataType": ["text"],
                        "description": "The content of the chat",
                        "moduleConfig": {
                            "text2vec-openai": {
                            "skip": False,
                            "vectorizePropertyName": False
                            }
                        },
                        "name": "content",
                    },
                ],
            },
            ]
        }

        client.schema.create(schema)
    # Create the vector store
    client.schema.get()
    return client

def load_settings():
    """Load the settings from the settings.json file."""
    global settings, model_path
    settings = json.load(open("settings.json"))
    if settings.model_name is not None:
        # Search for the model in the models folder
        model_folder = os.path.join("models", settings.model_name)
        if os.path.isdir(model_folder):
            model_path = model_folder
        else:
            raise Exception(f"Could not find model {settings.model_name} in the models folder")
load_dotenv(".env") # load environment variables from ".env
settings = None
load_settings()
# import environment variables
model_path = os.getenv("MODEL_PATH")


count = 0
running = False

callback_manager = None
llm = None
WEAVIATE_URL=None
client=None

server=setup_server()
client = setup_database()
vectorstore = Weaviate(client, "Chat", "content")
HttpRequestHandler.vectorstore = vectorstore
HttpRequestHandler.llm = llm
HttpRequestHandler.callback_manager = callback_manager

try:
    server.serve_forever()
except KeyboardInterrupt:
    print("Stopping server")
finally:
    server.server_close()
    print("Server closed")
