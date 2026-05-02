# Windows Setup Guide for Multi-Agent Research System

## Prerequisites Checklist

- ✅ Python 3.14 installed
- ✅ All pip dependencies installed (`py -m pip install -r requirements.txt`)
- ✅ Git repository initialized and synced
- ⚠️ **CRITICAL: Ollama must be running**

## Step 1: Install & Run Ollama

### Download Ollama
1. Visit https://ollama.ai/download (Windows)
2. Download and install Ollama
3. Or use winget:
   ```powershell
   winget install --id Ollama.Ollama -e
   ```

### Start Ollama Server

Open a **dedicated PowerShell terminal** and run:
```powershell
ollama serve
```

You should see output like:
```
2026/05/02 15:30:00 - Listening on 127.0.0.1:11434
```

**Keep this terminal running** — the system cannot work without it.

### Pull Required Models

In a **new PowerShell terminal**, pull the models:
```powershell
ollama pull mistral
ollama pull llama3
```

Wait for download to complete. Ollama will cache these models.

## Step 2: Run the Quick Test

In a **new PowerShell terminal** in the project root:

```powershell
$env:PYTHONPATH = "src"
py test_quick.py
```

Expected output:
```
Building graph...
  [Graph] SqliteSaver unavailable; using in-memory checkpointing

[Quick test] Running research on: 'What is machine learning?'
================================================================================
[Planner] Created 4 research questions
[Researcher] Researching: 1. What is machine learning...
  [Researcher] Fetching: https://en.wikipedia.org/wiki/Machine_learning
[Critic] Approved after 1 iteration(s)
[Writer] Generating final report...
================================================================================
=== GENERATED REPORT ===
...
```

**Expected runtime:** 5-10 minutes (depends on hardware and Ollama latency)

## Step 3: Run the API Server

In a **new PowerShell terminal**:

```powershell
$env:PYTHONPATH = "src"
py run.py
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8002 (Press CTRL+C to quit)
```

The API is now live at:
- **API Base:** http://localhost:8002
- **Swagger Docs:** http://localhost:8002/docs
- **Frontend:** http://localhost:8002/

## Terminal Requirements

Keep these terminals open and running:

| Terminal | Command | Purpose |
|----------|---------|---------|
| **Terminal 1** | `ollama serve` | LLM engine (MUST BE RUNNING FIRST) |
| **Terminal 2** | `py run.py` | FastAPI backend |
| **Terminal 3** | Optional: `py test_quick.py` | Test the system |

## Troubleshooting

### "Connection refused" Error
```
httpx.ConnectError: [WinError 10061] Aucune connexion n'a pu être établie
```
→ **Ollama is not running.** Go back to Step 1 and run `ollama serve` in a dedicated terminal.

### Models not found
```
Error: model 'mistral' not found
```
→ **Pull the models first:** `ollama pull mistral && ollama pull llama3`

### Port 8002 already in use
```
OSError: [Errno 10048] Only one usage of each socket address (protocol/port/IP)
```
→ Either:
- Kill existing process: `Get-Process -Name python | Stop-Process`
- Or set custom port: `$env:PORT=8003; py run.py`

### Python not found
```
Python was not found; run without arguments to install from the Microsoft Store
```
→ Use `py` (Python launcher) instead of `python`. All commands use `py` on Windows.

## Verification Checklist

After setup, verify everything works:

```powershell
# Terminal 1: Ollama running
ollama list
# Should show: mistral, llama3

# Terminal 2: API running
curl http://localhost:8002/health
# Should return: {"status":"ok"}

# Terminal 3: Test system
$env:PYTHONPATH = "src"; py test_quick.py
# Should complete without Ollama errors
```

## Next Steps

- **Modify topic:** Edit `test_quick.py` line 14 to research different topics
- **API usage:** See `api/main.py` for endpoint documentation
- **Production deployment:** Use `uvicorn` with proper workers and settings
- **GPU acceleration:** Set `OLLAMA_GPU=1` before running (if you have CUDA/Metal GPU)

## Key Ports

- **8002** – FastAPI server (configurable via `PORT` env var)
- **11434** – Ollama API (internal, fixed)

## Documentation

- `README.md` – Architecture overview
- `PHASE3_ARCHITECTURE.md` – Detailed system design
- `api/main.py` – API endpoint reference
- `src/agents/graph.py` – LangGraph orchestration

---

**Questions?** Check logs in the terminal where the error occurred. The full stack trace usually points to the issue.
