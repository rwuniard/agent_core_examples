from agent import MyAgent

def main():
    agent = MyAgent()
    while True:
        user_message = input("You: ")
        if user_message.lower() == "exit":
            break
        response = agent.invoke(user_message)
        print(f"Agent: {response}")


if __name__ == "__main__":
    main()
