#!/bin/zsh

LEDGER_DIR="$(cd "$(dirname "${(%):-%x}")" && pwd)"
LEDGER_STACK="$LEDGER_DIR/stack.json"
LEDGER_WHITELIST="$LEDGER_DIR/whitelist.txt"
LEDGER_ENABLED=0
LEDGER_PYTHON="/usr/bin/python3"
LEDGER_MARKER=$'<<<LEDGER_END>>>\r                              '
LEDGER_LAST=""

LEDGER_HOSTS=""
if [[ -f /etc/hosts ]]; then
    LEDGER_HOSTS=$(grep -v '^#' /etc/hosts | \
                   grep -vE '(127\.0\.0\.1|::1|localhost)' | \
                   awk 'NF>=2 {for(i=2;i<=NF;i++) print $i}' | \
                   grep -v '^$' | sort -u | tr '\n' '|' | sed 's/|$//')
fi

update_tmux_status() {
    [ -z "$TMUX" ] && return
    local st="[OFF] "
    [[ $LEDGER_ENABLED -eq 1 ]] && st="[ON]"
    
    if [[ -f "$LEDGER_STACK" ]]; then
        local info=$($LEDGER_PYTHON -c "
import json
try:
    d=json.loads(open('$LEDGER_STACK').read())
    c,t=len(d.get('commands',[])),d.get('total_tokens',0)
    print(f' {c}/{t}t') if c>0 else None
except:pass
" 2>/dev/null)
        st="${st}${info}"
    fi
    tmux set-option -g status-right "#[fg=cyan]${st} #[fg=white]%H:%M" 2>/dev/null
}

notify() {
    if [ -n "$TMUX" ]; then
        tmux set-option -g status-right "#[fg=yellow]$1" 2>/dev/null
        (sleep 1.5 && update_tmux_status) &
    else
        echo "$1"
    fi
}

is_whitelisted() {
    local c=$(echo "$1" | sed -E 's/^(sudo|time|nice)\s+//')
    local base=$(echo "$c" | awk '{print $1}')
    [[ -f "$LEDGER_WHITELIST" ]] && grep -qx "$base" "$LEDGER_WHITELIST"
}

has_target() {
    local cmd="$1"
    
    echo "$cmd" | grep -qE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' && return 0
    echo "$cmd" | grep -qiE '\.(com|net|org|io|htb|thm|local|lab|corp|box)([^a-zA-Z]|$)' && return 0
    # Check against /etc/hosts entries
    if [[ -n "$LEDGER_HOSTS" ]]; then
        echo "$cmd" | grep -qE "($LEDGER_HOSTS)" && return 0
    fi
    return 1
}

capture() {
    [ -z "$TMUX" ] && return
    local raw=$(tmux capture-pane -pS -100)
    echo "$raw" > /tmp/ldr_$$.tmp
    echo "$1" > /tmp/ldr_cmd_$$.tmp
    
    $LEDGER_PYTHON -c "
from pathlib import Path
import sys,re,yaml
sys.path.insert(0,'$LEDGER_DIR')
from daemon import StackManager

cfg=yaml.safe_load(open('$LEDGER_DIR/config.yaml'))
prompt=cfg.get('shell',{}).get('prompt_symbol','❯')
raw=open('/tmp/ldr_$$.tmp').read()
cmd=open('/tmp/ldr_cmd_$$.tmp').read().strip()
lines=raw.split('\n')

# find command line
idx=-1
for i in range(len(lines)-1,-1,-1):
    if cmd in lines[i] and prompt in lines[i]:
        idx=i
        break
if idx==-1: sys.exit(0)

# find marker
end=len(lines)
for i in range(idx+1,len(lines)):
    if 'LEDGER_END' in lines[i]:
        end=i
        break

# extract output (skip noise)
out=[]
for i in range(idx+1,end):
    l=lines[i]
    if l.strip().startswith(prompt) or 'LEDGER_END' in l: continue
    if re.match(r'^\[.*\]\s+\d+',l): continue  # job control
    out.append(l)

output='\n'.join(out)
# clean ansi
output=re.sub(r'\x1B[@-Z\[-_]|\[[0-?]*[ -/]*[@-~]','',output)
output=re.sub(r' {4,}','  ',output).strip()

if output:
    s=StackManager(Path('$LEDGER_STACK'))
    if s.push(cmd,output):
        Path('/tmp/ldr_send').touch()
" 2>/dev/null
    
    rm -f /tmp/ldr_$$.tmp /tmp/ldr_cmd_$$.tmp
    [[ -f /tmp/ldr_send ]] && { rm /tmp/ldr_send; start_countdown; }
    update_tmux_status
}

preexec() { [[ $LEDGER_ENABLED -eq 1 ]] && LEDGER_LAST="$1"; }


precmd() {
    if [[ $LEDGER_ENABLED -eq 1 ]] && [[ -n "$LEDGER_LAST" ]]; then
        (is_whitelisted "$LEDGER_LAST" || has_target "$LEDGER_LAST") && {
            capture "$LEDGER_LAST"
            echo "$LEDGER_MARKER"
        }
        
    fi
    unset LEDGER_LAST_CMD
}

# commands
ltog() {
    if [[ $LEDGER_ENABLED -eq 1 ]]; then
        LEDGER_ENABLED=0
        echo "[*] ShadowLedger: OFF"
    else
        LEDGER_ENABLED=1
        echo "[*] ShadowLedger: ON (Ctrl+P: stack management)"
    fi
    update_tmux_status
}

lst() {
    echo "Ledger: $([[ $LEDGER_ENABLED -eq 1 ]] && echo '[ON]' || echo '[OFF]')"
    pgrep -f daemon.py >/dev/null && echo "Daemon: [ON]" || echo "Daemon: [OFF]"
    [[ -f /tmp/ledger_countdown.lock ]] && echo "Timer: [ACTIVE]"
    [[ -f "$LEDGER_STACK" ]] && $LEDGER_PYTHON -c "
import sys
sys.path.insert(0,'$LEDGER_DIR')
from daemon import StackManager
print(StackManager('$LEDGER_STACK').status())
" 2>/dev/null
}

_stack_widget() {
    zle push-input
    BUFFER="lstack"
    zle accept-line
}

lstack() {
    $LEDGER_PYTHON "$LEDGER_DIR/stack_tui.py" "$LEDGER_STACK"
    update_tmux_status
}

lclear() {
    touch /tmp/ldr_cancel
    $LEDGER_PYTHON -c "
import sys
sys.path.insert(0,'$LEDGER_DIR')
from daemon import StackManager
StackManager('$LEDGER_STACK').clear()
" 2>/dev/null
    update_tmux_status
}

lsend() {
    [[ ! -f "$LEDGER_STACK" ]] && echo "[!] Stack empty" && return
    local n=$($LEDGER_PYTHON -c "
import json
try: print(len(json.loads(open('$LEDGER_STACK').read()).get('commands',[])))
except: print(0)
" 2>/dev/null)
    [[ $n -eq 0 ]] && echo "[!] Stack empty" && return
    touch /tmp/ldr_cancel
    echo "[*] Sending $n commands to LLM..."
    touch /tmp/ldr_trigger
    update_tmux_status
}

start_countdown() {
    [[ -f /tmp/ledger_countdown.lock ]] && return
    ($LEDGER_PYTHON "$LEDGER_DIR/countdown.py" 15 &)
}

# keybinds
zle -N _stack_widget
bindkey '^P' _stack_widget

update_tmux_status