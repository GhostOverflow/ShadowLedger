# ShadowLedger

**Auto-capture pentest commands. Let AI draft your notes.**

ShadowLedger hooks into your terminal during pentests, batches commands intelligently, and uses LLMs to generate documentation in the background. You keep hacking, it keeps notes.


## Who It Helps

- **OSCP/OSEP candidates** juggling multiple labs and losing track of findings
- **HTB/THM players** who want writeups without the post-session grind  
- **Red teamers** who need to document without breaking operator flow
- **Anyone** tired of reconstructing terminal history at 2 AM


## How It Works

1. **Terminal Hook** that Captures commands + output via tmux  
2. **Smart Filtering** Only logs commands with IPs/domains or whitelisted tools  
3. **AI Processing** Batches results and sends to LLM (Groq, OpenRouter, Ollama, etc.)  
4. **Structured Output** Generates phase-based notes with tables, credentials, and narrative

**This isn't magic.** LLMs miss things. Creds get skipped. Narratives drift. You're still the human reviewing the draft. ShadowLedger just cuts 60-70% of the documentation grind so you start with a solid foundation instead of a blank page.


## ⚠️ Security Warning

**DO NOT use with client data on external LLMs.**  

This tool sends terminal output to third-party APIs. Use only with:
- Lab environments (HTB, THM, home labs)
- Training/practice scenarios  
- Non-sensitive testing

**For client engagements:** Use local LLMs (Ollama).


## Requirements

- **OS**: Linux (Arch/Ubuntu/Kali) or macOS  
- **Shell**: Only supports ZSH for the moment 
- **Tools**: `tmux`, `python3`  
- **API Key**: At least one LLM provider (Groq recommended - free tier available)


## Quick Setup

```bash
git clone https://github.com/GhostOverflow/ShadowLedger
cd shadowledger
chmod +x setup.sh
./setup.sh
```

**Setup wizard will:**
1. Copy and paste your shell prompt symbol (`❯`, `$`, `%`)
2. Ask for LLM provider (Groq is free and fast)
3. Request API key
4. Install dependencies


## Usage

**Start daemon:**
```bash
./ledger start
```

**Open tmux (required):**
```bash
tmux
```

**Toggle capturing:**
```bash
ltog  # Turns on auto-capture
```

Now run your pentest commands normally. ShadowLedger watches in the background.


## Commands

| Command | Description |
|---------|-------------|
| `ltog` | Toggle capture on/off |
| `lst` | Check daemon/stack status |
| `Ctrl+P` | Open TUI to review/manage command stack |
| `lsend` | Manually trigger LLM processing |
| `lclear` | Clear command stack |


## Workflow Tips

- **Reorder commands in the TUI before sending** - LLMs can't infer chronology from timestamps alone  
- **Set a reasonable token threshold** (2000-3000) to avoid rate limits  
- **Check the whitelist** - add common tools (`nmap`, `nxc`, `secretsdump`) so they auto-capture  
- **Always review generated notes** - LLMs hallucinate, miss creds, or misinterpret output


## Features

- **Smart Capture** - Only logs commands with IPs, domains, or whitelisted tools  
- **Token-Aware Batching** - Groups commands to stay under API limits  
- **Countdown Timer** - 15-second warning before auto-processing  
- **Interactive TUI** - Review/edit stack with vim keybindings (`j/k`, `d` to delete)  
- **Multiple LLM Providers** - Groq, OpenRouter, HuggingFace, Ollama  
- **Quality Output** - Phase-based narratives with tables, credentials in backticks, MITRE ATT&CK tags


## Configuration

Edit `config.yaml` to:
- Switch LLM providers  
- Adjust token threshold  
- Change output directory  
- Modify system prompts


## Advanced: Intelligence Mode

ShadowLedger includes an **experimental Intelligence Mode** with MCP integration for structured Obsidian vault management.

📖 See `AGENTIC.md` for setup details.

**Note:** Requires Docker Desktop + MCP Gateway. Not needed for basic usage.


## Support

- **Issues**: [GitHub Issues](https://github.com/GhostOverflow/ShadowLedger/issues)  
- **Discord**: `@ghost_overflow`


## License

MIT - Use responsibly. Don't send client data to external APIs.
