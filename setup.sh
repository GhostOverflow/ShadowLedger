#!/bin/bash
set -e

echo "ShadowLedger Setup"
echo "==================" && echo

REPO="$(cd "$(dirname "$0")" && pwd)"

echo "[1/5] Checking requirements..."
[[ ! "$SHELL" == *"zsh"* ]] && { echo "[-] ZSH required"; exit 1; }
command -v tmux >/dev/null || { echo "[-] TMUX required"; exit 1; }
command -v python3 >/dev/null || { echo "[-] Python3 required"; exit 1; }
echo "[+] Requirements OK" && echo

echo "[2/5] Shell prompt symbol"
echo "Examples: % (zsh) | $ (bash) | ❯ (oh-my-zsh)"
read -p "Your prompt [default: ❯]: " PROMPT
PROMPT=${PROMPT:-❯}
ESC=$(printf '%s\n' "$PROMPT"|sed 's/[[\.*^$()+?{|]/\\&/g')
if sed --version &>/dev/null 2>&1; then
    sed -i "s/prompt_symbol: \".\+\"/prompt_symbol: \"$ESC\"/" "$REPO/config.yaml"
else
    sed -i '' "s/prompt_symbol: \".\+\"/prompt_symbol: \"$ESC\"/" "$REPO/config.yaml"
fi
echo "[+] Using: $PROMPT" && echo

echo "[3/5] Creating directories..."
mkdir -p "$HOME/pentest-notes"
chmod +x "$REPO"/*.py "$REPO/ledger" 2>/dev/null
echo "[+] Created ~/pentest-notes" && echo

echo "[4/5] Installing Python deps..."
if python3 -m pip install --user -q pyyaml groq openai aiohttp 2>/dev/null; then
    echo "[+] Dependencies installed"
elif python3 -m pip install --break-system-packages -q pyyaml huggingface_hub groq openai aiohttp 2>/dev/null; then
    echo "[+] Dependencies installed"
else
    echo "[!] Install manually: pip3 install pyyaml groq openai aiohttp"
fi
echo

echo "[5/5] LLM provider"
echo "1) Groq (fast, recommended)"
echo "2) OpenRouter"
echo "3) HuggingFace"
echo "4) Ollama (local, private)"
echo "5) Skip (configure later in config file)"
read -p "Choice [1-5]: " prov

case "$prov" in
    1)
        echo "Get key: https://console.groq.com/keys"
        read -p "Groq API key: " key
        if [[ -n "$key" ]]; then
            if sed --version &>/dev/null 2>&1; then
                sed -i "/groq:/,/timeout:/ s/api_key: \"\"/api_key: \"$key\"/" "$REPO/config.yaml"
            else
                sed -i '' "/groq:/,/timeout:/ s/api_key: \"\"/api_key: \"$key\"/" "$REPO/config.yaml"
            fi
            echo "[+] Groq configured"
        fi
        ;;
    2)
        echo "Get key: https://openrouter.ai/keys"
        read -p "OpenRouter API key: " key
        if [[ -n "$key" ]]; then
            if sed --version &>/dev/null 2>&1; then
                sed -i "s/provider: \"groq\"/provider: \"openrouter\"/" "$REPO/config.yaml"
                sed -i "/openrouter:/,/timeout:/ s|api_key: \".*\"|api_key: \"$key\"|" "$REPO/config.yaml"
            else
                sed -i '' "s/provider: \"groq\"/provider: \"openrouter\"/" "$REPO/config.yaml"
                sed -i '' "/openrouter:/,/timeout:/ s|api_key: \".*\"|api_key: \"$key\"|" "$REPO/config.yaml"
            fi
            echo "[+] OpenRouter configured"
        fi
        ;;
    3)
        echo "Get token: https://huggingface.co/settings/tokens"
        read -p "HuggingFace token: " key
        if [[ -n "$key" ]]; then
            if sed --version &>/dev/null 2>&1; then
                sed -i "s/provider: \"groq\"/provider: \"huggingface\"/" "$REPO/config.yaml"
                sed -i "/huggingface:/,/timeout:/ s|api_key: \".*\"|api_key: \"$key\"|" "$REPO/config.yaml"
            else
                sed -i '' "s/provider: \"groq\"/provider: \"huggingface\"/" "$REPO/config.yaml"
                sed -i '' "/huggingface:/,/timeout:/ s|api_key: \".*\"|api_key: \"$key\"|" "$REPO/config.yaml"
            fi
            echo "[+] HuggingFace configured"
        fi
        ;;
    4)
        if sed --version &>/dev/null 2>&1; then
            sed -i "s/provider: \"groq\"/provider: \"ollama\"/" "$REPO/config.yaml"
        else
            sed -i '' "s/provider: \"groq\"/provider: \"ollama\"/" "$REPO/config.yaml"
        fi
        echo "[+] Ollama configured (run: ollama pull qwen3)"
        ;;
    5)
        echo "[*] Skipped - edit config.yaml manually"
        ;;
esac
echo

# zshrc integration
if ! grep -q shadowledger ~/.zshrc 2>/dev/null; then
    echo "source $REPO/hook.zsh" >> ~/.zshrc
    echo "[+] Added to ~/.zshrc"
fi

rm -f "$REPO/config.yaml.bak"

echo "[+] Setup complete!"
echo ""
echo "Next:"
echo "  source ~/.zshrc"
echo "  $REPO/ledger start"
echo "  tmux"
echo "  ltog"
echo ""
echo "Commands: ltog lst lstack lsend lclear"