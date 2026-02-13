#!/usr/bin/python3
import curses
import json
import sys
from pathlib import Path

PAUSE = Path("/tmp/ledger_countdown_pause")
CANCEL = Path("/tmp/ledger_countdown_cancel")


class StackTUI:
    def __init__(self, stack_file):
        self.file = Path(stack_file)
        self.current = 0
        self.mode = 'normal'
        self.paused = False

        if Path("/tmp/ledger_countdown.lock").exists():
            PAUSE.touch()
            self.paused = True

        self.load()

    def load(self):
        try:
            d = json.loads(self.file.read_text()) if self.file.exists() else {}
            self.cmds = d.get('commands', [])
            self.tokens = d.get('total_tokens', 0)
        except:
            self.cmds, self.tokens = [], 0

    def save(self):
        self.file.write_text(json.dumps(
            {'commands': self.cmds, 'total_tokens': self.tokens}, indent=2))

    def delete(self):
        if self.cmds:
            rm = self.cmds.pop(self.current)
            self.tokens -= rm['tokens']
            if self.current >= len(self.cmds) and self.current > 0:
                self.current -= 1
            self.save()

    def move_up(self):
        if self.current > 0:
            self.cmds[self.current], self.cmds[self.current -
                                               1] = self.cmds[self.current-1], self.cmds[self.current]
            self.current -= 1
            self.save()

    def move_down(self):
        if self.current < len(self.cmds)-1:
            self.cmds[self.current], self.cmds[self.current +
                                               1] = self.cmds[self.current+1], self.cmds[self.current]
            self.current += 1
            self.save()

    def clear_all(self):
        self.cmds, self.tokens, self.current = [], 0, 0
        self.save()

    def send(self):
        Path('/tmp/ldr_trigger').touch()
        return True

    def cleanup(self):
        if self.paused:
            PAUSE.unlink(missing_ok=True)

    def draw(self, scr):
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)

        while True:
            scr.clear()
            h, w = scr.getmaxyx()

            # header
            title = "ShadowLedger Stack"
            if self.paused:
                title += " (timer paused)"
            scr.addstr(0, (w-len(title))//2, title,
                       curses.color_pair(2) | curses.A_BOLD)

            # stats
            stats = f"Commands: {len(self.cmds)} | Tokens: {self.tokens}"
            scr.addstr(1, (w-len(stats))//2, stats)
            scr.addstr(2, 0, "─"*w)

            # list
            start = max(0, self.current-(h-10))
            end = min(len(self.cmds), start+(h-10))

            if not self.cmds:
                msg = "Stack empty (q to exit)"
                scr.addstr(h//2, (w-len(msg))//2, msg, curses.color_pair(3))
            else:
                for i in range(start, end):
                    y = 3+(i-start)
                    c = self.cmds[i]
                    txt = c['command'][:w-20]
                    tok = c['tokens']
                    line = f"[{i+1:2d}] {txt}"

                    if i == self.current:
                        scr.addstr(y, 0, "→", curses.color_pair(1)
                                   | curses.A_BOLD)
                        scr.addstr(
                            y, 2, line[:w-10], curses.color_pair(1) | curses.A_BOLD)
                        scr.addstr(y, w-8, f"{tok}t", curses.color_pair(1))
                    else:
                        scr.addstr(y, 2, line[:w-10])
                        scr.addstr(y, w-8, f"{tok}t", curses.COLOR_CYAN)

            # footer
            fy = h-5
            scr.addstr(fy, 0, "─"*w)

            if self.mode == 'confirm_clear':
                scr.addstr(fy+1, 2, "Clear ALL? (y/n)",
                           curses.color_pair(4) | curses.A_BOLD)
            elif self.mode == 'confirm_send':
                scr.addstr(
                    fy+1, 2, f"Send {len(self.cmds)} commands? (y/n)", curses.color_pair(3) | curses.A_BOLD)
            else:
                help = "j/k:nav | Shift+J/K:move | d:del | s:send | c:clear | q:quit"
                scr.addstr(fy+1, 2, help[:w-4], curses.color_pair(3))

            scr.refresh()

            try:
                key = scr.getch()
            except KeyboardInterrupt:
                break

            # handlers
            if self.mode == 'confirm_clear':
                if key in [ord('y'), ord('Y')]:
                    self.clear_all()
                    CANCEL.touch()
                    self.mode = 'normal'
                elif key in [ord('n'), ord('N'), 27]:
                    self.mode = 'normal'
                continue

            elif self.mode == 'confirm_send':
                if key in [ord('y'), ord('Y')]:
                    if self.send():
                        CANCEL.touch()
                        return 'sent'
                elif key in [ord('n'), ord('N'), 27]:
                    self.mode = 'normal'
                continue

            # normal mode
            if key in [ord('q'), 27]:
                if self.paused:
                    CANCEL.touch()
                break
            elif key == ord('j') and self.cmds:
                self.current = min(len(self.cmds)-1, self.current+1)
            elif key == ord('k') and self.cmds:
                self.current = max(0, self.current-1)
            elif key == ord('J') and self.cmds:
                self.move_down()
            elif key == ord('K') and self.cmds:
                self.move_up()
            elif key == curses.KEY_DOWN and self.cmds:
                self.current = min(len(self.cmds)-1, self.current+1)
            elif key == curses.KEY_UP and self.cmds:
                self.current = max(0, self.current-1)
            elif key in [ord('d'), ord('x')] and self.cmds:
                self.delete()
            elif key == ord('c') and self.cmds:
                self.mode = 'confirm_clear'
            elif key == ord('s') and self.cmds:
                self.mode = 'confirm_send'

        return 'quit'


def main():
    if len(sys.argv) < 2:
        print("Usage: stack_tui.py <stack_file>")
        sys.exit(1)

    tui = StackTUI(sys.argv[1])

    try:
        result = curses.wrapper(tui.draw)
        tui.cleanup()
        if result == 'sent':
            print("[*] Stack sent to LLM")
        sys.exit(0)
    except Exception as e:
        tui.cleanup()
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
