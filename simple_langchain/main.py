from agent import SimpleLangchainAgent
import asyncio


async def stream_reply(agent: SimpleLangchainAgent, user_message: str) -> None:
    print("Agent: ", end="", flush=True)
    async for chunk in agent.astream(
        user_message,
        actor_id="test-actor-2",
        thread_id="f0942990-b1b5-4754-b25d-a3bd98233b1b",
    ):
        print(chunk, end="", flush=True)
    print()


def main():
    agent = SimpleLangchainAgent()   # async entrypoint
    while True:
        user_message = input("You: ")
        if user_message.lower() == "exit":
            break
        asyncio.run(stream_reply(agent, user_message))
        # blocking (non-streaming) alternative:
        # response = asyncio.run(agent.invoke_async(user_message, actor_id="test-actor-2", thread_id="..."))
        # sync entrypoint
        # response = agent.invoke(user_message)


if __name__ == "__main__":
    main()
