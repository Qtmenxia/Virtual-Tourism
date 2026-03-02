from model.chatdoubaollm import ChatDoubaoLM
from tools.camera import get_image, preprocess_image
from tools.modelpredict import predict_image
from langchain.agents import Tool
from langgraph.prebuilt import create_react_agent
from langchain.prompts import PromptTemplate
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Dict, Any

school_labels = [
    "一校区主楼",
    "校部楼",
    "行政楼",
    "科学园航天馆",
    "一校区图书馆",
    "科学园卧震苍穹",
]


class ConversationSummarizer:
    """对话摘要器 - 替代 SummarizationMiddleware"""
    
    def __init__(self, llm, max_history_tokens: int = 3000, messages_to_keep: int = 4):
        self.llm = llm
        self.max_history_tokens = max_history_tokens
        self.messages_to_keep = messages_to_keep
        
    def estimate_tokens(self, text: str) -> int:
        """估算文本的 token 数量"""
        return len(text) // 4  # 粗略估算：1 token ≈ 4 字符
    
    def should_summarize(self, messages: List[BaseMessage]) -> bool:
        """判断是否需要进行摘要"""
        total_tokens = sum(self.estimate_tokens(str(m.content)) for m in messages)
        return total_tokens > self.max_history_tokens
    
    async def summarize_async(self, messages: List[BaseMessage]) -> str:
        """异步摘要历史消息"""
        conversation_text = "\n".join([
            f"{msg.__class__.__name__}: {msg.content}" 
            for msg in messages
        ])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "请简洁地总结以下对话的关键信息和上下文，保留重要的事实和用户意图："),
            ("user", "{conversation}")
        ])
        
        chain = prompt | self.llm
        result = await chain.ainvoke({"conversation": conversation_text})
        
        return result.content
    
    def summarize(self, messages: List[BaseMessage]) -> str:
        """同步摘要历史消息"""
        conversation_text = "\n".join([
            f"{msg.__class__.__name__}: {msg.content}" 
            for msg in messages
        ])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "请简洁地总结以下对话的关键信息和上下文，保留重要的事实和用户意图："),
            ("user", "{conversation}")
        ])
        
        chain = prompt | self.llm
        result = chain.invoke({"conversation": conversation_text})
        
        return result.content
    
    async def process_async(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """异步处理消息列表，必要时进行摘要"""
        if not messages:
            return messages
            
        if not self.should_summarize(messages):
            return messages
        
        # 分离系统消息、旧消息和最近消息
        system_messages = [m for m in messages if isinstance(m, SystemMessage)]
        non_system_messages = [m for m in messages if not isinstance(m, SystemMessage)]
        
        if len(non_system_messages) <= self.messages_to_keep:
            return messages
        
        # 保留最近的消息
        recent_messages = non_system_messages[-self.messages_to_keep:]
        old_messages = non_system_messages[:-self.messages_to_keep]
        
        # 摘要旧消息
        summary_text = await self.summarize_async(old_messages)
        summary_message = SystemMessage(content=f"[对话历史摘要]：\n{summary_text}")
        
        # 组合结果：系统消息 + 摘要 + 最近消息
        return system_messages + [summary_message] + recent_messages
    
    def process(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """同步处理消息列表，必要时进行摘要"""
        if not messages:
            return messages
            
        if not self.should_summarize(messages):
            return messages
        
        # 分离系统消息、旧消息和最近消息
        system_messages = [m for m in messages if isinstance(m, SystemMessage)]
        non_system_messages = [m for m in messages if not isinstance(m, SystemMessage)]
        
        if len(non_system_messages) <= self.messages_to_keep:
            return messages
        
        # 保留最近的消息
        recent_messages = non_system_messages[-self.messages_to_keep:]
        old_messages = non_system_messages[:-self.messages_to_keep]
        
        # 摘要旧消息
        summary_text = self.summarize(old_messages)
        summary_message = SystemMessage(content=f"[对话历史摘要]：\n{summary_text}")
        
        # 组合结果：系统消息 + 摘要 + 最近消息
        return system_messages + [summary_message] + recent_messages


class PredictAgent:
    def __init__(self):
        self.model = ChatDoubaoLM(
            model_name="doubao-1-5-pro-32k-250115",
            temperature=0.7,
        )
        
        self.system_prompt = f"""
        你是一个校园景点识别助手。你可以通过摄像头拍照并识别以下景点：
        {', '.join(school_labels)}
        你有以下工具可以使用：
        1. predict_tool：从摄像头获取图像并预测景点
        当用户询问当前位置或要求识别景点时，请使用 predict_tool 工具。
        请用友好的方式回答用户的问题。\
        """        
        self.tools = [
            Tool(
                name="predict_tool",
                func=self.predict_tool,
                description="useful when you want to predict the location of the picture. Input should be 'camera' or image source.",
            ),
        ]        
        self.checkpointer = MemorySaver()
        self.summarizer = ConversationSummarizer(
            llm=self.model,
            max_history_tokens=3000, 
            messages_to_keep=4,
        )
        self.agent = create_react_agent(
            model=self.model,
            tools=self.tools,
            checkpointer=self.checkpointer,
        )
    
    def predict_tool(self, source: str = "camera") -> str:
        """预测工具"""
        try:
            image = get_image(source=source)
            result = predict_image(image)
            return f"识别结果：{result}"
        except Exception as e:
            return f"识别失败：{str(e)}"
    
    async def chat_async(self, user_message: str, thread_id: str = "default") -> Dict[str, Any]:
        """异步聊天方法，自动使用摘要处理历史消息"""
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            state = await self.agent.aget_state(config)
            current_messages = state.values.get("messages", [])
            if current_messages:
                print(f"[DEBUG] 处理前消息数: {len(current_messages)}")
                processed_messages = await self.summarizer.process_async(current_messages)
                print(f"[DEBUG] 处理后消息数: {len(processed_messages)}")
                if len(processed_messages) != len(current_messages):
                    print("[DEBUG] 消息已被摘要，更新状态...")
                    await self.agent.aupdate_state(
                        config,
                        {"messages": processed_messages}
                    )
            if not current_messages:
                input_messages = [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=user_message)
                ]
            else:
                input_messages = [HumanMessage(content=user_message)]
            result = await self.agent.ainvoke(
                {"messages": input_messages},
                config=config
            )            
            return result
        except Exception as e:
            print(f"[ERROR] 异步聊天出错: {str(e)}")
            return {
                "messages": [AIMessage(content=f"出错了：{str(e)}")],
                "error": str(e)
            }
    
    def chat(self, user_message: str, thread_id: str = "default") -> str:
        """同步聊天方法，自动使用摘要处理历史消息"""
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            # 获取当前对话状态
            state = self.agent.get_state(config)
            current_messages = state.values.get("messages", [])
            
            # 使用摘要器处理历史消息
            if current_messages:
                print(f"[DEBUG] 处理前消息数: {len(current_messages)}")
                processed_messages = self.summarizer.process(current_messages)
                print(f"[DEBUG] 处理后消息数: {len(processed_messages)}")
                
                # 如果消息被摘要了，更新状态
                if len(processed_messages) != len(current_messages):
                    print("[DEBUG] 消息已被摘要，更新状态...")
                    self.agent.update_state(
                        config,
                        {"messages": processed_messages}
                    )
            
            # 构建输入消息
            if not current_messages:
                # 第一次对话，添加系统提示
                input_messages = [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=user_message)
                ]
            else:
                input_messages = [HumanMessage(content=user_message)]
            
            # 调用 agent
            result = self.agent.invoke(
                {"messages": input_messages},
                config=config
            )
            
            # 提取最后的 AI 回复
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                return last_message.content if hasattr(last_message, 'content') else str(last_message)
            
            return "没有收到回复"
            
        except Exception as e:
            print(f"[ERROR] 同步聊天出错: {str(e)}")
            return f"出错了：{str(e)}"
    
    def reset_conversation(self, thread_id: str = "default"):
        """重置特定线程的对话历史"""
        config = {"configurable": {"thread_id": thread_id}}
        try:
            self.agent.update_state(config, {"messages": []})
            return "对话历史已重置"
        except Exception as e:
            return f"重置失败：{str(e)}"
    
    def get_conversation_stats(self, thread_id: str = "default") -> Dict[str, Any]:
        """获取对话统计信息"""
        config = {"configurable": {"thread_id": thread_id}}
        try:
            state = self.agent.get_state(config)
            messages = state.values.get("messages", [])
            
            total_tokens = sum(self.summarizer.estimate_tokens(str(m.content)) for m in messages)
            
            return {
                "total_messages": len(messages),
                "estimated_tokens": total_tokens,
                "should_summarize": self.summarizer.should_summarize(messages),
                "system_messages": sum(1 for m in messages if isinstance(m, SystemMessage)),
                "user_messages": sum(1 for m in messages if isinstance(m, HumanMessage)),
                "ai_messages": sum(1 for m in messages if isinstance(m, AIMessage)),
            }
        except Exception as e:
            return {"error": str(e)}
    
    # 保留旧的 run 方法以保持向后兼容
    def run(self, input_text: str, thread_id: str = "default") -> str:
        """运行 agent（向后兼容的方法）"""
        return self.chat(input_text, thread_id)


