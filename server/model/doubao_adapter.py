# doubao_adapter.py
# -*- coding: utf-8 -*-
"""
Bridge between OpenAI-style ChatCompletion and Doubao (豆包) model.
Author: <you>
Date  : 2025-08-26
"""

import time
import uuid
from typing import List, Dict, Any, Optional
from volcenginesdkarkruntime import Ark
import json

# ---------------------------------------------------------------------------
# 🔑 1. 你的豆包凭据
# ---------------------------------------------------------------------------
AK = "AKLTMGM4NjZmMTJjZWFiNDI0MmEyZTMzOTU2NjM2ZWQyMDg"
SK = "TmpoaE9UY3pNMlJsT0RCak5EZGtOemhtWmpKaU1EWTJNV0UwTlRRNU56WQ=="
API_KEY = "0403856c-d05b-48ef-9b4a-6661d775d796"
DOUBAO_MODEL = "doubao-1-5-pro-32k-250115"

# 初始化Ark客户端
ark_client = Ark(
    ak=AK,
    sk=SK,
    api_key=API_KEY,
)

# ---------------------------------------------------------------------------
# 2. 主适配类：模仿 openai.ChatCompletion
# ---------------------------------------------------------------------------
class DoubaoChatCompletion:
    """
    用法：
        from doubao_adapter import DoubaoChatCompletion as ChatCompletion

        resp = ChatCompletion.create(
            model="gpt-3.5-turbo",           # 任意占位符，内部会被替换
            messages=[{"role":"user","content":"今天天气？"}],
            temperature=0.7,
        )
        print(resp["choices"][0]["message"]["content"])
    """

    @staticmethod
    def create(
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.9,
        top_p: float = 1.0,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        接口完全兼容 openai.ChatCompletion.create 的常用参数。
        """
        try:
            # 构建请求参数
            request_params = {
                "model": DOUBAO_MODEL,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "stream": stream,
            }
            
            # 添加可选参数
            if max_tokens:
                request_params["max_tokens"] = max_tokens
            
            # 调用豆包API
            completion = ark_client.chat.completions.create(**request_params)
            
            if stream:
            # 流式返回处理
                def gen():
                    for chunk in completion:
                        if chunk.choices and len(chunk.choices) > 0:
                            delta = chunk.choices[0].delta
                            content = getattr(delta, 'content', '') or ''
                            finish_reason = getattr(chunk.choices[0], 'finish_reason', None)
                            
                            yield {
                                "choices": [{
                                    "delta": {"content": content},
                                "finish_reason": finish_reason
                            }]
                        }
                return gen()

                # 非流式返回处理
            message = completion.choices[0].message
            content = message.content or ""
                
            # 转换为OpenAI格式
            created = int(time.time())
            choice = {
                "index": 0,
                "finish_reason": getattr(completion.choices[0], 'finish_reason', 'stop'),
                "message": {
                    "role": "assistant",
                    "content": content,
                },
            }
        
            # 使用情况统计
            usage = {
                "prompt_tokens": completion.usage.prompt_tokens if hasattr(completion, 'usage') and completion.usage else 0,
                "completion_tokens": completion.usage.completion_tokens if hasattr(completion, 'usage') and completion.usage else 0,
                "total_tokens": completion.usage.total_tokens if hasattr(completion, 'usage') and completion.usage else 0,
            }

            return {
                "id": getattr(completion, 'id', str(uuid.uuid4())),
                "object": "chat.completion",
                "created": created,
                "model": model,
                "choices": [choice],
                "usage": usage,
            }
        
        except Exception as e:
            raise RuntimeError(f"Doubao API error: {str(e)}")