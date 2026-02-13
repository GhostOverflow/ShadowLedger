#!/usr/bin/python3
import asyncio
import json
from pathlib import Path
from datetime import datetime
import yaml
import re
from llm_provider import GroqProvider, OpenRouterProvider, HuggingFaceProvider, OllamaProvider

try:
    from mcp import ClientSession
    from mcp.client.sse import sse_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

TRIGGER = Path("/tmp/ldr_trigger")
REPO = Path(__file__).parent
LOG = Path("/tmp/shadowledger.log")


def log(msg, prefix="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {prefix}: {msg}\n"
    LOG.write_text(LOG.read_text() + line if LOG.exists() else line)
    print(line.rstrip())


def strip_ansi(txt):
    return re.sub(r'\x1B[@-Z\[-_]|\[[0-?]*[ -/]*[@-~]', '', txt)


class StackManager:
    def __init__(self, path, threshold=2000):
        self.path = Path(path)
        self.threshold = threshold
        self.data = self._load()

    def _load(self):
        try:
            return json.loads(self.path.read_text()) if self.path.exists() else {"commands": [], "total_tokens": 0}
        except:
            return {"commands": [], "total_tokens": 0}

    def _save(self):
        self.path.parent.mkdir(exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2))

    def estimate_tokens(self, txt):
        clean = strip_ansi(txt)
        clean = re.sub(r'\s+', ' ', clean)
        return len(clean) // 4

    def push(self, cmd, out):
        tokens = self.estimate_tokens(cmd + out)
        entry = {
            "timestamp": datetime.now().timestamp(),
            "command": cmd,
            "output": out,
            "tokens": tokens
        }
        self.data["commands"].append(entry)
        self.data["total_tokens"] += tokens
        self._save()
        return self.data["total_tokens"] >= self.threshold

    def pop_by_index(self, idx):
        if 0 <= idx < len(self.data["commands"]):
            e = self.data["commands"].pop(idx)
            self.data["total_tokens"] -= e["tokens"]
            self._save()
            return e

    def get_content(self):
        parts = [
            f"$ {c['command']}\n{c['output']}" for c in self.data["commands"]]
        return "\n\n".join(parts)

    def clear(self):
        n = len(self.data["commands"])
        self.data = {"commands": [], "total_tokens": 0}
        self._save()
        print(f"[*] Cleared {n} commands")

    def status(self):
        c = len(self.data["commands"])
        t = self.data["total_tokens"]
        pct = (t/self.threshold*100) if self.threshold > 0 else 0
        return f"Stack: {c} cmds | {t}/{self.threshold}t ({pct:.0f}%)"


async def process_batch(llm, stack_file, out_dir, pattern, prompt):
    if not stack_file.exists():
        return

    try:
        stack = StackManager(stack_file)
        cmds = stack.data.get("commands", [])
        if not cmds:
            return

        content = strip_ansi(stack.get_content())
        log(f"Processing {len(cmds)} commands ({len(content)} chars)")

        notes = await llm.generate(f"{prompt}\n\nDocument this:\n\n{content}")

        if notes.strip():
            out_path = Path(out_dir).expanduser()
            out_path.mkdir(parents=True, exist_ok=True)

            date = datetime.now().strftime('%Y-%m-%d')
            fname = pattern.replace('{date}', date)
            fpath = out_path / fname

            header = f"\n\n---\n**Auto-added {datetime.now().strftime('%Y-%m-%d %H:%M')}**\n\n"

            with open(fpath, 'a') as f:
                f.write(header + notes)

            log(f"Wrote to {fpath}")
            stack.clear()

    except Exception as e:
        log(f"Error: {e}", "ERR")


