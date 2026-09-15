const { app, BrowserWindow, Menu, ipcMain, session } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { execFile } = require('child_process');

// Thin shell — no local backend. The agent, auth, and all data live entirely
// on the production server; this window just loads the same site a browser
// would. One login (email + password against jason.tryfloatai.com), one
// account, one dataset — nothing local to go stale, get lost, or diverge.
const APP_URL = process.env.JASON_URL || 'https://jason.tryfloatai.com';
const WS_URL = process.env.JASON_WS_URL || 'wss://jason.tryfloatai.com/ws/helper';

// JasonMax (FR-011): the ONLY piece of this app with real local-machine
// power — takes real computer-use commands (screenshot/click/type/key) from
// the paired cloud account and actually executes them on this Mac. Pairing
// is opt-in (via the jason://pair custom-protocol link, clicked from
// Settings inside the app itself) and reversible (regenerating the token
// server-side invalidates this device instantly).
//
// NOTE ON PACKAGING: action execution shells out to action_executor.py,
// reusing the exact pyautogui/Quartz mechanism already verified working in
// the FR-011 proof-of-concept, rather than a native Node input-simulation
// module. That's the right tradeoff to get a genuinely working end-to-end
// version fast, but it means this machine needs Python + pyautogui
// available — for distributing to real customers (not just this dev
// machine), that needs to become a bundled standalone executable (e.g. via
// PyInstaller) shipped inside the app, not a dependency on the user's own
// Python install. Flagged here so it isn't quietly forgotten.
const CONFIG_DIR = path.join(app.getPath('userData'), 'jasonmax');
const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');
const PYTHON_BIN = process.env.JASON_PYTHON_BIN
  || '/Users/dwightjones/Developer/myagent/.venv/bin/python3';
// Packaged builds pack main.js into app.asar (a virtual FS only Node/Electron
// understands) — a plain Python subprocess can't open a path inside it, so
// action_executor.py ships as an unpacked extraResource instead and must be
// looked up via process.resourcesPath when running from a real .app, not
// __dirname (which would resolve inside the asar and silently fail).
const ACTION_EXECUTOR = app.isPackaged
  ? path.join(process.resourcesPath, 'action_executor.py')
  : path.join(__dirname, 'action_executor.py');

let helperSocket = null;
let helperReconnectTimer = null;

function loadConfig() {
  try { return JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8')); } catch (_) { return {}; }
}
function saveConfig(cfg) {
  fs.mkdirSync(CONFIG_DIR, { recursive: true });
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(cfg));
}

function runAction(action, params) {
  return new Promise((resolve) => {
    const payload = JSON.stringify({ action, params, overlay_rect: controlOverlayRect });
    // maxBuffer stays small on purpose — screenshots go through a temp file
    // (image_path), not raw stdout, precisely because that path already
    // blew past Node's default 1MB buffer on the first real screenshot.
    execFile(PYTHON_BIN, [ACTION_EXECUTOR, payload], { timeout: 20000, maxBuffer: 1024 * 1024 }, (err, stdout) => {
      if (err) { resolve({ error: String(err) }); return; }
      let result;
      try { result = JSON.parse(stdout); }
      catch (e) { resolve({ error: `bad executor output: ${stdout}` }); return; }

      if (result.image_path) {
        try {
          const data = fs.readFileSync(result.image_path);
          resolve({ image_b64: data.toString('base64') });
        } catch (e) {
          resolve({ error: `couldn't read screenshot file: ${e}` });
        } finally {
          fs.unlink(result.image_path, () => {});  // best-effort cleanup
        }
        return;
      }
      resolve(result);
    });
  });
}

// Direct file operations (list/read/rename/move) — the fast path for simple
// file tasks. Handled entirely in Node via fs, never shelling out to
// action_executor.py's screenshot/pyautogui machinery at all, which is the
// whole reason this is fast where Computer Use is slow.
const FILE_OP_ACTIONS = new Set(['list_dir', 'read_file', 'rename_file', 'move_file', 'create_folder', 'write_file', 'get_file_info']);

// Same "fast, no vision model, one round trip" category as the file ops
// above — a plain AppleScript query, not a Python/Quartz computer-use task.
const CHROME_ACTIONS = new Set(['list_chrome_tabs', 'read_active_tab', 'click_in_active_tab', 'type_in_active_tab']);

// Generic Accessibility (System Events) actions — any app, not just Chrome.
const SCREEN_ACTIONS = new Set(['read_frontmost_window', 'click_ui_element', 'type_into_ui_element']);

// Cap matches read_file's own 500KB cap (mac_files.py) — kept in sync so a
// file Jason writes is never bigger than one it could turn around and read
// back in the same fast path.
const WRITE_FILE_MAX_BYTES = 500000;

