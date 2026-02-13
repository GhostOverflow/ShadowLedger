#!/usr/bin/python3
import aiohttp
import asyncio
import os
from typing import Dict, List, Optional
from groq import AsyncGroq
from huggingface_hub import InferenceClient as HFInferenceClient
from openai import AsyncOpenAI


class OpenRouterProvider():
    def __init__(self, model: str = "anthropic/claude-3.5-sonnet",
                 api_key: Optional[str] = None,
                 temperature: float = 0.7, top_p: float = 0.9,
                 timeout: int = 300):
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.timeout = timeout
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key or os.environ.get("OPENROUTER_API_KEY")
        )

    async def generate(self, prompt: str, tools: Optional[List[Dict]] = None) -> str:
        """Async generate text response."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                top_p=self.top_p,
                timeout=self.timeout
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenRouter error: {e}")
            return ""

    async def chat_with_tools(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        """Async chat with tool-calling support."""
        try:
            openai_tools = self._convert_to_openai_tools(
                tools) if tools else None

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                top_p=self.top_p,
                tools=openai_tools,
                timeout=self.timeout
            )

            choice = response.choices[0]
            msg = {
                "role": "assistant",
                "content": choice.message.content
            }

            # Add tool calls if present
            if choice.message.tool_calls:
                msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in choice.message.tool_calls
                ]

            return {"message": msg}
        except Exception as e:
            print(f"OpenRouter chat error: {e}")
            return {"message": {"role": "assistant", "content": ""}}

    def _convert_to_openai_tools(self, mcp_tools: List[Dict]) -> List[Dict]:
        """Convert MCP tools to OpenAI format."""
        return [{
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["inputSchema"]
            }
        } for t in mcp_tools]


class GroqProvider():

    def __init__(self, model: str = "llama-3.3-70b-versatile",
                 api_key: Optional[str] = None,
                 temperature: float = 0.7, top_p: float = 0.9,
                 timeout: int = 300):
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.timeout = timeout
        self.client = AsyncGroq(
            api_key=api_key or os.environ.get("GROQ_API_KEY"))

    async def generate(self, prompt: str, tools: Optional[List[Dict]] = None) -> str:

        try:
            response = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=self.temperature,
                top_p=self.top_p,
                timeout=self.timeout
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Groq error: {e}")
            return ""

    async def chat_with_tools(self, messages: List[Dict], tools: List[Dict]) -> Dict:

        try:
            groq_tools = self._convert_to_groq_tools(tools) if tools else None

            response = await self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                temperature=self.temperature,
                top_p=self.top_p,
                tools=groq_tools,
                timeout=self.timeout
            )

            choice = response.choices[0]
            msg = {
                "role": "assistant",
                "content": choice.message.content
            }

            # Add tool calls if present
            if choice.message.tool_calls:
                msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in choice.message.tool_calls
                ]

            return {"message": msg}
        except Exception as e:
            print(f"Groq chat error: {e}")
            return {"message": {"role": "assistant", "content": ""}}

    def _convert_to_groq_tools(self, mcp_tools: List[Dict]) -> List[Dict]:

        return [{
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["inputSchema"]
            }
        } for t in mcp_tools]


class HuggingFaceProvider():


    def __init__(self, model: str = "meta-llama/Llama-3.3-70B-Instruct",
                 api_key: Optional[str] = None,
                 temperature: float = 0.7, top_p: float = 0.9,
                 timeout: int = 300):
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.timeout = timeout
        self.client = HFInferenceClient(
            api_key=api_key or os.environ.get("HF_TOKEN"))

    async def generate(self, prompt: str, tools: Optional[List[Dict]] = None) -> str:

        try:
            response = await asyncio.to_thread(
                self.client.chat_completion,
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=self.temperature,
                top_p=self.top_p
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"HuggingFace error: {e}")
            return ""

    async def chat_with_tools(self, messages: List[Dict], tools: List[Dict]) -> Dict:

        try:
            hf_tools = self._convert_to_hf_tools(tools) if tools else None

            response = await asyncio.to_thread(
                self.client.chat_completion,
                messages=messages,
                model=self.model,
                temperature=self.temperature,
                top_p=self.top_p,
                tools=hf_tools
            )

            choice = response.choices[0]
            msg = {
                "role": "assistant",
                "content": choice.message.content
            }

            # Add tool calls if present
            if choice.message.tool_calls:
                msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in choice.message.tool_calls
                ]

            return {"message": msg}
        except Exception as e:
            print(f"HuggingFace chat error: {e}")
            return {"message": {"role": "assistant", "content": ""}}

    def _convert_to_hf_tools(self, mcp_tools: List[Dict]) -> List[Dict]:

        return [{
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["inputSchema"]
            }
        } for t in mcp_tools]


class OllamaProvider():

    def __init__(self, model: str = "qwen3:latest", url: str = "http://localhost:11434",
                 temperature: float = 0.7, top_p: float = 0.9,
                 num_ctx: int = 8192, timeout: int = 300):
        self.model = model
        self.url = url
        self.temperature = temperature
        self.top_p = top_p
        self.num_ctx = num_ctx
        self.timeout = timeout

    async def generate(self, prompt: str, tools: Optional[List[Dict]] = None) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "num_ctx": self.num_ctx
            }
        }

        for attempt in range(3):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{self.url}/api/generate", json=payload, timeout=self.timeout) as resp:
                        resp.raise_for_status()
                        data = await resp.json()
                        return data.get("response", "").strip()
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(1 + attempt * 2)
                else:
                    print(f"Ollama error: {e}")
        return ""

    async def chat_with_tools(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        ollama_tools = self._convert_tools_to_ollama(tools)
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": ollama_tools,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "num_ctx": self.num_ctx
            }
        }

        for attempt in range(3):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{self.url}/api/chat", json=payload, timeout=self.timeout) as resp:
                        resp.raise_for_status()
                        return await resp.json()
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(1 + attempt * 2)
                else:
                    print(f"Ollama chat error: {e}")
        return {}

    def _convert_tools_to_ollama(self, mcp_tools: List[Dict]) -> List[Dict]:
        ollama_tools = []
        for tool in mcp_tools:
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("inputSchema", {})
                }
            })
        return ollama_tools
