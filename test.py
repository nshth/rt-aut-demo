import sys
import requests
from dotenv import load_dotenv

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_groq import ChatGroq

from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

load_dotenv('.env')

API_URL = "http://127.0.0.1:8000/check-stock"  # Your FastAPI backend


@tool
def check_stock(productName: str, quantity: int) -> dict:
    """Check if a given product is in stock with the required quantity."""
    payload = {"productName": productName, "quantity": quantity}
    response = requests.post(API_URL, json=payload)

    if response.status_code != 200:
        return {"error": response.json().get("detail", "Unknown error")}

    return response.json()


prompt = ChatPromptTemplate.from_messages(
    [
        ("system", """You are an intelligent order-taking assistant.
        - Extract the product name and quantity from user requests.
        - Use the tool `check_stock` to verify stock availability.
        - Reply to the customer clearly with availability and price.
        
        Example:
        Human: I want 2 laptop stands
        AI: Yes, 2 Laptop Stands are available at $25 each.
        """),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)

# Choose the LLM that will drive the agent
llm = ChatGroq(model="deepseek-r1-distill-llama-70b", temperature=0)

# Setup the toolkit
toolkit = [check_stock]

# Construct the OpenAI Tools agent
agent = create_openai_tools_agent(llm, toolkit, prompt)

# Create an agent executor by passing in the agent and tools
agent_executor = AgentExecutor(agent=agent, tools=toolkit, verbose=True)

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
