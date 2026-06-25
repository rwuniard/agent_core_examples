import os

from dotenv import load_dotenv
load_dotenv()  # loads .env for local dev; no-op when env vars are already set

from langchain.agents import create_agent
from langchain_aws import ChatBedrockConverse
from langgraph_checkpoint_aws import AgentCoreMemorySaver

# Bedrock AgentCore App
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

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

# Create agent once at module level so the checkpointer connection is reused.
agent = SimpleLangchainAgent()

@app.entrypoint
def agent_entrypoint(payload, context):
    actor_id = payload.get("actor_id", "default-actor")
    print(f"actor_id: {actor_id}")
    thread_id = payload.get("session_id", context.session_id)
    print(f"thread_id: {thread_id}")
    print(f"payload: {payload}")
    return agent.invoke(payload["message"], actor_id=actor_id, thread_id=thread_id)


if __name__ == "__main__":
    print("Starting the agent...")
    app.run()
