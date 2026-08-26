import os
import sys
import traceback

# Add current directory to path
sys.path.append(os.path.dirname(__file__))
# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

service_type = os.environ.get("SERVICE_TYPE", "ml")
print(f"🚀 Dispatcher: SERVICE_TYPE={service_type}", flush=True)

if service_type == "backend":
    print("🔄 Routing to Data API (main.py)", flush=True)
    app_import = "main:app"
    # Pre-test the import so errors are visible
    try:
        import main  # noqa: F401
        print("✅ main.py imported successfully", flush=True)
    except Exception as e:
        print(f"❌ FATAL: Failed to import main.py: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)
elif service_type == "discord":
    print("🤖 Routing to Discord Bot (scripts/discord_bot.py)", flush=True)
    import subprocess

    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
    bot_script = os.path.join(scripts_dir, "discord_bot.py")
    sys.exit(subprocess.call([sys.executable, bot_script]))
elif service_type == "telegram":
    print("📱 Routing to Telegram Bot (scripts/telegram_bot.py)", flush=True)
    import subprocess

    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
    bot_script = os.path.join(scripts_dir, "telegram_bot.py")
    sys.exit(subprocess.call([sys.executable, bot_script]))
else:
    print("🤖 Routing to ML API (ml_api_impl.py)", flush=True)
    app_import = "ml_api_impl:app"

if __name__ == "__main__":
    try:
        import uvicorn
        port = int(os.environ.get("PORT", 8000))
        workers = int(os.environ.get("WEB_CONCURRENCY", 1))
        print(f"Starting {app_import} on port {port} with {workers} worker(s)...", flush=True)
        uvicorn.run(app_import, host="0.0.0.0", port=port, workers=workers)
    except Exception as e:
        print(f"❌ FATAL: uvicorn failed to start: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)