async def process_batch_mcp(llm, session, obs_tools, stack_file, prompt, target_note):
    if not stack_file.exists():
        return
    stack = StackManager(stack_file)
    cmds = stack.data.get("commands", [])
    if not cmds:
        return
    try:
        log(f"Processing {len(cmds)} commands")

        combined = "\n\n".join(
            [f"Command: {c['command']}\nOutput:\n{c['output'][:2000]}" for c in cmds])
        messages = [
            {"role": "system", "content": prompt + f"\n\nTarget note file: {target_note}"},
            {"role": "user", "content": combined}
        ]

        total_calls = 0
        while total_calls < 10:
            resp = await llm.chat_with_tools(messages, obs_tools)
            msg = resp.get("message", {})
            tcalls = msg.get("tool_calls", [])

            if not tcalls:
                break

            messages.append(msg)

            for tc in tcalls:
                if total_calls >= 10:
                    log("Max tool calls", "WARN")
                    break
                try:
                    func = tc["function"]
                    args = json.loads(func["arguments"]) if isinstance(func["arguments"], str) else func["arguments"]
                    result = await session.call_tool(func["name"], arguments=args)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", ""),
                        "content": str(result.content) if hasattr(result, 'content') else str(result)
                    })

                    log(f"Tool {func['name']}: ok")
                    total_calls += 1
                except Exception as te:
                    log(f"Tool {func['name']}: {te}", "ERR")
                    messages.append({
                        "role": "tool", 
                        "tool_call_id": tc.get("id", ""),
                        "content": f"Error: {te}"
                    })
        stack.clear()
        log(f"Batch complete ({total_calls} calls)")
    except Exception as e:
        log(f"MCP error: {e}", "ERR")

async def daemon():
    log("ShadowLedger daemon starting")
    cfg = yaml.safe_load((REPO / "config.yaml").read_text())

    prov = cfg["llm"]["provider"]
    providers = {
        "groq": GroqProvider,
        "openrouter": OpenRouterProvider,
        "huggingface": HuggingFaceProvider,
        "ollama": OllamaProvider
    }
    if prov not in providers:
        log(f"Unknown provider: {prov}", "ERR")
        return

    pcfg = cfg["llm"][prov]
    llm = providers[prov](**pcfg)

    log(f"Provider: {prov} | Model: {llm.model}")

    stack_path = REPO / cfg["stack"]["stack_file"].lstrip('./')
    intel_mode = cfg.get("intelligence_mode", False)
    if intel_mode:
        if not MCP_AVAILABLE:
            log("Intelligence mode needs mcp package: pip install mcp", "ERR")
            return

        gw_url = cfg["mcp"]["gateway_url"]
        target_note = cfg["mcp"].get("target_note", "notes.md")
        prompt = cfg.get("system_prompt_intelligence") or cfg.get("system_prompt_simple", "")
        
        log(f"Mode: intelligence | Gateway: {gw_url} | Note: {target_note}")

        try:
            async with sse_client(gw_url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    tools_result = await session.list_tools()
                    obs_tools = [{"name": t.name, "description": t.description, "inputSchema": t.inputSchema}
                                 for t in tools_result.tools]

                    log(f"Connected ({len(obs_tools)} tools)")
                    log("Ready")

                    last_ping = datetime.now()

                    while True:
                        try:
                            # keepalive every 60s
                            if (datetime.now() - last_ping).seconds > 60:
                                await session.list_tools()
                                last_ping = datetime.now()
                                log("Ping", "DEBUG")

                            if TRIGGER.exists():
                                TRIGGER.unlink()
                                log("Processing triggered")
                                await process_batch_mcp(llm, session, obs_tools, stack_path, prompt, target_note)

                            await asyncio.sleep(0.5)

                        except KeyboardInterrupt:
                            log("Stopped by user")
                            break

        except Exception as e:
            log(f"MCP connection error: {e}", "ERR")
    else:
        out_dir = cfg["output"]["directory"]
        pattern = cfg["output"]["filename_pattern"]
        prompt = cfg.get("system_prompt_simple") or cfg.get("system_prompt", "")

        log(f"Mode: simple | Output: {out_dir}/{pattern}")
        log("Ready")

        while True:
            try:
                if TRIGGER.exists():
                    TRIGGER.unlink()
                    log("Processing triggered")
                    await process_batch(llm, stack_path, out_dir, pattern, prompt)

                await asyncio.sleep(0.5)

            except KeyboardInterrupt:
                log("Stopped by user")
                break
            except Exception as e:
                log(f"Error: {e}", "ERR")
                await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(daemon())