// Allowed roots default to the whole home folder — same precedent already
// used for JASON_EXTRA_DIRS on a local admin install (see agent/core.py) —
// just enforced per-operation here (real-path resolved, so a symlink or `..`
// can't escape it) rather than granted for a whole session. No config UI for
// this yet; revisit if this ever needs to be narrower or user-configurable.
//
// Plus any external drive currently mounted under /Volumes (added
// 2026-09-05, Dwight's request — Jason needs to read Logic sessions/bounces
// living on whatever drive is plugged in, not just ones named in advance).
// One important exclusion: macOS mounts the boot volume itself under
// /Volumes too (e.g. "Macintosh HD" as a symlink to "/") — including that
// would make every path on the whole machine pass the allow-list check, so
// any entry that resolves to the filesystem root is skipped, not granted.
function allowedFileRoots() {
  const roots = [fs.realpathSync(os.homedir())];
  let entries = [];
  try {
    entries = fs.readdirSync('/Volumes');
  } catch (_) {
    entries = [];
  }
  for (const entry of entries) {
    try {
      const real = fs.realpathSync(path.join('/Volumes', entry));
      if (real !== '/' && real !== path.sep) {
        roots.push(real);
      }
    } catch (_) {
      // Unmounted/inaccessible between the readdir and the realpath — skip.
    }
  }
  return roots;
}

// Resolves a path and confirms it's really inside one of the allowed roots.
// realpathSync follows symlinks — needed so a symlink pointing outside the
// allowed roots can't be used to escape them. Falls back to the plain
// resolved path if the target doesn't exist yet (e.g. a move destination
// that doesn't exist until the move actually happens) — path.resolve() has
// already normalized any `..` segments in that case.
//
// A leading `~` is expanded to the home folder first — path.resolve() (unlike
// a real shell) treats `~` as a literal folder name, not home. Without this,
// "~/Documents/X" resolves to something like <cwd>/~/Documents/X, which is
// outside every allowed root, and gets refused with the exact same message
// as a genuinely disallowed path — indistinguishable from a real permissions
// problem even though it's just an unexpanded path (confirmed in real
// testing 2026-07-25: a model-supplied "~/Documents/..." path was refused
// this way and read as "Documents isn't accessible" when it actually was).
function expandHome(rawPath) {
  if (rawPath === '~') return os.homedir();
  if (rawPath.startsWith('~/') || rawPath.startsWith('~\\')) {
    return path.join(os.homedir(), rawPath.slice(2));
  }
  return rawPath;
}

function resolveWithinAllowedRoots(rawPath) {
  const resolved = path.resolve(expandHome(rawPath));
  let real;
  try { real = fs.realpathSync(resolved); } catch (_) { real = resolved; }
  const roots = allowedFileRoots();
  const ok = roots.some((root) => real === root || real.startsWith(root + path.sep));
  if (!ok) {
    return { error: `Refused: "${rawPath}" is outside the folders this Mac has granted Jason access to.` };
  }
  return { realPath: real };
}

