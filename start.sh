#!/bin/bash
set -e

echo "SERVICE_TYPE: ${SERVICE_TYPE:-backend}"
echo "PORT: ${PORT:-8001}"

if [ "$SERVICE_TYPE" = "backend" ]; then
    cd /app/backend && python backend_api.py
elif [ "$SERVICE_TYPE" = "discord" ]; then
    cd /app && python scripts/discord_bot.py
elif [ "$SERVICE_TYPE" = "telegram" ]; then
    cd /app && python scripts/telegram_bot.py
elif [ "$SERVICE_TYPE" = "scheduler" ]; then
    cd /app && python scripts/scheduled_tasks.py
else
    cd /app/backend && python main.py
fi
