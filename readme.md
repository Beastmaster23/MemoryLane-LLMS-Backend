# MemoryLane-LLMS-Backend
## _Adding Long-Term Memories to LLMS as a Local Backend Server for Simple Local Projects_

A Backend Server for Serving AI-Generated Text to Your Applications

## Supported

- LLM's supported (Vicuna or LLama based)
- Weaviate DB
- Websockets for streaming
- REST API

## Features

- Long-term memory in your local chats
- Soon have all data local to your network
- Option to use OpenAI
- A simple REST API

## Backend Dependency

MemoryLane uses a number of open source projects to work properly:

- [LangChain] This runs the llm and has several wrappers for vector databases
- [Weaviate] This is the main vector database
- [Websockets] For streaming the text to clients (When langchain supports it)
- [Docker] For your database

And of course Dillinger itself is open source with a [public repository][dill]
 on GitHub.

## Installation

MemoryLane uses python 3.10.+

Install the dependencies using pip or windows bat

## Windows Installer
It's super simple just setup your vector database and get OpenAI API key
```sh
windows_install.bat
```

## Manual Installer

I recommend using conda to seperate your environment.

# Setup Weaviate Here:
[WeaviateDocker] This will setup a docker file.
Run in this directory.
```sh
docker-compose up -d
```

```sh
pip install -r requirements.txt
```

## Usage

Run the main for http server
```sh
python main.py
```

Run the websocket_main for websocket server
```sh
python websocket_main.py
```

# Client

Clients and Server will send and receive JSON request for AI responses.
Client:
```json
{
    complete_prompt: str the complete prompt to send to the AI (required),
    chat_text: dict the chat format string to send to the AI
        {user_name: str - the user side of the chat format string
        ai_name: str - the ai side of the chat format string},
    chat (required): dict - the chat to send to the AI
        {user_text: str - the user's text,
        ai_text: str - the ai's text},
    names (required): dict - the names for the user and the ai
        {user_name: str - the user's name,
        ai_name: str - the ai's name},
    args: dict - the arguments to send to the AI (optional) (history is required)
        {history (required): str - the history of the conversation},
    save (optional): bool - whether to save the prompt to the database (default: False),
    memory (optional): bool - whether to use the memory (default: False)
}
```



Server:
```json
{
    status: int | SERVER_CODES - the status code [23: success, -1: error, 0: running],
    token: str - the token that got generated,
    prompt: str - the prompt that got generated,
    error: str - the error message if there was an error
}
```

## Development

Want to contribute? Great!

Just make a pull request when done.

## License

MIT

**Happy Devving**

   [LangChain]: <https://python.langchain.com/en/latest/index.html>
   [Weaviate]: <https://weaviate.io>
   [Websockets]: <https://pypi.org/project/websockets/>
   [WeaviateDocker]: <https://weaviate.io/developers/weaviate/installation/docker-compose>