PyRun — Core Execution Engine Prototype

> Empower Global Tech AI Pvt. Ltd. — Full Stack Web Developer Intern Assignment

A code execution engine where users write Python, click Run, and see the output — with a strict 2-second timeout to prevent infinite loops.

Project Structure



pyrun/
├── main.py           # FastAPI server with embedded frontend
├── requirements.txt  # Python dependencies
├── static/
│   └── index.html    # Frontend UI
└── README.md
```

---

## How to Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload --port 8000
```

Then open <http://localhost:8000>

---

## Deploy to Render

1. Push your code to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port 10000`
5. Click Create Web Service

Your app will be live at `https://your-app.onrender.com`

---

 Test Cases

| :--- | :--- | :--- |
|------|------|----------|
| Success | `print("Hello Empower")` | Returns `Hello Empower` |
| Timeout | `while True: pass` | Returns timeout error after 2 seconds |

---

 Keyboard Shortcuts

- **Ctrl + Enter** — Run code
- **Tab** — Insert 4 spaces

---

 Security Risks

> ⚠️ **Important:** This implementation runs arbitrary user code on the server. For production use, you must address these risks.

1. Arbitrary Code Execution
The server executes any Python code submitted by users with full access to the host OS. A malicious user could access environment variables, read sensitive files, or exfiltrate data.

Risk: `os.environ`, `open("/etc/passwd")`, `subprocess` calls from within Python.

2. File System Access
Users can read/write files anywhere the server process has permission.

Risk: `open("/root/.ssh/id_rsa")`, writing to arbitrary directories.

3. Network Access
Submitted code can make outbound HTTP requests, potentially acting as a proxy or exfiltrating data.

Risk: `requests` library, `socket` connections to external services.

4. Fork Bombs
A single `os.fork()` loop can exhaust all process slots before the 2-second timeout kills it, crashing the server for all users.

Risk: `"while True: os.fork()"` on Linux/Render.

5. Memory Exhaustion
Large allocations like `"A" * 10**10` can OOM-kill the server process before the timeout fires.

Risk: Render's free tier has 512MB RAM — a 400MB allocation is trivial.

6. No Rate Limiting
Anyone can hit `/run` unlimited times, enabling easy denial-of-service attacks.

Risk: A single user can spam 1000 requests/minute, blocking legitimate users.

7. Race Conditions
In high concurrency, temp file cleanup can conflict between requests.

Risk:Concurrent requests using overlapping temp file names.

 Recommended Production Fixes

| Risk | Solution |
|:-----|:---------|
| Host access | Run code in **Docker containers** with `--network none --memory 64m --read-only` |
| Memory bombs | Enforce Docker `--memory` limits and Python-side recursion/memory limits |
| Rate limiting | Add **API gateway rate limiting** (e.g., 5 runs/minute per IP) |
| Fork bombs | Use Docker `--pids-limit 64` and cgroup process limits |
| Concurrent load | Move execution to an **async queue** (Redis/Celery) |

---

Scaling to 500 Concurrent Students

The current single-process model blocks on each execution (up to 2 seconds). With 500 simultaneous "Run" clicks, the server would exhaust all worker threads and crash.

Recommended Architecture

```
Students → Load Balancer → API Replicas → Redis Queue → Worker Pool → Docker Containers
```

1. API Layer (FastAPI replicas)
- Multiple FastAPI instances behind a load balancer
- Each request immediately returns a `job_id` (no blocking)
- Jobs are pushed to Redis queue

2. Queue (Redis + Celery)
- API sends `{ user_code, job_id }` to Redis
- Workers pick up jobs asynchronously
- Frontend polls `GET /result/{job_id}` every 500ms

3. Worker Pool
- Celery workers run in separate processes/pods
- Each worker executes code inside a     throwaway Docker container
- Container is destroyed after execution

4. Docker Isolation (per job)
```bash
docker run --rm \
  --network none \
  --memory 64m \
  --cpus 0.5 \
  --pids-limit 64 \
  --read-only \
  python:3.12-slim \
  python /code/main.py
```

This ensures:
- No network access (can't exfiltrate data)
- No file system access (read-only or tmpfs only)
- Memory limit enforced by kernel
- CPU limit prevents CPU bombs
- PID limit prevents fork bombs

 Why This Works

| Without Queue | With Queue |
|:-------------|:-----------|
| 500 requests → 500 blocked threads → crash | 500 requests → 500 instant job IDs → 5 workers process in batches |
| Each "Run" blocks for 2 seconds | API responds in <5ms |
| One crash affects all users | Isolated Docker containers fail independently |

 Deployment Options

| Platform | Approach |
|:---------|:---------|
| **Render** | Use **Background Workers** (Celery on Redis) + **Web Service** (API) |
| **Railway** | Private repo + separate web + worker services |
| **Kubernetes** | HPA auto-scales API + worker pods based on queue depth |

