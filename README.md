# BugLens — connected frontend + backend

This integration bundle connects Member 2's existing `index.html` frontend to Member 1's AI function and Member 3's SQLite/duplicate-detection modules.

## How the pieces connect

- `index.html`: Member 2's BugLens UI, adjusted to call the backend on the same origin.
- `agent.py`: structured bug analysis plus post-processing to block unsafe credential requests while preserving normal labels such as `password-reset`.
- `model_client.py`: Ollama HTTP client (`OLLAMA_MODEL` defaults to `qwen2.5:3b`). If Member 1 has a different working model client, compare and use that team's final connector.
- `database.py`: SQLite storage and status updates, based on Member 3's version with stricter title/description validation.
- `duplicate_detector.py`: Member 3's TF-IDF/cosine similarity matching.
- `server.py`: Flask API adapter that maps `missing_information` ↔ `missing_info` and `similarity` → `score` for the frontend.

## Windows PowerShell setup

1. Put these files in one folder and open PowerShell in that folder.
2. Create and activate an environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

3. Start Ollama and make sure the model exists. If you're using the default model:

   ```powershell
   ollama pull qwen2.5:3b
   ```

   To use another local model, set `$env:OLLAMA_MODEL = "your-model-name"` before starting the server.

4. Start the backend and serve the frontend from the same origin:

   ```powershell
   python server.py
   ```

5. Open **http://127.0.0.1:5000** in your browser. Do not open `index.html` directly with `file://` for the integrated run.

The app stores reports in `issues.db` in the project folder. Keep this file local; it contains submitted reports.

## API contract

- `GET /api/health` — check the service.
- `POST /api/analyze` — accepts `{title, description, expected, actual}` and returns summary, category, component, priority, labels, `missing_info`, `issue_draft`, and `duplicates` with `{id,title,score}`.
- `GET /api/issues` — lists saved reports.
- `POST /api/issues` — persists an approved/rejected report from the review screen.
- `PATCH /api/issues/<id>/status` — changes a saved issue status.

## Tests

```powershell
python test_member1_basic.py
python test_member1_security.py
python test_agent.py
python test_integration.py
```

Integration tests mock the AI response so they test the API/data flow without needing a running model. To test live AI behavior, run the UI with Ollama running.

## Important team note

This is an integration working copy. Before merging, compare `agent.py` and `model_client.py` against Member 1's latest reviewed files, and compare `database.py`/`duplicate_detector.py` against Member 3's latest commit. Keep the function/output contract stable. `agent.py` should be tested with Member 1's security regression tests before accepting it as final.
