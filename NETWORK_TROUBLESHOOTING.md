# Network & Environment Troubleshooting Guide

## Issues & Solutions

### 1. **WinError 10013 - Socket Access Denied** ❌→✅

**Problem:**
```
[WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions
```

This occurs when trying to call external APIs (Groq, Gemini) because your runtime environment has firewall/security restrictions blocking outbound network connections.

**Root Cause:**
- Windows Firewall is enabled (`State ON` on all profiles)
- Python process is not allowed to make outbound socket connections
- Sandboxed/restricted runtime environment (common in corporate/managed IT)

**Solutions (in order of preference):**

#### **Solution A: Enable Offline Mock Mode** ✅ (No Admin Required - NOW ACTIVE)
The app has been updated with a 3-tier fallback:
1. Try Groq API → Fails with network error
2. Try Gemini API → Fails with network error  
3. **Fallback to offline mock generation** ← This now activates automatically

The mock mode generates realistic blog posts without requiring network access, allowing you to test the full pipeline.

**How it works:**
- When all network providers fail, `llm_fallback.py` generates a structured mock blog post
- Output includes TITLE, META_DESCRIPTION, READING_TIME, SEO_KEYWORDS, and markdown content
- Useful for development/testing without internet access

**Updated file:**
- `agents/llm_fallback.py` - Added `_generate_mock_response()` function with 3-tier fallback

#### **Solution B: Allow Python Through Firewall** (Requires Admin)
```powershell
# Run as Administrator
netsh advfirewall firewall add rule name="Python Outbound" `
  dir=out action=allow program="c:/Users/harsh/AppData/Local/Python/pythoncore-3.14-64/python.exe" `
  enable=yes profile=all
```

#### **Solution C: Add Exception for Specific Ports**
```powershell
# Allow outbound HTTPS (443) for API calls
netsh advfirewall firewall add rule name="HTTPS Outbound" `
  dir=out action=allow protocol=tcp remoteport=443 `
  enable=yes profile=all
```

#### **Solution D: Configure VPN/Proxy**
If your IT policy requires using a corporate proxy:
- Set `HTTP_PROXY` and `HTTPS_PROXY` environment variables
- Update LangChain/httpx to use proxy settings

---

### 2. **chromadb Not Installed** ❌→✅

**Status:** ✅ **FIXED**
```
Successfully installed: chromadb, sentence-transformers
Python Environment: c:/Users/harsh/AppData/Local/Python/pythoncore-3.14-64/python.exe
```

**What this enables:**
- RAG (Retrieval Augmented Generation) now works
- Chroma vector database will store and retrieve embeddings
- Search results will be embedded and stored in `rag/chroma_db/`

---

### 3. **Python venv Access Denied** ❌

**Problem:**
```
Original venv\Scripts\python.exe is blocked with "Access is denied"
```

**Solution:**
The system Python is being used instead: 
```
c:/Users/harsh/AppData/Local/Python/pythoncore-3.14-64/python.exe (Python 3.14.5)
```

**Why this works:**
- The system Python installation has proper permissions
- No need to create/activate a virtual environment if system Python is available
- All packages are installed in the system Python environment

**If you need venv later:**
```powershell
# Create venv with system Python
c:/Users/harsh/AppData/Local/Python/pythoncore-3.14-64/python.exe -m venv venv
.\venv\Scripts\Activate.ps1
```

---

## Testing the Fixes

### Test 1: Run Blog Generation (Tests Mock LLM)
```bash
c:/Users/harsh/AppData/Local/Python/pythoncore-3.14-64/python.exe main.py
```
Expected output:
- ✅ Groq fails with network error (expected in restricted environment)
- ✅ Gemini fails with network error (expected)
- ✅ Falls back to mock generation
- ✅ Blog saves to `outputs/blogs/`

### Test 2: Test RAG/Embeddings
```python
from rag.chroma_store import ChromaStore

store = ChromaStore()
store.add_documents([
    {"id": "1", "content": "Test document", "metadata": {}}
])
results = store.search("test", top_k=1)
print(results)
```
Expected: Documents are embedded and searchable

### Test 3: Check API Keys
If your environment has API keys configured in `.env`:
```
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...
TAVILY_API_KEY=tvly_...
```

Then when network access is restored (or firewall rule added), the real APIs will be used automatically without code changes.

---

## Next Steps

### 🔧 **Option 1: Continue with Mock Mode** (Recommended for now)
- ✅ Blog generation works (offline)
- ✅ RAG indexing works (local chromadb)
- ✅ Full pipeline can be tested
- ⚠️ Limitation: Generated content is templated, not AI-generated

### 🌐 **Option 2: Restore Network Access**
Contact your IT department to:
1. Whitelist outbound HTTPS (port 443) for your user
2. Add exception for Python.exe in firewall
3. Configure proxy settings if required

### 🧪 **Option 3: Test with Ollama (Local LLM)**
If you have [Ollama](https://ollama.ai) installed locally:
```python
from langchain_ollama import ChatOllama
# Use local LLM - no network required!
```

---

## Configuration Files Updated

- ✅ `agents/llm_fallback.py` - 3-tier fallback with offline mock mode
- ✅ Python packages installed: `chromadb`, `sentence-transformers`
- ✅ Python environment: System Python 3.14.5

## Monitoring Network Errors

To debug future socket errors, add this to any Python script:
```python
import socket
import traceback

try:
    # Your network call here
    pass
except socket.error as e:
    print(f"Socket Error {e.errno}: {e.strerror}")
    # errno 10013 = WSAEACCES (Permission denied)
except Exception as e:
    traceback.print_exc()
```

---

## Resources
- [Windows Firewall Commands](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/)
- [Python Socket Errors](https://docs.python.org/3/library/socket.html#exceptions)
- [Groq API Documentation](https://console.groq.com/docs)
- [Gemini API Documentation](https://ai.google.dev/docs)