async function runFileOp(action, params) {
  try {
    if (action === 'list_dir') {
      const target = params.path || os.homedir();
      const check = resolveWithinAllowedRoots(target);
      if (check.error) return { error: check.error };
      const entries = fs.readdirSync(check.realPath, { withFileTypes: true });
      return { entries: entries.map((d) => ({ name: d.name, is_dir: d.isDirectory() })) };
    }
    if (action === 'read_file') {
      const check = resolveWithinAllowedRoots(params.path || '');
      if (check.error) return { error: check.error };
      const stat = fs.statSync(check.realPath);
      if (stat.isDirectory()) return { error: `"${params.path}" is a folder, not a file.` };
      if (stat.size > 500000) {
        return { error: `File is too large to read directly (${stat.size} bytes, over the 500KB limit for this tool).` };
      }
      const buf = fs.readFileSync(check.realPath);
      // A null byte anywhere in the first chunk is a reliable enough binary
      // signal for this purpose — refuse rather than return garbage.
      if (buf.subarray(0, 8000).includes(0)) {
        return { error: `"${params.path}" looks like a binary file — this tool only reads plain text.` };
      }
      return { content: buf.toString('utf8') };
    }
    if (action === 'rename_file') {
      const check = resolveWithinAllowedRoots(params.path || '');
      if (check.error) return { error: check.error };
      const newName = String(params.new_name || '').trim();
      if (!newName || newName.includes('/') || newName.includes('\\')) {
        return { error: 'new_name must be a plain filename, not a path.' };
      }
      const dest = path.join(path.dirname(check.realPath), newName);
      if (fs.existsSync(dest)) return { error: `"${newName}" already exists there — refusing to overwrite.` };
      fs.renameSync(check.realPath, dest);
      return { message: `Renamed to "${newName}".` };
    }
    if (action === 'move_file') {
      const srcCheck = resolveWithinAllowedRoots(params.path || '');
      if (srcCheck.error) return { error: srcCheck.error };
      const destDirCheck = resolveWithinAllowedRoots(params.destination_dir || '');
      if (destDirCheck.error) return { error: destDirCheck.error };
      if (!fs.statSync(destDirCheck.realPath).isDirectory()) {
        return { error: `"${params.destination_dir}" is not a folder.` };
      }
      const finalName = params.new_name ? String(params.new_name).trim() : path.basename(srcCheck.realPath);
      if (finalName.includes('/') || finalName.includes('\\')) {
        return { error: 'new_name must be a plain filename, not a path.' };
      }
      const dest = path.join(destDirCheck.realPath, finalName);
      if (fs.existsSync(dest)) return { error: `"${finalName}" already exists at the destination — refusing to overwrite.` };
      // rename() across same-volume dirs is a real move; cross-volume would
      // throw EXDEV and need a copy+delete fallback — out of scope for v1.
      fs.renameSync(srcCheck.realPath, dest);
      return { message: `Moved to "${dest}".` };
    }
    if (action === 'create_folder') {
      const check = resolveWithinAllowedRoots(params.path || '');
      if (check.error) return { error: check.error };
      if (fs.existsSync(check.realPath)) {
        return { error: `"${params.path}" already exists there — refusing to overwrite.` };
      }
      fs.mkdirSync(check.realPath, { recursive: true });
      return { message: `Created folder "${params.path}".` };
    }
    if (action === 'write_file') {
      const check = resolveWithinAllowedRoots(params.path || '');
      if (check.error) return { error: check.error };
      if (fs.existsSync(check.realPath)) {
        return { error: `"${params.path}" already exists there — refusing to overwrite. Use a different name, or move/rename the existing file first.` };
      }
      const content = params.content || '';
      const byteLength = Buffer.byteLength(content, 'utf8');
      if (byteLength > WRITE_FILE_MAX_BYTES) {
        return { error: `Content is too large to write directly (${byteLength} bytes, over the ${WRITE_FILE_MAX_BYTES}-byte limit for this tool).` };
      }
      // Same allowed-roots check already covers the parent dir (it's a
      // prefix of the target path), so creating any missing intermediate
      // folders here can't escape the sandbox it already passed.
      fs.mkdirSync(path.dirname(check.realPath), { recursive: true });
      fs.writeFileSync(check.realPath, content, 'utf8');
      return { message: `Wrote "${params.path}" (${byteLength} bytes).` };
    }
    if (action === 'get_file_info') {
      const check = resolveWithinAllowedRoots(params.path || '');
      if (check.error) return { error: check.error };
      const stat = fs.statSync(check.realPath);
      const isDir = stat.isDirectory();
      // birthtime = real creation date, survives renames/moves (unlike
      // mtime, which bumps on any content or directory-entry change) — this
      // is what the naming-convention rename work actually needs, proven
      // against files already correctly renamed by the watcher (Sep 2026:
      // matched exactly, verified before this tool existed).
      return {
        is_dir: isDir,
        created_date: stat.birthtime.toISOString().slice(0, 10),
        created_at: stat.birthtime.toISOString(),
        modified_date: stat.mtime.toISOString().slice(0, 10),
        modified_at: stat.mtime.toISOString(),
        // A directory's own stat.size is its inode/metadata size, not its
        // contents' total size — misleading if returned as-is, so omitted
        // rather than returning a small, wrong-looking number for folders.
        size_bytes: isDir ? null : stat.size,
      };
    }
    return { error: `unhandled file action: ${action}` };
  } catch (exc) {
    return { error: String((exc && exc.message) || exc) };
  }
}

// Chrome tab rescue-and-organize workflow, Stage 1 (capture). Returns every
// open tab's title + URL, grouped by window, from the user's REAL
// daily-driver Chrome — deliberately separate from Calm Desk's dedicated
// agent-browser Chrome (a different, isolated instance entirely; this reads
// the one the user actually lives in). No trimming/redaction here — full
// URLs are returned as-is, including anything sensitive a query string
// happens to carry (OAuth tokens, session codes, etc.); that's a deliberate
// choice, not an oversight — the user needs to see exactly what a tab was
// before deciding keep/discard, and nothing here gets stored permanently.
// Redaction is Stage 3's job (Calm Desk, at the point something is actually
// saved as a kept object), not this capture step's.
async function chromeIsRunning() {
  return new Promise((resolve) => {
    execFile('/usr/bin/pgrep', ['-x', 'Google Chrome'], (err) => resolve(!err));
  });
}

// Real, confirmed-live bug (2026-08-20): Calm Desk's own agent_browser tool
// launches its OWN Chrome process — same executable, separate
// --user-data-dir, so it's a totally isolated automation profile — but
// `tell application "Google Chrome"` addresses BOTH by the same bundle
// identity, and which process actually receives the Apple Event is decided
// by macOS, not by anything in this script. When agent_browser's instance
// wins that routing, every read_active_tab/click/type call silently landed
// on ITS blank about:blank tab instead of the user's real browsing session
// — no error, just wrong (empty) data, which is far worse than a clear
// failure. Checked before every Chrome-JS call so this fails loudly with an
// actionable message instead of quietly reading nothing.
async function agentBrowserChromeRunning() {
  return new Promise((resolve) => {
    execFile('/usr/bin/pgrep', ['-f', 'Calm Desk/agent-browser-profile'], (err) => resolve(!err));
  });
}

