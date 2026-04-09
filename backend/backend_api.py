#!/usr/bin/env python3
"""FixtureCast Backend API (Compatibility Wrapper).

The canonical Data API lives in `backend/main.py`.

This module is kept to avoid breaking older start commands that still
reference `backend/backend_api.py`.
"""

from __future__ import annotations

import os
import sys
import traceback

print("🔄 Booting backend_api.py...", flush=True)

try:
    import uvicorn
    # Re-export canonical app
    from main import app  # noqa: F401
    print("✅ Successfully imported main.py", flush=True)
except Exception as e:
    print(f"❌ FATAL: Failed to import main.py: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

if __name__ == "__main__":
    try:
        port = int(os.environ.get("PORT", 8001))
        print(f"Starting FixtureCast Backend API (main.py) on port {port}...", flush=True)
        uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
    except Exception as e:
        print(f"❌ FATAL: Uvicorn crashed: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)
