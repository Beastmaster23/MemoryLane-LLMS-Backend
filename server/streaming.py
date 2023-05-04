from typing import Any, Dict, List, Optional, Union, Callable, Awaitable, Coroutine

from langchain.agents import initialize_agent, load_tools
from langchain.agents import AgentType
from langchain.callbacks.base import CallbackManager, BaseCallbackHandler, AsyncCallbackHandler
from langchain.schema import AgentAction, AgentFinish, LLMResult

from server.server import Server, SERVER_CODES, PromptRequest, PromptResponse
import asyncio
import json


class WebsocketCallbackHandler(BaseCallbackHandler):
    """Custom CallbackHandler for Websocket.
        Will stream output to the websocket server.
        
    """

    def __init__(self, server, client_id: int=-1):
        super().__init__()
        self.server: Server = server
        self.client_id: int=client_id
    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Print out the prompts."""
        pass

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Do nothing."""
        print("")
        print(response.generations[0][0].text, end="", flush=True)
        # Create a prompt response
        prompt_response = PromptResponse(status=SERVER_CODES["RUNNING"], prompt=response.generations[0][0].text)
        # Send the response
        synchronize_async_helper(self.server.send_to_client, self.client_id, prompt_response.to_json())
    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Do nothing."""
        print(token, end="", flush=True)
        # Create a prompt response
        response = PromptResponse(status=SERVER_CODES["RUNNING"], token=token)
        # Send the response
        synchronize_async_helper(self.server.send_to_client, self.client_id, response.to_json())
    def on_llm_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """Do nothing."""
        pass

    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """Print out that we are entering a chain."""
        class_name = serialized["name"]
        print(f"\n\n\033[1m> Entering new {class_name} chain...\033[0m")

    def on_chain_end(self, response: AgentFinish, **kwargs: Any) -> None:
        """Do nothing."""
        pass

    def on_chain_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """Do nothing."""
        pass

    def on_agent_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """Print out that we are entering an agent."""
        class_name = serialized["name"]
        print(f"\n\n\033[1m> Entering new {class_name} agent...\033[0m")

    def on_agent_end(self, response: AgentAction, **kwargs: Any) -> None:
        """Do nothing."""
        pass

    def on_agent_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """Do nothing."""
        pass

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Do nothing."""
        pass

    def on_agent_action(
        self, action: AgentAction, color: Optional[str] = None, **kwargs: Any
    ) -> Any:
        """Run on agent action."""
        print(action)

    def on_tool_end(
        self,
        output: str,
        color: Optional[str] = None,
        observation_prefix: Optional[str] = None,
        llm_prefix: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """If not the final action, print out observation"""
        print(output)

    def on_tool_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """Do nothing."""
        pass
    
    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> Any:
        """Do nothing."""
        pass

    def on_text(self, text: str, **kwargs: Any) -> None:
        """Do nothing."""
        pass

class StreamingWebsocketCallbackHandler(AsyncCallbackHandler):
    """Custom CallbackHandler for Websocket.
        Will stream output to the websocket server.
        
    """

    def __init__(self, server, client_id: int=-1):
        super().__init__()
        self.server: Server = server
        self.client_id: int=client_id
    
    async def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> Coroutine[Any, Any, None]:
        """Print out the prompts."""
        await self.server.send_to_client(self.client_id, PromptRequest(status=SERVER_CODES["RUNNING"], token="hhh").to_json())

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> Coroutine[Any, Any, None]:
        """Do nothing."""
        print(token, end="", flush=True)
        # Create a prompt response
        response = PromptResponse(status=SERVER_CODES["RUNNING"], token=token)
        # Send the response
        return None


    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Coroutine[Any, Any, None]:
        """Do nothing."""
        print("")
        print(response.generations[0][0].text, end="", flush=True)
        # Create a prompt response
        prompt_response = PromptResponse(status=SERVER_CODES["RUNNING"], prompt=response.generations[0][0].text)
        # Send the response
        await self.server.send_to_client(self.client_id, prompt_response.to_json())

class StreamingToUserCallbackHandler(BaseCallbackHandler):
    """Custom CallbackHandler."""

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Print out the prompts."""
        pass

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Do nothing."""
        print("")
        print(response.generations[0][0].text, end="", flush=True)

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Do nothing."""
        print(token, end="", flush=True)
        
    def on_llm_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """Do nothing."""
        pass

    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """Print out that we are entering a chain."""
        class_name = serialized["name"]
        print(f"\n\n\033[1m> Entering new {class_name} chain...\033[0m")

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Print out that we finished a chain."""
        print("\n\033[1m> Finished chain.\033[0m", flush=True)

    def on_chain_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """Do nothing."""
        pass

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Do nothing."""
        pass

    def on_agent_action(
        self, action: AgentAction, color: Optional[str] = None, **kwargs: Any
    ) -> Any:
        """Run on agent action."""
        print(action)

    def on_tool_end(
        self,
        output: str,
        color: Optional[str] = None,
        observation_prefix: Optional[str] = None,
        llm_prefix: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """If not the final action, print out observation."""
        print(output)

    def on_tool_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """Do nothing."""
        pass

    def on_text(
        self,
        text: str,
        color: Optional[str] = None,
        end: str = "",
        **kwargs: Optional[str],
    ) -> None:
        """Run when agent ends."""
        print(text)

    def on_agent_finish(
        self, finish: AgentFinish, color: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Run on agent end."""
        print(finish.log)