async function runChromeTabs() {
  // Checked via pgrep first, not System Events — `tell application "Google
  // Chrome"` auto-launches the app if it isn't already running, which would
  // be a real, surprising side effect for what's supposed to be a passive
  // read. pgrep also avoids needing a second, separate Automation permission
  // grant (System Events) beyond the one Chrome itself will prompt for.
  const running = await chromeIsRunning();
  if (!running) {
    return { windows: [], not_running: true };
  }
  // tab/linefeed are computed OUTSIDE the tell block and passed in as plain
  // variables — Chrome's own AppleScript dictionary defines a "tab" object
  // class (a browser tab), which shadows AppleScript's built-in `tab`
  // character constant inside `tell application "Google Chrome"`, silently
  // resolving to Chrome's own ambiguous term instead and stringifying as the
  // literal text "tab" rather than an actual tab character. Confirmed via
  // real output: `1tabEmail addressestabhttps://...` instead of real tabs.
  const script = `
set tabChar to ASCII character 9
set nlChar to ASCII character 10
tell application "Google Chrome"
  set output to ""
  repeat with w from 1 to count of windows
    set win to window w
    repeat with t in tabs of win
      set output to output & w & tabChar & (title of t) & tabChar & (URL of t) & nlChar
    end repeat
  end repeat
  return output
end tell`;
  return new Promise((resolve) => {
    execFile('/usr/bin/osascript', ['-e', script], { maxBuffer: 1024 * 1024 * 20 }, (err, stdout, stderr) => {
      if (err) {
        resolve({ error: `Couldn't read Chrome tabs: ${String((stderr || err.message || err)).trim()}` });
        return;
      }
      const byWindow = new Map();
      for (const line of stdout.split('\n')) {
        if (!line.trim()) continue;
        // URL is always the last field (URLs can't contain literal tabs/
        // newlines — they'd be percent-encoded); title is everything
        // between the window index and the URL, rejoined in case a title
        // itself happens to contain a literal tab character.
        const parts = line.split('\t');
        if (parts.length < 3) continue;
        const windowIndex = Number(parts[0]);
        const url = parts[parts.length - 1];
        const title = parts.slice(1, -1).join('\t');
        if (!byWindow.has(windowIndex)) byWindow.set(windowIndex, []);
        byWindow.get(windowIndex).push({ title, url });
      }
      const windows = [...byWindow.keys()].sort((a, b) => a - b)
        .map((idx) => ({ window: idx, tabs: byWindow.get(idx) }));
      resolve({ windows });
    });
  });
}

// Chrome active-tab content + action, via `execute javascript` — same
// mechanism as list_chrome_tabs (AppleScript, no vision), but reads full
// rendered page text and can click/type in the REAL active tab, not just
// enumerate titles. This is the fast "read what I'm looking at" path for
// whichever tab actually has focus, distinct from list_chrome_tabs (every
// tab, title/URL only). innerText is capped — a long page shouldn't blow
// past what's actually useful to read in one go.
const CHROME_TEXT_MAX_CHARS = 8000;

