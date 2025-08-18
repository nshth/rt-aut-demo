# import os
# from dotenv import load_dotenv

# from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
# from langchain.agents import create_openai_tools_agent, AgentExecutor
# from langchain_groq import ChatGroq

# # Import the tool
# from backend.agent.tools.check_stock_tool import check_stock_tool

# # Load env
# load_dotenv()
# groq_api_key = os.getenv("GROQ_API_KEY")

# llm = ChatGroq(
#     groq_api_key=groq_api_key,
#     model="llama3-8b-8192",
#     temperature=0.7
# )

# prompt = ChatPromptTemplate.from_messages(
#     [
#         ("system", """You are an intelligent order-taking assistant. 
#         - Extract the product name and quantity from user requests.
#         - Use the tool `check_stock` to verify stock availability.
#         - Reply back to the user in plain language, e.g. 
#           'Yes, 2 laptop stands are available at $25 each' or 
#           'Sorry, only 1 laptop stand is in stock.'"""),
#         MessagesPlaceholder("chat_history", optional=True),
#         ("human", "{input}"),
#         MessagesPlaceholder("agent_scratchpad"),
#     ]
# )

# tools = [check_stock_tool]
# agent = create_openai_tools_agent(llm, tools, prompt)
# agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