if __name__ == "__main__":
    # 测试代码
    agent = PredictAgent()
    
    print("=" * 60)
    print("测试 1: 简单对话")
    print("=" * 60)
    response1 = agent.chat("你好，你能做什么？")
    print(f"回复: {response1}\n")
    stats1 = agent.get_conversation_stats()
    print(f"对话统计: {stats1}\n")
    
    print("=" * 60)
    print("测试 2: 请求识别景点")
    print("=" * 60)
    response2 = agent.chat("帮我识别一下当前位置")
    print(f"回复: {response2}\n")
    stats2 = agent.get_conversation_stats()
    print(f"对话统计: {stats2}\n")
    
    print("=" * 60)
    print("测试 3: 继续对话（测试历史记忆）")
    print("=" * 60)
    response3 = agent.chat("刚才识别的是什么地方？")
    print(f"回复: {response3}\n")
    stats3 = agent.get_conversation_stats()
    print(f"对话统计: {stats3}\n")
    
    # 模拟长对话以触发摘要
    print("=" * 60)
    print("测试 4: 模拟长对话以触发摘要")
    print("=" * 60)
    for i in range(10):
        response = agent.chat(f"这是第 {i+1} 轮对话，请告诉我一些关于校园景点的信息。")
        print(f"第 {i+1} 轮回复: {response[:100]}...")
        stats = agent.get_conversation_stats()
        print(f"统计: 消息数={stats['total_messages']}, Token数={stats['estimated_tokens']}, 需要摘要={stats['should_summarize']}\n")
    
    print("=" * 60)
    print("测试 5: 使用不同的 thread_id")
    print("=" * 60)
    response4 = agent.chat("你好", thread_id="user_123")
    print(f"回复: {response4}\n")
    
    print("=" * 60)
    print("测试 6: 重置对话")
    print("=" * 60)
    reset_msg = agent.reset_conversation()
    print(f"{reset_msg}")
    stats_after_reset = agent.get_conversation_stats()
    print(f"重置后统计: {stats_after_reset}\n")
    
    # 异步测试示例（可选）
    """
    import asyncio
    
    async def test_async():
        print("=" * 60)
        print("异步测试")
        print("=" * 60)
        result = await agent.chat_async("异步测试：帮我识别景点")
        messages = result.get("messages", [])
        if messages:
            last_msg = messages[-1]
            content = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
            print(f"异步回复: {content}")
    
    asyncio.run(test_async())
    """


