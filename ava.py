#!/usr/bin/env python3
"""
AVATHINGS v0 - Local Web Dashboard & Project Launcher
Single-file FastAPI server with embedded UI:
- Pretty JSON textarea editor with instant Save
- Live rendered app cards underneath (Start / Open Folder / About)
"""

import json
import os
import subprocess
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

APPS_FILE = Path(__file__).resolve().parent / "apps.json"

app = FastAPI(title="AvaThings")


class RawJsonPayload(BaseModel):
    content: str


def read_raw_apps() -> str:
    if not APPS_FILE.exists():
        default_data = [
            {
                "name": "VetGems",
                "folder": "C:\\Users\\dev\\Code\\tdg\\vetgems-lake",
                "start_command": "python web_public.py",
                "about": "Public veterinary-practice search site and data lake."
            }
        ]
        write_raw_apps(json.dumps(default_data, indent=2))
        return json.dumps(default_data, indent=2)
    try:
        with open(APPS_FILE, "r", encoding="utf-8") as f:
            parsed = json.load(f)
            return json.dumps(parsed, indent=2)
    except Exception:
        with open(APPS_FILE, "r", encoding="utf-8") as f:
            return f.read()


def write_raw_apps(content: str):
    with open(APPS_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def get_parsed_apps() -> List[dict]:
    try:
        with open(APPS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


@app.get("/api/registry")
def get_registry():
    raw_text = read_raw_apps()
    try:
        parsed = json.loads(raw_text)
    except Exception:
        parsed = []
    return {"raw": raw_text, "apps": parsed}


@app.post("/api/registry")
def save_registry(payload: RawJsonPayload):
    try:
        parsed = json.loads(payload.content)
        if not isinstance(parsed, list):
            raise HTTPException(status_code=400, detail="JSON must be an array of app objects")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    formatted = json.dumps(parsed, indent=2)
    write_raw_apps(formatted)
    return {"status": "saved", "raw": formatted, "apps": parsed}


@app.post("/api/start/{name}")
def start_app_endpoint(name: str):
    apps = get_parsed_apps()
    matched = next((a for a in apps if a.get("name", "").lower() == name.lower()), None)
    if not matched:
        raise HTTPException(status_code=404, detail="App not found")

    folder = matched.get("folder", "")
    command = matched.get("start_command", "")
    target_dir = Path(folder) if folder else Path.cwd()

    if not command:
        raise HTTPException(status_code=400, detail="No start_command defined for this app")

    # Write a small run.bat file in the target directory and launch with os.startfile
    # os.startfile uses the Windows ShellExecute API directly, which guarantees an interactive visible window on the user's desktop
    bat_file = target_dir / "_run.bat"
    bat_content = f"@echo off\r\ntitle {name}\r\ncd /d \"{target_dir}\"\r\n{command}\r\npause\r\n"
    try:
        with open(bat_file, "w", encoding="utf-8") as f:
            f.write(bat_content)
        
        os.startfile(str(bat_file))
        return {"status": "launched", "method": "os.startfile", "command": command}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to launch: {e}")


@app.post("/api/open-folder/{name}")
def open_folder_endpoint(name: str):
    apps = get_parsed_apps()
    matched = next((a for a in apps if a.get("name", "").lower() == name.lower()), None)
    if not matched:
        raise HTTPException(status_code=404, detail="App not found")

    folder = matched.get("folder", "")
    if not folder:
        raise HTTPException(status_code=400, detail="No folder configured")

    path = Path(folder)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Folder does not exist: {folder}")

    try:
        os.startfile(str(path))
        return {"status": "opened", "folder": folder}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open folder: {e}")


HTML_CONTENT = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AVATHINGS</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: '#6366f1'
          }
        }
      }
    }
  </script>
  <style>
    body { background-color: #090d16; font-family: ui-sans-serif, system-ui, sans-serif; }
    textarea { tab-size: 2; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
  </style>
</head>
<body class="text-slate-100 min-h-screen p-6 md:p-10">
  <div class="max-w-4xl mx-auto space-y-8">
    
    <!-- Header -->
    <header class="flex items-center justify-between pb-4 border-b border-slate-800">
      <div class="flex items-center space-x-3">
        <div class="h-8 w-8 rounded-lg bg-indigo-600 flex items-center justify-center font-black tracking-wider text-sm shadow-lg shadow-indigo-500/20">A</div>
        <h1 class="text-2xl font-bold tracking-tight text-white">AVATHINGS</h1>
        <span class="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-indigo-400 border border-slate-700">v0</span>
      </div>
      <span class="text-xs text-slate-400 font-mono">apps.json registry</span>
    </header>

    <!-- Notification Toast -->
    <div id="toast" class="fixed bottom-6 right-6 hidden z-50 px-4 py-3 rounded-lg shadow-xl text-sm font-medium transition-all"></div>

    <!-- Section 1: The Raw JSON Registry (The Source of Truth) -->
    <section class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl space-y-3">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-sm font-semibold uppercase tracking-wider text-slate-300">Registry Source (<code class="text-indigo-400">apps.json</code>)</h2>
          <p class="text-xs text-slate-500 mt-0.5">Edit JSON directly, hit Save, and your app cards update immediately below.</p>
        </div>
        <button id="save-btn" onclick="saveRegistry()" class="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition shadow-sm flex items-center space-x-1.5">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"></path></svg>
          <span>Save JSON</span>
        </button>
      </div>

      <textarea id="json-editor" rows="9" class="w-full bg-slate-950 text-slate-200 border border-slate-800 rounded-lg p-3 text-xs leading-relaxed focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 spellcheck-false"></textarea>
    </section>

    <!-- Section 2: Rendered App Cards -->
    <section class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-slate-400">Launchpad</h2>
        <span id="app-count" class="text-xs text-slate-500 font-mono">0 apps</span>
      </div>

      <div id="apps-container" class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="text-slate-500 text-sm py-6">Loading registry...</div>
      </div>
    </section>

  </div>

  <script>
    const jsonEditor = document.getElementById('json-editor');
    const appsContainer = document.getElementById('apps-container');
    const appCount = document.getElementById('app-count');

    // Tab key indentation support in textarea
    jsonEditor.addEventListener('keydown', function(e) {
      if (e.key === 'Tab') {
        e.preventDefault();
        const start = this.selectionStart;
        const end = this.selectionEnd;
        this.value = this.value.substring(0, start) + "  " + this.value.substring(end);
        this.selectionStart = this.selectionEnd = start + 2;
      }
    });

    function showToast(msg, isError = false) {
      const toast = document.getElementById('toast');
      toast.innerText = msg;
      toast.className = `fixed bottom-6 right-6 z-50 px-4 py-3 rounded-lg shadow-xl text-sm font-medium transition-all ${
        isError ? 'bg-rose-900 border border-rose-700 text-rose-200' : 'bg-emerald-900 border border-emerald-700 text-emerald-200'
      }`;
      toast.classList.remove('hidden');
      setTimeout(() => toast.classList.add('hidden'), 3500);
    }

    async function fetchRegistry() {
      try {
        const res = await fetch('/api/registry');
        const data = await res.json();
        jsonEditor.value = data.raw;
        renderCards(data.apps || []);
      } catch (err) {
        showToast('Failed to load apps.json', true);
      }
    }

    async function saveRegistry() {
      const btn = document.getElementById('save-btn');
      btn.disabled = true;
      try {
        const res = await fetch('/api/registry', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: jsonEditor.value })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Save failed');
        jsonEditor.value = data.raw;
        renderCards(data.apps || []);
        showToast('Saved apps.json');
      } catch (err) {
        showToast(err.message, true);
      } finally {
        btn.disabled = false;
      }
    }

    function renderCards(apps) {
      appCount.innerText = `${apps.length} app${apps.length === 1 ? '' : 's'}`;
      if (!apps || apps.length === 0) {
        appsContainer.innerHTML = `
          <div class="col-span-full border border-dashed border-slate-800 rounded-xl p-8 text-center text-slate-500 text-sm">
            No valid apps found. Add entries in the JSON editor above and click Save.
          </div>
        `;
        return;
      }

      appsContainer.innerHTML = apps.map(app => `
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition flex flex-col justify-between shadow-lg space-y-4">
          <div>
            <h3 class="text-base font-bold text-white tracking-tight">${escapeHtml(app.name || 'Unnamed App')}</h3>
            <p class="text-xs text-slate-400 mt-1 line-clamp-2">${escapeHtml(app.about || 'No description provided.')}</p>

            <div class="mt-3 space-y-1 font-mono text-[11px] text-slate-400 bg-slate-950 p-2.5 rounded-lg border border-slate-800/80">
              <div class="flex items-center space-x-2 truncate">
                <span class="text-slate-600 uppercase font-semibold text-[10px] w-12">Folder</span>
                <span class="truncate text-slate-300" title="${escapeHtml(app.folder)}">${escapeHtml(app.folder || 'N/A')}</span>
              </div>
              <div class="flex items-center space-x-2 truncate">
                <span class="text-slate-600 uppercase font-semibold text-[10px] w-12">Cmd</span>
                <span class="truncate text-indigo-300 font-semibold" title="${escapeHtml(app.start_command)}">${escapeHtml(app.start_command || 'N/A')}</span>
              </div>
            </div>
          </div>

          <div class="flex items-center space-x-2 pt-2 border-t border-slate-800/60">
            <button onclick='startApp("${escapeHtml(app.name)}")' class="flex-1 inline-flex items-center justify-center px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition shadow-sm">
              <svg class="w-3.5 h-3.5 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              Start
            </button>
            <button onclick='openFolder("${escapeHtml(app.name)}")' class="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition border border-slate-700" title="Open Folder">
              <svg class="w-3.5 h-3.5 mr-1 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z"></path></svg>
              Folder
            </button>
          </div>
        </div>
      `).join('');
    }

    async function startApp(name) {
      try {
        const res = await fetch(`/api/start/${encodeURIComponent(name)}`, { method: 'POST' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Start failed');
        showToast(`Launched ${name} (${data.method})`);
      } catch (err) {
        showToast(err.message, true);
      }
    }

    async function openFolder(name) {
      try {
        const res = await fetch(`/api/open-folder/${encodeURIComponent(name)}`, { method: 'POST' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to open folder');
        showToast(`Opened folder for ${name}`);
      } catch (err) {
        showToast(err.message, true);
      }
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    fetchRegistry();
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(content=HTML_CONTENT)


def launch_browser():
    time.sleep(1.0)
    webbrowser.open("http://127.0.0.1:8765")


if __name__ == "__main__":
    threading.Thread(target=launch_browser, daemon=True).start()
    print("Starting AVATHINGS dashboard at http://127.0.0.1:8765 ...")
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
