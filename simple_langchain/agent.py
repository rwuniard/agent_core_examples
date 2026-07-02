import os
from typing import AsyncIterator

from dotenv import load_dotenv
load_dotenv()  # loads .env for local dev; no-op when env vars are already set

from langchain.agents import create_agent
from langchain_aws import ChatBedrockConverse
from langgraph_checkpoint_aws import AgentCoreMemorySaver
from opentelemetry.instrumentation.langchain import LangchainInstrumentor

# Bedrock AgentCore App
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# OpenTelemetry Instrumentation, so it will send Session, Traces, Spans to CloudWatch.
LangchainInstrumentor().instrument()

app = BedrockAgentCoreApp()


def _extract_text(content) -> str:
    """Normalize a message chunk's content into plain text.

    ChatBedrockConverse can emit content as a plain string or as a list of
    Converse-style content blocks (e.g. [{"type": "text", "text": "..."}]).
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block if isinstance(block, str) else block.get("text", "")
            for block in content
            if isinstance(block, str) or block.get("type") == "text"
        )
    return ""


class SimpleLangchainAgent:

    def __init__(self):
        self.llm = ChatBedrockConverse(model="us.amazon.nova-pro-v1:0", region_name="us-east-1")
        self.tools = []
        self.system_prompt = """
        You are a helpful assistant that can answer questions and help with tasks.
        """
        # AgentCoreMemorySaver persists conversation state to AgentCore Memory,
        # surviving container restarts. Requires AGENTCORE_MEMORY_ID env var.
        checkpointer = AgentCoreMemorySaver(
            memory_id=os.environ["AGENTCORE_MEMORY_ID"],
            region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        )
        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.system_prompt,
            checkpointer=checkpointer,
        )

    # sync entrypoint with invoke method. Blocking call.
    # The invoke method is less efficient than the invoke_async method because it blocks until the entire response is generated.
    def invoke(self, user_message: str, actor_id: str, thread_id: str) -> str:
        config = {
            "configurable": {
                "actor_id": actor_id,   # identifies the user across sessions
                "thread_id": thread_id, # identifies the conversation session
            }
        }
        messages = {"messages": [{"role": "user", "content": user_message}]}
        result = self.agent.invoke(messages, config=config)
        return result["messages"][-1].content
    
    # async entrypoint with invoke_async method. This is more efficient than the sync entrypoint with invoke method.
    # It blocks until the entire response is generated, then returns the final result.
    # The invoke_async method is more efficient than the invoke method because it doesn't block until the entire response is generated.
    async def invoke_async(self, user_message: str, actor_id: str, thread_id: str) -> str:
        config = {
            "configurable": {
                "actor_id": actor_id,   # identifies the user across sessions
                "thread_id": thread_id, # identifies the conversation session
            }
        }
        messages = {"messages": [{"role": "user", "content": user_message}]}
        result = await self.agent.ainvoke(messages, config=config)
        return result["messages"][-1].content

    # async entrypoint with astream method. Streams yielded chunks as SSE.
    async def astream(self, user_message: str, actor_id: str, thread_id: str) -> AsyncIterator[str]:
        """Yield response text chunks as they're generated, instead of blocking until completion."""
        config = {
            "configurable": {
                "actor_id": actor_id,   # identifies the user across sessions
                "thread_id": thread_id, # identifies the conversation session
            }
        }
        messages = {"messages": [{"role": "user", "content": user_message}]}
        async for message_chunk, _metadata in self.agent.astream(
            messages, config=config, stream_mode="messages"
        ):
            text = _extract_text(message_chunk.content)
            if text:
                yield text

# Create agent once at module level so the checkpointer connection is reused.
agent = SimpleLangchainAgent()

# This is with astream method. Streams yielded chunks as SSE.
@app.entrypoint
async def agent_entrypoint_async(payload, context):
    """Async-generator entrypoint: BedrockAgentCoreApp streams yielded chunks as SSE."""
    actor_id = payload.get("actor_id", "default-actor")
    print(f"actor_id: {actor_id}")
    thread_id = payload.get("session_id", context.session_id)
    print(f"thread_id: {thread_id}")
    print(f"payload: {payload}")
    async for chunk in agent.astream(payload["message"], actor_id=actor_id, thread_id=thread_id):
        yield chunk

# sync entrypoint with invoke method.
# def agent_entrypoint(payload, context):
#     actor_id = payload.get("actor_id", "default-actor")
#     print(f"actor_id: {actor_id}")
#     thread_id = payload.get("session_id", context.session_id)
#     print(f"thread_id: {thread_id}")
#     print(f"payload: {payload}")
#     return agent.invoke(payload["message"], actor_id=actor_id, thread_id=thread_id)


if __name__ == "__main__":
    print("Starting the agent...")
    app.run()
