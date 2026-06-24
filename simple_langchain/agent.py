from langchain.agents import create_agent
from langchain_aws import ChatBedrockConverse

# Bedrock AgentCore App
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

class MyAgent:

    def __init__(self):
        self.llm = ChatBedrockConverse(model="us.amazon.nova-pro-v1:0", region_name="us-east-1")
        self.tools = []
        self.system_prompt = """
        You are a helpful assistant that can answer questions and help with tasks.
        """
        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.system_prompt
        )

    def invoke(self, user_message: str) -> str:
        messages = {"messages": [{"role": "user", "content": user_message}], "response_format": {"type": "json_object"}}
        result = self.agent.invoke(messages)
        return result["messages"][-1].content

@app.entrypoint
def agent_entrypoint(payload, context):
    agent = MyAgent()
    return agent.invoke(payload["message"])


if __name__ == "__main__":
    app.run()