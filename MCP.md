# Intelligence Mode - MCP Integration

**Advanced feature for power users with extensive token budget and Docker Desktop.**

Intelligence Mode uses Model Context Protocol (MCP) to give the LLM structured access to your Obsidian vault, enabling smarter note organization beyond simple appending.


## ⚠️ Prerequisites

- **Docker Desktop** (required for MCP Gateway)
- **Obsidian** (with vault configured and local rest API plugin installed)
- **Higher token budget** (5x more tokens than simple mode)
- **MCP knowledge** (basic understanding helpful)

**If you just want auto-notes:** Stick to simple mode. Intelligence Mode is optional.


## What It Does Differently

### Simple Mode (Default):
- Captures commands then sends to LLM then appends output to flat markdown file
- Fast, cheap, works for 90% of users

### Intelligence Mode:
- Captures commands then LLM queries existing note structure and appends under appropriate headings or creates new sections if needed
- Uses MCP tools like:
  - `obsidian_get_headings` - See current note structure
  - `obsidian_append_under_heading` - Add content to specific section
  - `obsidian_search` - Check what's already documented
  - `obsidian_create_heading` - Organize new findings

**Result:** Structured notes instead of chronological dumps.


## Setup

### 1. Install MCP Package

```bash
pip install mcp
```

### 2. Start Docker Desktop

Make sure Docker Desktop is running (required for MCP Gateway).

### 3. Configure MCP Gateway

**Install MCP Gateway:**

Follow instructions at: https://github.com/modelcontextprotocol/gateway

**Or quick setup:**
```bash
cd ShadowLedger
docker compose up -d
```

### 4. Add Obsidian MCP Server

MCP Gateway supports 200+ servers. For ShadowLedger, you need the Obsidian server. You can use other servers as well if you need like web serarch, etc

**In Docker Desktop:**
- Open MCP Gateway interface (http://localhost:8811)
- Search for "Obsidian" server
- Click to enable
- Configure the API key you got from plugin


### 5. Enable Intelligence Mode

Edit `config.yaml`:

```yaml
intelligence_mode: true

mcp:
  gateway_url: "http://localhost:8811/sse"
  target_note: "pentesting/current-engagement.md"

```

## Usage

**Start daemon with Intelligence Mode:**
```bash
./ledger start
```

It will automatically detect `intelligence_mode: true` in config.

**Toggle capturing (same as before):**
```bash
ltog
```

**Trigger processing:**
```bash
lsend
```

**Check logs:**
```bash
tail -f /tmp/shadowledger.log
```

You'll see entries like:
```
[12:34:56] INFO: Mode: intelligence | Gateway: http://localhost:8811/sse
[12:35:10] INFO: Got 12 tools from gateway
[12:35:15] INFO: Executing 3 tool calls (iteration 1)
[12:35:18] INFO: Tool obsidian_append_under_heading: ok
```

## How It Works

1. **Command batch ready** → Daemon triggers processing
2. **LLM receives:** Commands + output + available MCP tools
3. **LLM decides:** "This is SMB enumeration, I'll append under 'Initial Access' heading"
4. **Tool call:** `obsidian_append_under_heading(heading="Initial Access", content="...")`
5. **Repeat:** LLM continues processing remaining commands with tool calls
6. **Done:** Notes organized by phase/category instead of chronological dump


## Cost Comparison

**Simple Mode (2000 tokens/batch):**
- Input: 2000 tokens
- Output: ~500 tokens

**Intelligence Mode (same content):**
- Input: 2000 tokens + tool definitions + conversation turns
- Output: ~500 tokens + multiple tool calls
- Total: ~5000-8000 tokens per batch


**5x more expensive, slightly better organization.**


## Troubleshooting

### "MCP package not installed"
```bash
pip install mcp
```

### "Cannot connect to gateway"
Check Docker Desktop is running:
```bash
docker ps | grep mcp-gateway
```

Restart gateway:
```bash
docker restart mcp-gateway
```

### "No tools returned from gateway"
- Verify Obsidian server is enabled in gateway
- Check vault path is correct
- Restart gateway after config changes

### "Tool calls failing"
Check `/tmp/shadowledger.log` for specific errors:
```bash
tail -f /tmp/shadowledger.log
```

Common issues:
- Vault path incorrect
- Heading doesn't exist (LLM should create it first)
- Obsidian not running


## When To Use Intelligence Mode

**Use it if:**
- You have token budget for 10x cost
- You want highly structured notes (organized by attack phase)
- You're documenting long engagements (multi-day)
- You use Obsidian for all pentesting notes

**Don't use it if:**
- You're on free API tiers (will burn tokens fast)
- Simple chronological notes work fine for you
- You don't use Obsidian
- You're just starting with ShadowLedger (learn simple mode first)


## Alternative: DIY Structured Output

**Don't want MCP complexity?**

You can get 80% of the benefit by:
1. Using simple mode
2. Modifying the system prompt to include phase headers
3. Manually organizing output in your editor

Intelligence Mode is for power users who want maximum automation and have the token budget for it.


## Support

**Intelligence Mode issues:**
- Check MCP Gateway docs: https://github.com/modelcontextprotocol/gateway
- ShadowLedger issues: https://github.com/GhostOverflow/ShadowLedger/issues
- Discord: `@ghost_overflow`

**Note:** Intelligence Mode is experimental. Simple mode is the recommended default.
