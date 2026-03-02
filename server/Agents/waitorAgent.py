import os
from dotenv import load_dotenv
load_dotenv()
from model.chatdoubaollm import ChatDoubaoLM
from tools.camera import get_image, preprocess_image
from tools.modelpredict  import predict_image
from langchain.agents import initialize_agent, AgentType, AgentExecutor, create_openai_tools_agent, Tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain.prompts import PromptTemplate
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.utilities import SerpAPIWrapper

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

class waitorAgent:
    def __init__(self):
        self.model = ChatDoubaoLM(
            model_name="doubao-1-5-pro-32k-250115",
            temperature=0.7,
        )
        self.memory = MemorySaver()
        self.template = """
        你是一个校园景点介绍助手
        """
        self.prompt = PromptTemplate.from_template(self.template)
        self.tools = [
            Tool(
                name="search",
                func=SerpAPIWrapper().run,
                description="useful for when you want to answer questions about current events",
            )
        ]
        self.agent = create_react_agent(
            model=self.model,
            tools=self.tools,
            checkpointer=self.memory,
            verbose=True,
            agent_type=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
        )
