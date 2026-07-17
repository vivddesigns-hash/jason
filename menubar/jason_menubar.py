#!/usr/bin/env python3
"""Jason menu-bar controller.

Puts a Jason icon in the macOS menu bar with Open / Start / Stop / Restart,
and a live running/stopped status. Start & Stop control the local Jason
launchd service (com.floatai.jason) — Stop is your instant kill switch.
"""

import os
import subprocess

import rumps

HOME = os.path.expanduser("~")
PLIST = f"{HOME}/Library/LaunchAgents/com.floatai.jason.plist"
LABEL = "com.floatai.jason"
URL = "http://localhost:8787"
ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jason-menubar.png")


def _running() -> bool:
    try:
        out = subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if LABEL in line:
                pid = line.split("\t")[0].strip()
                return pid.isdigit() and pid != "0"
    except Exception:
        pass
    return False


def _launchctl(*args):
    subprocess.run(["launchctl", *args], capture_output=True, text=True)


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
        self.status_item = rumps.MenuItem("Checking…")  # informational (no callback)
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
            _launchctl("load", PLIST)
        # Prefer opening inside Calm Desk (Dwight's workspace) over the browser.
        if os.path.exists("/Applications/Calm Desk.app"):
            subprocess.run(["open", "-a", "Calm Desk"])
        else:
            subprocess.run(["open", URL])

    def start(self, _):
        _launchctl("load", PLIST)
        _notify("Starting Jason…")
        self.refresh(None)

    def stop(self, _):
        _launchctl("unload", PLIST)
        _notify("Jason stopped.")
        self.refresh(None)

    def restart(self, _):
        _launchctl("unload", PLIST)
        _launchctl("load", PLIST)
        _notify("Jason restarted.")
        self.refresh(None)


if __name__ == "__main__":
    JasonApp().run()