function escapeForAppleScriptJs(js) {
  // The JS string is itself embedded inside an AppleScript string literal —
  // both layers of quoting need escaping, or a selector/text containing a
  // quote silently breaks the whole script instead of erroring clearly.
  return js.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

// Shared message for the "landed on the wrong Chrome instance" case — same
// wording whether it's read or write, so the model gets one consistent,
// actionable signal instead of interpreting empty/blank content as a real
// answer about the user's screen.
const WRONG_CHROME_INSTANCE_ERROR =
  "This reached Calm Desk's own isolated automation Chrome instead of the " +
  "user's real browser (a known macOS Apple-Events routing ambiguity when " +
  "both share the Google Chrome app identity) — not the user's actual " +
  'screen. Tell them to close any idle Calm Desk browser windows/agent ' +
  'tasks and try again, don\'t report this blank result as real content.';

async function runChromeExecuteJs(js) {
  const running = await chromeIsRunning();
  if (!running) return { error: 'not_running' };
  const agentBrowserUp = await agentBrowserChromeRunning();
  const script = `tell application "Google Chrome"
  if (count of windows) = 0 then return "__NO_WINDOW__"
  set tabUrl to URL of active tab of front window
  if tabUrl is "about:blank" then return "__BLANK_WINDOW__"
  return execute front window's active tab javascript "${escapeForAppleScriptJs(js)}"
end tell`;
  return new Promise((resolve) => {
    execFile('/usr/bin/osascript', ['-e', script], { maxBuffer: 1024 * 1024 * 10 }, (err, stdout, stderr) => {
      if (err) { resolve({ error: String((stderr || err.message || err)).trim() }); return; }
      const out = stdout.replace(/\n$/, '');
      if (out === '__NO_WINDOW__') { resolve({ error: 'no Chrome window open' }); return; }
      if (out === '__BLANK_WINDOW__') {
        resolve({ error: agentBrowserUp ? WRONG_CHROME_INSTANCE_ERROR : 'The active Chrome tab is blank (about:blank) — nothing to read/act on.' });
        return;
      }
      resolve({ result: out });
    });
  });
}

async function runChromeReadActiveTab() {
  const running = await chromeIsRunning();
  if (!running) return { not_running: true };
  const agentBrowserUp = await agentBrowserChromeRunning();
  const script = `tell application "Google Chrome"
  if (count of windows) = 0 then return "__NO_WINDOW__"
  set tabTitle to title of active tab of front window
  set tabUrl to URL of active tab of front window
  if tabUrl is "about:blank" then return "__BLANK_WINDOW__"
  set tabText to execute front window's active tab javascript "document.body.innerText.slice(0, ${CHROME_TEXT_MAX_CHARS})"
  return tabTitle & "\\n" & tabUrl & "\\n" & tabText
end tell`;
  return new Promise((resolve) => {
    execFile('/usr/bin/osascript', ['-e', script], { maxBuffer: 1024 * 1024 * 10 }, (err, stdout, stderr) => {
      if (err) { resolve({ error: String((stderr || err.message || err)).trim() }); return; }
      if (stdout.trim() === '__NO_WINDOW__') { resolve({ error: 'no Chrome window open' }); return; }
      if (stdout.trim() === '__BLANK_WINDOW__') {
        resolve({ error: agentBrowserUp ? WRONG_CHROME_INSTANCE_ERROR : 'The active Chrome tab is blank (about:blank) — nothing to read.' });
        return;
      }
      const nl = stdout.indexOf('\n');
      const nl2 = stdout.indexOf('\n', nl + 1);
      resolve({
        title: stdout.slice(0, nl),
        url: stdout.slice(nl + 1, nl2),
        text: stdout.slice(nl2 + 1).replace(/\n$/, ''),
      });
    });
  });
}

async function runChromeAction(action, params) {
  try {
    if (action === 'list_chrome_tabs') {
      return await runChromeTabs();
    }
    if (action === 'read_active_tab') {
      return await runChromeReadActiveTab();
    }
    if (action === 'click_in_active_tab') {
      // querySelector + .click() — returns whether an element was actually
      // found, so a bad selector reports clearly instead of silently doing
      // nothing (indistinguishable from "clicked but nothing happened").
      const sel = escapeForAppleScriptJs(params.selector || '');
      const r = await runChromeExecuteJs(
        `(function(){var e=document.querySelector("${sel}");if(!e)return "not_found";e.click();return "clicked";})()`
      );
      return r.error ? r : { result: r.result };
    }
    if (action === 'type_in_active_tab') {
      const sel = escapeForAppleScriptJs(params.selector || '');
      const val = escapeForAppleScriptJs((params.text || '').replace(/"/g, '\\"'));
      const r = await runChromeExecuteJs(
        `(function(){var e=document.querySelector("${sel}");if(!e)return "not_found";` +
        `e.focus();e.value="${val}";e.dispatchEvent(new Event('input',{bubbles:true}));` +
        `e.dispatchEvent(new Event('change',{bubbles:true}));return "typed";})()`
      );
      return r.error ? r : { result: r.result };
    }
    return { error: `unhandled chrome action: ${action}` };
  } catch (exc) {
    return { error: String((exc && exc.message) || exc) };
  }
}

// Generic "read/act on whatever's on screen" — macOS Accessibility API via
// System Events, NOT vision. Works on any app (not just Chrome): reads the
// frontmost window's UI element tree (buttons, fields, static text) as
// structured data, and can click/type directly into a named element. This
// is the general fallback-before-the-fallback that FR-011 always meant to
// build alongside Computer Use ("browser/CDP first, Computer Use only when
// nothing else works") — Computer Use should now be the LAST resort, not
// the only option, for anything with a normal accessibility tree.
const SCREEN_ELEMENTS_MAX = 200;
const SCREEN_TEXT_MAX_CHARS = 200;

const READ_FRONTMOST_SCRIPT = `
on getElementInfo(el)
    set clsStr to ""
    set nameStr to ""
    set valStr to ""
    try
        set clsStr to (class of el) as string
    end try
    try
        set nameStr to (name of el) as string
    end try
    try
        set valStr to (value of el) as string
    end try
    if nameStr is "missing value" then set nameStr to ""
    if valStr is "missing value" then set valStr to ""
    return clsStr & "\\t" & nameStr & "\\t" & valStr
end getElementInfo

tell application "System Events"
    set frontProc to first application process whose frontmost is true
    set appName to name of frontProc
    set winName to "none"
    set allEls to {}
    tell frontProc
        try
            set winName to name of front window
        end try
        try
            set allEls to entire contents of front window
        end try
    end tell
end tell

set outList to {}
set n to 0
repeat with el in allEls
    if n > ${SCREEN_ELEMENTS_MAX} then exit repeat
    set n to n + 1
    set end of outList to my getElementInfo(el)
end repeat
set AppleScript's text item delimiters to linefeed
set outStr to outList as string
set AppleScript's text item delimiters to ""
return appName & "\\n" & winName & "\\n" & outStr
`;

async function runReadFrontmostWindow() {
  return new Promise((resolve) => {
    execFile('/usr/bin/osascript', ['-e', READ_FRONTMOST_SCRIPT], { maxBuffer: 1024 * 1024 * 10 }, (err, stdout, stderr) => {
      if (err) { resolve({ error: String((stderr || err.message || err)).trim() }); return; }
      const lines = stdout.replace(/\n$/, '').split('\n');
      const appName = lines[0];
      const winName = lines[1];
      const elements = lines.slice(2).filter(Boolean).map((l) => {
        const [cls, name, value] = l.split('\t');
        return {
          class: cls,
          name: name ? name.slice(0, SCREEN_TEXT_MAX_CHARS) : undefined,
          value: value ? value.slice(0, SCREEN_TEXT_MAX_CHARS) : undefined,
        };
        // Structural containers (groups, scroll areas) with neither a name
        // nor a value carry no useful information — filtered out below,
        // here in JS where checking "either field present" is trivial,
        // rather than in AppleScript string-matching (got this wrong once
        // already: matching only on trailing tab silently dropped every
        // element that had a name but an empty value — most buttons).
      }).filter((el) => el.name || el.value);
      resolve({ app: appName, window: winName, elements });
    });
  });
}

function escapeForAppleScriptStr(s) {
  return String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

async function runUiAction(action, params) {
  const targetName = escapeForAppleScriptStr(params.name || '');
  const findAndAct = (actionScript) => `
tell application "System Events"
    set frontProc to first application process whose frontmost is true
    set allEls to {}
    tell frontProc
        try
            set allEls to entire contents of front window
        end try
    end tell
    set target to missing value
    repeat with el in allEls
        try
            if (name of el as string) is "${targetName}" then
                set target to el
                exit repeat
            end if
        end try
    end repeat
    if target is missing value then return "not_found"
    ${actionScript}
    return "ok"
end tell`;

  let script;
  if (action === 'click_ui_element') {
    script = findAndAct('click target');
  } else if (action === 'type_into_ui_element') {
    const text = escapeForAppleScriptStr(params.text || '');
    script = findAndAct(`
    try
        set focused of target to true
    end try
    try
        set value of target to "${text}"
    on error
        keystroke "${text}"
    end try`);
  } else {
    return { error: `unhandled screen action: ${action}` };
  }

  return new Promise((resolve) => {
    execFile('/usr/bin/osascript', ['-e', script], { maxBuffer: 1024 * 1024 }, (err, stdout, stderr) => {
      if (err) { resolve({ error: String((stderr || err.message || err)).trim() }); return; }
      const result = stdout.trim();
      if (result === 'not_found') { resolve({ error: `no element named "${params.name}" found in the frontmost window` }); return; }
      resolve({ result });
    });
  });
}

async function runScreenAction(action, params) {
  try {
    if (action === 'read_frontmost_window') return await runReadFrontmostWindow();
    if (action === 'click_ui_element' || action === 'type_into_ui_element') return await runUiAction(action, params);
    return { error: `unhandled screen action: ${action}` };
  } catch (exc) {
    return { error: String((exc && exc.message) || exc) };
  }
}

function connectHelper() {
  const { token } = loadConfig();
  if (!token) return;  // not paired yet — nothing to connect

  clearTimeout(helperReconnectTimer);
  try { helperSocket && helperSocket.close(); } catch (_) {}

  const ws = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`);
  helperSocket = ws;

  ws.addEventListener('message', async (event) => {
    let msg;
    try { msg = JSON.parse(event.data); } catch (_) { return; }
    // Two message shapes on this socket: a real action request (has
    // request_id, needs a result sent back), or a bare event notification
    // (task_start/task_end) driving the on-screen control indicator — no
    // response expected for the latter.
    if (msg.event === 'task_start') { showControlOverlay(); return; }
    if (msg.event === 'task_end') { hideControlOverlay(); return; }
    if (!msg.request_id) return;
    const result = FILE_OP_ACTIONS.has(msg.action) ? await runFileOp(msg.action, msg.params || {})
      : CHROME_ACTIONS.has(msg.action) ? await runChromeAction(msg.action, msg.params || {})
      : SCREEN_ACTIONS.has(msg.action) ? await runScreenAction(msg.action, msg.params || {})
      : await runAction(msg.action, msg.params || {});
    try { ws.send(JSON.stringify({ request_id: msg.request_id, ...result })); } catch (_) {}
  });

  ws.addEventListener('close', () => {
    hideControlOverlay();  // never leave the indicator stuck up if the connection drops
    if (helperSocket === ws) helperReconnectTimer = setTimeout(connectHelper, 5000);
  });
  ws.addEventListener('error', () => { try { ws.close(); } catch (_) {} });
}

// JasonMax control indicator — an always-on-top overlay shown for the exact
// duration of a real computer-use task, driven by task_start/task_end
// events from the server (not a timeout guess), so the customer always
// knows when Jason genuinely has control of their mouse/keyboard, with an
// immediate Stop affordance rather than only the in-chat Stop button.
let controlOverlay = null;
// Real screen coordinates of the overlay's Stop button while a task is
// running — sent down with every action so action_executor.py can refuse to
// let the automation's OWN synthetic clicks ever land in this region. Without
// this, a stray automated click landing on the same screen pixels as the
// Stop button was indistinguishable from a genuine user click (both just
// look like "the button was clicked" to the overlay's own handler) — this
// makes it categorically impossible for automation to trigger a stop, so any
// stop that does happen is guaranteed to be a real user action.
let controlOverlayRect = null;

function showControlOverlay() {
  if (controlOverlay) return;
  const { screen } = require('electron');
  const { width } = screen.getPrimaryDisplay().workAreaSize;
  const overlayWidth = 340;
  const overlayX = Math.round((width - overlayWidth) / 2);
  const overlayY = 8;
  controlOverlayRect = { x: overlayX, y: overlayY, width: overlayWidth, height: 44 };
  controlOverlay = new BrowserWindow({
    width: overlayWidth,
    height: 44,
    x: overlayX,
    y: overlayY,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    movable: false,
    skipTaskbar: true,
    focusable: true,
    // Safe to relax isolation here specifically: this window's entire HTML
    // is generated locally by this same app (a data: URI, not remote
    // content) — nothing untrusted ever loads in it, unlike mainWindow.
    webPreferences: { nodeIntegration: true, contextIsolation: false },
  });
  controlOverlay.setAlwaysOnTop(true, 'screen-saver');
  controlOverlay.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  controlOverlay.loadURL(
    'data:text/html,' + encodeURIComponent(`
      <body style="margin:0;font-family:-apple-system,sans-serif;background:rgba(20,20,20,0.92);
        color:#fff;border-radius:10px;display:flex;align-items:center;justify-content:space-between;
        padding:0 14px;height:44px;box-sizing:border-box;-webkit-app-region:drag;">
        <span style="font-size:13px;display:flex;align-items:center;gap:8px">
          <span style="width:8px;height:8px;border-radius:50%;background:#ff453a;
            box-shadow:0 0 6px #ff453a;"></span>
          Jason is in control of this Mac
        </span>
        <button id="stopBtn" style="-webkit-app-region:no-drag;background:#ff453a;color:#fff;
          border:none;padding:6px 14px;border-radius:6px;font-weight:600;cursor:pointer;font-size:12px">
          Stop
        </button>
        <script>
          document.getElementById('stopBtn').onclick = () => {
            require('electron').ipcRenderer.send('jasonmax-stop-clicked');
          };
        </script>
      </body>
    `)
  );
}

function hideControlOverlay() {
  controlOverlayRect = null;
  if (!controlOverlay) return;
  try { controlOverlay.close(); } catch (_) {}
  controlOverlay = null;
}

// The overlay's Stop button lives in a renderer with nodeIntegration on, so
// it can call ipcRenderer.send directly — this is the main-process side that
// actually relays it to the server over the same socket the helper uses for
// everything else. Server-side, bridge.should_stop() picks this up at the
// top of the next loop iteration.
ipcMain.on('jasonmax-stop-clicked', () => {
  if (helperSocket && helperSocket.readyState === WebSocket.OPEN) {
    try { helperSocket.send(JSON.stringify({ event: 'stop_requested' })); } catch (_) {}
  }
  hideControlOverlay();  // reflect the stop immediately rather than waiting on task_end
});

function handlePairUrl(url) {
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== 'jason:' || parsed.hostname !== 'pair') return;
    const token = parsed.searchParams.get('token');
    if (!token) return;
    saveConfig({ token });
    connectHelper();
    if (mainWindow) {
      mainWindow.webContents.executeJavaScript(
        `window._jasonMaxPaired && window._jasonMaxPaired(); void 0;`
      ).catch(() => {});
    }
  } catch (_) { /* malformed URL — ignore */ }
}

app.setAsDefaultProtocolClient('jason');

let mainWindow;

// Single-instance lock (prevent multiple app instances)
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
}

// Auto-heal transient load failures the same way Calm Desk's shell does:
// retry a few times, clearing this session's service-worker + cache-storage
// first so the retry fetches the current deployment rather than a stale
// cached bundle. errorCode -3 is ERR_ABORTED (normal navigation/redirect)
// and is ignored. Cookies/logins are untouched.
function attachRetry(contents) {
  let tries = 0;
  contents.on('did-finish-load', () => { tries = 0; });
  contents.on('did-fail-load', (_e, errorCode, _desc, _url, isMainFrame) => {
    if (!isMainFrame || errorCode === -3 || tries >= 3) return;
    tries += 1;
    setTimeout(() => {
      try {
        contents.session
          .clearStorageData({ storages: ['serviceworkers', 'cachestorage'] })
          .catch(() => {})
          .finally(() => { try { contents.reloadIgnoringCache(); } catch (_) {} });
      } catch (_) { /* noop */ }
    }, 700 * tries);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  mainWindow.loadURL(APP_URL);
  attachRetry(mainWindow.webContents);

  if (process.env.JASON_DEV) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Links the app itself doesn't handle internally should open in the
  // system browser, not hijack this window.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    require('electron').shell.openExternal(url);
    return { action: 'deny' };
  });

  // TEMPORARY diagnostic (2026-09-02): forward the page's own console output
  // to a plain log file so a real mic-input failure can be read directly,
  // instead of guessing at what the site's JS is doing. Remove once the mic
  // issue is confirmed fixed.
  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    try {
      fs.appendFileSync(
        path.join(os.tmpdir(), 'jason-console.log'),
        `[${new Date().toISOString()}] level=${level} ${sourceId}:${line} ${message}\n`
      );
    } catch (_) { /* noop */ }
  });

  // A jason://pair link clicked from Settings is a SAME-window navigation
  // (window.location.href, not a new tab/window), so setWindowOpenHandler
  // above never sees it. Electron doesn't hand same-window custom-protocol
  // navigations off to the OS the way a real browser does — left alone, it
  // just fails to load and looks like nothing happened. Since we're already
  // running inside the exact app that should handle this, no OS round-trip
  // is needed at all — catch it here and handle it directly, in-process.
  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (url.startsWith('jason://')) {
      event.preventDefault();
      handlePairUrl(url);
    }
  });
}

// Electron denies every permission request by default (mic, camera, etc.)
// unless the main process explicitly allows it — this app loads a real web
// page (APP_URL) that calls getUserMedia() for voice input, and that call
// was silently failing with no handler here at all. Scoped to APP_URL's own
// origin only, so a link opened inside this window can't piggyback on the
// grant. session.defaultSession only exists once Electron's app is actually
// ready — calling it at module load time throws "Session can only be
// received when app is ready", so this has to live inside app.on('ready'),
// not at the top level.
const APP_ORIGIN = new URL(APP_URL).origin;

app.on('ready', () => {
  session.defaultSession.setPermissionCheckHandler((_webContents, permission, requestingOrigin) => {
    if (permission === 'media' && requestingOrigin === APP_ORIGIN) return true;
    return false;
  });
  session.defaultSession.setPermissionRequestHandler((_webContents, permission, callback, details) => {
    const requestingOrigin = details && details.requestingUrl ? new URL(details.requestingUrl).origin : null;
    callback(permission === 'media' && requestingOrigin === APP_ORIGIN);
  });

  createWindow();
  createMenu();
  connectHelper();  // reconnects automatically if already paired from a prior run
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

// macOS: jason://pair?token=... links (including ones clicked inside this
// app's own webview) arrive here, not as a page navigation.
app.on('open-url', (event, url) => {
  event.preventDefault();
  handlePairUrl(url);
});

app.on('second-instance', (_event, argv) => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  }
  // Windows/Linux equivalent of open-url: the protocol URL shows up as an argv entry.
  const pairArg = argv.find((a) => a.startsWith('jason://pair'));
  if (pairArg) handlePairUrl(pairArg);
});

function createMenu() {
  const template = [
    {
      label: 'Jason',
      submenu: [
        { label: 'About Jason', role: 'about' },
        { type: 'separator' },
        { label: 'Quit Jason', accelerator: 'Cmd+Q', click: () => app.quit() },
      ],
    },
    {
      label: 'Edit',
      submenu: [
        { label: 'Undo', accelerator: 'Cmd+Z', role: 'undo' },
        { label: 'Redo', accelerator: 'Cmd+Shift+Z', role: 'redo' },
        { type: 'separator' },
        { label: 'Cut', accelerator: 'Cmd+X', role: 'cut' },
        { label: 'Copy', accelerator: 'Cmd+C', role: 'copy' },
        { label: 'Paste', accelerator: 'Cmd+V', role: 'paste' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { label: 'Reload', accelerator: 'Cmd+R', role: 'reload' },
        { label: 'Force Reload', accelerator: 'Cmd+Shift+R', role: 'forceReload' },
        { type: 'separator' },
        { label: 'Toggle Dev Tools', accelerator: 'Cmd+Alt+I', role: 'toggleDevTools' },
      ],
    },
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}
