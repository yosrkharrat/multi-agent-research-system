# 🚀 QUICK START - Multi-Agent Research System

## What You Want to Do
Research: **"What are the key breakthroughs in quantum computing?"**

## Prerequisites (One-Time Setup)

### 1. Install Ollama

**Option A: Automatic Installation** ✅ Easiest
```powershell
cd C:\Users\Admin\multi_agent_research_system
powershell -ExecutionPolicy Bypass -File install-ollama.ps1
```

**Option B: Manual Installation**
1. Visit https://ollama.ai/download
2. Download `Ollama-windows` installer
3. Run the installer
4. Click "Install"

**Option C: Command Line (with Admin PowerShell)**
```powershell
winget install --id Ollama.Ollama -e
```

### 2. Verify Installation
```powershell
ollama --version
# Should output: ollama version X.X.X
```

---

## Running Your Research (Every Time)

### Terminal 1: Start Ollama
```powershell
cd C:\Users\Admin\multi_agent_research_system
powershell -ExecutionPolicy Bypass -File start-ollama.ps1
```

**Wait for this message:**
```
✅ Ollama is ready to use!
Keep this window open while running the research system
```

**⚠️ DO NOT close this terminal while researching!**

---

### Terminal 2: Run Your Research
*Open a NEW PowerShell window AFTER Terminal 1 shows "ready"*

```powershell
cd C:\Users\Admin\multi_agent_research_system
$env:PYTHONPATH = "src"
py research-quantum.py
```

**Expected output:**
```
================================================================================
  MULTI-AGENT RESEARCH SYSTEM
================================================================================

📚 Topic: What are the key breakthroughs in quantum computing?

Building research pipeline...
✅ Graph built

Starting research orchestration...
================================================================================
[Planner] Created 4 research questions
[Researcher] Researching question 1/4...
[Researcher] Researching question 2/4...
[Researcher] Researching question 3/4...
[Researcher] Researching question 4/4...
[Critic] Approved research findings
[Writer] Generating final report...

================================================================================
  ✅ RESEARCH COMPLETE
================================================================================

📄 GENERATED REPORT:

# Quantum Computing: Key Breakthroughs
...
```

**Runtime:** 5-15 minutes depending on your computer

---

## Optional: Start Web API

### Terminal 3: Run API Server
```powershell
cd C:\Users\Admin\multi_agent_research_system
$env:PYTHONPATH = "src"
py run.py
```

Then visit:
- 🌐 **Web UI:** http://localhost:8002
- 📚 **API Docs:** http://localhost:8002/docs

---

## Troubleshooting

### ❌ "Connection refused" Error
```
httpx.ConnectError: [WinError 10061] Aucune connexion n'a pu être établie
```

**Solution:** 
1. Make sure Terminal 1 (Ollama) is still running
2. Check for error messages in Terminal 1
3. Restart both terminals

---

### ❌ "Ollama not found" During Installation
**Solution:** Download manually from https://ollama.ai/download

---

### ❌ Port 11434 Already in Use
```
OSError: Address already in use
```

**Solution:** Stop existing Ollama:
```powershell
Get-Process ollama | Stop-Process
```

---

### ❌ Installation Hangs
- Try Option B (manual download from website)
- Ensure you have administrator rights
- Disable antivirus temporarily

---

## File Reference

| File | Purpose |
|------|---------|
| `install-ollama.ps1` | Auto-download and install Ollama |
| `install-ollama.bat` | Batch version of installer |
| `start-ollama.ps1` | Start Ollama server + pull models |
| `start-ollama.bat` | Batch version of starter |
| `research-quantum.py` | Run quantum computing research |
| `run.py` | Start web API server |

---

## Summary

```
Step 1: powershell -ExecutionPolicy Bypass -File install-ollama.ps1
Step 2: powershell -ExecutionPolicy Bypass -File start-ollama.ps1  (Terminal 1)
Step 3: $env:PYTHONPATH = "src"; py research-quantum.py          (Terminal 2)
```

That's it! Your research will complete in 5-15 minutes. 🎯

---

## Need Help?

- **Installation issues?** → Try manual download from https://ollama.ai/download
- **Runtime issues?** → Check that Terminal 1 (Ollama) is still running
- **System too slow?** → Normal for first run (model caching). Subsequent runs are faster.
- **Out of disk space?** → Ollama needs ~10GB for models. Clear temp files.

---

**You're all set! Run Terminal 1 first, then Terminal 2.** 🚀
