import sys
from backend.agent.chat_agent import agent_executor

yellow = "\033[0;33m"
green = "\033[0;32m"
white = "\033[0;39m"

chat_history = []
print(f"{yellow}---------------------------------------------------------------------------------")
print('I am an order-taking assistant. How can I help you?')
print('---------------------------------------------------------------------------------')

while True:
    query = input(f"{green}Prompt: ")
    if query in ["exit", "quit", "q", "f"]:
        print('Exiting')
        sys.exit()
    if query.strip() == '':
        continue
    result = agent_executor.invoke({"input": query})
    print(f"\n{white}Answer: " + result["output"] + "\n")
    chat_history.append((query, result["output"]))