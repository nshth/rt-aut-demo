import asyncio
import warnings
from backend.agent.chat_agent import create_agent_executor
from langchain.agents import AgentExecutor

# --- Silencing deprecation warnings ---
warnings.filterwarnings("ignore", category=DeprecationWarning)

# --- CLI colors ---
YELLOW = "\033[0;33m"
GREEN = "\033[0;32m"
WHITE = "\033[0;39m"

async def main():
    # Header
    print(f"{YELLOW}" + "-"*81)
    print('I am an order-taking assistant. How can I help you?')
    print("-"*81 + f"{WHITE}")

    # Session & memory
    session_id = "cli_test_user"  # fake session ID for testing
    # Agent executor
    agent_executor = create_agent_executor(session_id, from_number)

    # Main loop
    while True:
        query = input(f"{GREEN}Prompt: ").strip()
        if query.lower() in ["exit", "quit", "q", "f"]:
            print("Exiting")
            break
        if not query:
            continue

        response = await agent_executor.ainvoke({"input": query})
        print(f"\n{WHITE}Answer: {response.get('output', 'No output returned')}\n")

if __name__ == "__main__":
    asyncio.run(main())

