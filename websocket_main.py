from langchain.llms import LlamaCpp
from langchain import PromptTemplate, LLMChain
from langchain.callbacks.base import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Weaviate
from dotenv import load_dotenv
from server.streaming import StreamingWebsocketCallbackHandler
import os
from server.server import Server, SERVER_CODES, PromptRequest, PromptResponse
import json
import weaviate
load_dotenv(".env") # load environment variables from ".env
# import environment variables
model_path = os.getenv("MODEL_PATH")

# Start the server
server = Server()

count = 0
running = False
#Streaming reference
streaming_callback = StreamingWebsocketCallbackHandler(server, -1)
# Create the callback manager
callback_manager = CallbackManager([ StreamingStdOutCallbackHandler()])

# Load the model
llm = LlamaCpp(
    model_path=model_path,
    callback_manager=callback_manager,
    verbose=True,
    streaming=True,
)

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
vectorstore = Weaviate(client, "Chat", "content")

def on_disconnect(client_id):
    """Handle the disconnect event."""
    global count
    print("Client {} disconnected".format(client_id))
    count -= 1

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

def run_chain(client_id, prompt_request: PromptRequest) -> PromptResponse:
    """Run a chain."""
    global running
    running = True
    global llm
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
    
    streaming_callback.client_id = client_id
    output = ""
    # Create the chain
    chain = LLMChain(
        llm=llm,
        prompt=template,
        callback_manager=callback_manager,
    )

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
    
async def server_handler(server, ws, uri, client_id):
    """
    It must return one of the following codes:
    SERVER_CODES['SUCCESS'] - if the request was successful and wants end the connection
    SERVER_CODES['ERROR'] - if there was an error and wants to end the connection
    SERVER_CODES['RUNNING'] - if the request was successful and wants to keep the connection open
    This is where you would run the chain and send the output to the client
    """
    global count
    global running
    count += 1
    if count>1 and not running:
        # Disconnect the client
        await server.disconnect(client_id)
        return SERVER_CODES['SUCCESS']
    
    # Get the prompt request
    prompt_request = json.loads(await server.receive(client_id))
    print(prompt_request)
    prompt_request = validate_prompt_request(prompt_request)

    # LLM stuff
    prompt_response=run_chain(client_id, prompt_request)

    # Send the response
    await server.send_to_client(client_id, prompt_response.to_json())
    return SERVER_CODES['SUCCESS']


server.on_disconnect = on_disconnect
server.start('localhost', 9001, server_handler)