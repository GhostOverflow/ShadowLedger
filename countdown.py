#!/usr/bin/python3
import time
import sys
import subprocess
from pathlib import Path

LOCK = Path("/tmp/ledger_countdown.lock")
PAUSE = Path("/tmp/ledger_countdown_pause")
CANCEL = Path("/tmp/ldr_cancel")
TRIGGER = Path("/tmp/ldr_trigger")


def set_tmux(msg):
    try:
        subprocess.run(["tmux", "set-option", "-g", "status-right", msg],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass


def main():
    if len(sys.argv) < 2 or LOCK.exists():
        sys.exit(0)

    try:
        LOCK.touch()
        secs = int(sys.argv[1])

        for t in range(secs, 0, -1):
            if CANCEL.exists():
                CANCEL.unlink()
                set_tmux("#[fg=cyan][ON] #[fg=white]%H:%M")
                sys.exit(0)

            while PAUSE.exists():
                time.sleep(0.5)
                if CANCEL.exists():
                    CANCEL.unlink()
                    PAUSE.unlink(missing_ok=True)
                    set_tmux("#[fg=cyan][ON] #[fg=white]%H:%M")
                    sys.exit(0)

            set_tmux(
                f"#[fg=yellow][!] Auto-send in {t}s (Ctrl+P)#[fg=white] %H:%M")
            time.sleep(1)

        # done - trigger send
        TRIGGER.touch()
        set_tmux("#[fg=cyan][ON] #[fg=white]%H:%M")

    finally:
        LOCK.unlink(missing_ok=True)
        PAUSE.unlink(missing_ok=True)
        CANCEL.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
