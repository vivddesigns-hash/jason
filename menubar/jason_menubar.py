#!/usr/bin/env python3
"""Jason menu-bar controller.

A Jason icon in the macOS menu bar with Open / Start / Stop / Restart and a live
running/stopped status. Controls the local Jason launchd service
(com.floatai.jason). Stop is a real kill switch: it boots the job out AND
disables it, so it stays stopped (no KeepAlive respawn, no login restart) until
you press Start.
"""

import os
import subprocess

import rumps

HOME = os.path.expanduser("~")
PLIST = f"{HOME}/Library/LaunchAgents/com.floatai.jason.plist"
LABEL = "com.floatai.jason"
URL = "http://localhost:8787"
ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jason-menubar.png")
DOMAIN = f"gui/{os.getuid()}"
TARGET = f"{DOMAIN}/{LABEL}"
SYNC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sync.sh"))


def _lc(*args):
    subprocess.run(["launchctl", *args], capture_output=True, text=True)


def _sync(direction):
    """Best-effort brain/chat sync with the cloud (pull on start, push on stop)."""
    try:
        subprocess.run(["bash", SYNC, direction], capture_output=True, timeout=90)
    except Exception:
        pass


def _running() -> bool:
    try:
        out = subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if line.endswith(LABEL):
                pid = line.split("\t")[0].strip()
                return pid.isdigit() and pid != "0"
    except Exception:
        pass
    return False


def _start():
    _lc("enable", TARGET)          # undo any prior disable
    _lc("bootstrap", DOMAIN, PLIST)  # load + RunAtLoad starts it


def _stop():
    _lc("bootout", TARGET)         # stop + unload now
    _lc("disable", TARGET)         # stay stopped (no login restart)


def _notify(msg: str):
    try:
        rumps.notification("Jason", "", msg)
    except Exception:
        pass


class JasonApp(rumps.App):
    def __init__(self):
        super().__init__("Jason",
                         icon=ICON if os.path.exists(ICON) else None,
                         template=False, quit_button=None)
        self.status_item = rumps.MenuItem("Checking…")
        self.menu = [
            self.status_item,
            None,
            rumps.MenuItem("Open Jason", callback=self.open_app),
            rumps.MenuItem("Start", callback=self.start),
            rumps.MenuItem("Stop", callback=self.stop),
            rumps.MenuItem("Restart", callback=self.restart),
            None,
            rumps.MenuItem("Quit controller", callback=lambda _: rumps.quit_application()),
        ]
        self.refresh(None)
        rumps.Timer(self.refresh, 5).start()

    def refresh(self, _):
        up = _running()
        self.status_item.title = "● Jason is running" if up else "○ Jason is stopped"
        self.menu["Start"].set_callback(None if up else self.start)
        self.menu["Stop"].set_callback(self.stop if up else None)

    def open_app(self, _):
        if not _running():
            _sync("pull")
            _start()
        subprocess.run(["open", URL])  # default browser

    def start(self, _):
        _sync("pull")   # bring the cloud's latest brain/chats down first
        _start()
        _notify("Starting Jason (synced with cloud)…")
        self.refresh(None)

    def stop(self, _):
        _stop()
        _sync("push")   # send this session's brain/chats up to the cloud
        _notify("Jason stopped (synced to cloud).")
        self.refresh(None)

    def restart(self, _):
        _stop()
        _start()
        _notify("Jason restarted.")
        self.refresh(None)


if __name__ == "__main__":
    JasonApp().run()
