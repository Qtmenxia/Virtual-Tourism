from typing import List
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.prompt_values import ChatPromptValue
from model.doubao_adapter import DoubaoChatCompletion
from collections.abc import Iterator

class ChatDoubaoLM(BaseChatModel):
    model_name: str = "doubao-1-5-pro-32k-250115"
    temperature: float = 0.7

    def _convert_messages(self, messages: List[BaseMessage]) -> List[dict]:
        """将LangChain消息格式转换为豆包API格式"""
        converted_messages = []
        for m in messages:
            if isinstance(m, (str, list)):
                if isinstance(m, list) and len(m) == 2:
                    role, content = m
                    role = self._normalize_role(role)
                    converted_messages.append({"role": role, "content": content})
                elif isinstance(m, str):
                    converted_messages.append({"role": "user", "content": m})
            else:
                role = m.type if hasattr(m, 'type') else 'user'
                content = m.content if hasattr(m, 'content') else str(m)
                role = self._normalize_role(role)
                converted_messages.append({"role": role, "content": content})
        
        return converted_messages

    def _normalize_role(self, role: str) -> str:
        """标准化角色名称，确保符合豆包API要求"""
        role_mapping = {
            "human": "user",
            "ai": "assistant",
            "assistant": "assistant",
            "system": "system",
            "user": "user",
            "tool": "tool"
        }
        return role_mapping.get(role.lower(), "user")

    def _generate(self, messages: List[BaseMessage], **kwargs) -> ChatResult:
        """生成单次对话响应"""
        try:
            converted_messages = self._convert_messages(messages)
            print(f"DEBUG - Converted messages: {converted_messages}")
            
            payload = DoubaoChatCompletion.create(
                model=self.model_name,
                messages=converted_messages,
                temperature=self.temperature,
                **kwargs
            )
            message_content = payload["choices"][0]["message"]["content"]
            return ChatResult(
                generations=[
                    ChatGeneration(
                        text=message_content,
                        message=AIMessage(content=message_content)
                    )
                ]
            )
        except Exception as e:
            raise RuntimeError(f"Failed to generate response: {str(e)}")
    
    def stream_generate(self, messages: List[BaseMessage], **kwargs) -> Iterator[str]:
        """流式返回，每次 yield 一段新文本，适配 LCEL/Agent streaming 场景。"""
        try:
            resp_iter = DoubaoChatCompletion.create(
                model=self.model_name,
                messages=self._convert_messages(messages),
                temperature=self.temperature,
                stream=True,
                **kwargs
            )
            for chunk in resp_iter:
                if chunk["choices"] and len(chunk["choices"]) > 0:
                    delta_content = chunk["choices"][0]["delta"].get("content", "")
                    if delta_content:
                        yield delta_content
        except Exception as e:
            raise RuntimeError(f"Failed to stream generate: {str(e)}")
    
    def invoke(self, input_data, config=None, **kwargs):
        """处理invoke调用，支持不同的输入格式"""
        if config is not None:
            kwargs.update(config.get('kwargs', {}))
        
        if isinstance(input_data, str):
            messages = [HumanMessage(content=input_data)]
        elif isinstance(input_data, dict):
            if "raw_response" in input_data:
                messages = [HumanMessage(content=input_data["raw_response"])]
            else:
                raise ValueError("Invalid dictionary input: 'raw_response' key is required")
        elif isinstance(input_data, list):
            if len(input_data) == 2 and isinstance(input_data[0], str) and isinstance(input_data[1], str):
                role, content = input_data
                normalized_role = self._normalize_role(role)
                if normalized_role == "user":
                    messages = [HumanMessage(content=content)]
                elif normalized_role == "system":
                    messages = [SystemMessage(content=content)]
                elif normalized_role == "assistant":
                    messages = [AIMessage(content=content)]
                else:
                    messages = [HumanMessage(content=content)]
            else:
                messages = input_data
        elif isinstance(input_data, BaseMessage):
            messages = [input_data]
        elif isinstance(input_data, ChatPromptValue):
            messages = input_data.messages  # 提取 ChatPromptValue 中的消息列表
        else:
            raise ValueError(f"Unsupported input type: {type(input_data)}")
        
        result = self._generate(messages, **kwargs)
        return result.generations[0].message
    
    @property
    def _llm_type(self) -> str:
        return "doubao-chat"