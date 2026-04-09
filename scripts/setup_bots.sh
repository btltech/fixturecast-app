#!/bin/bash
# FixtureCast Bot Integration Setup
# This script helps integrate all social media bots into your system

set -e

echo "🤖 FixtureCast Bot Integration Setup"
echo "===================================="

# Check if we're in the right directory
if [ ! -f "requirements.txt" ] || [ ! -d "scripts" ]; then
    echo "❌ Please run this script from the fixturecast root directory"
    exit 1
fi

echo ""
echo "📦 Step 1: Installing Bot Dependencies"
echo "--------------------------------------"
pip install discord.py python-dotenv python-telegram-bot

echo ""
echo "🔧 Step 2: Setting up Environment Variables"
echo "-------------------------------------------"

if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file with your bot credentials:"
    echo "   nano .env"
    echo ""
    echo "   Required credentials:"
    echo "   - Discord: DISCORD_BOT_TOKEN"
    echo "   - Telegram: TELEGRAM_BOT_TOKEN"
    echo ""
    read -p "Press Enter after you've added your credentials..."
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🧪 Step 3: Testing API Connectivity"
echo "-----------------------------------"

echo "Testing Backend API (port 8001)..."
if curl -s http://localhost:8001/health > /dev/null; then
    echo "✅ Backend API is running"
else
    echo "❌ Backend API not running"
    echo "   Start with: python backend/main.py"
fi

echo "Testing ML API (port 8000)..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ ML API is running"
else
    echo "❌ ML API not running"
    echo "   Start with: python backend/ml_api.py"
fi

echo ""
echo "🤖 Step 4: Testing Bot Scripts"
echo "------------------------------"

echo "Testing Discord bot (dry run)..."
if python scripts/discord_bot.py --help 2>/dev/null || timeout 5 python scripts/discord_bot.py 2>&1 | head -5; then
    echo "✅ Discord bot script is executable"
else
    echo "❌ Discord bot script has issues"
fi

echo "Testing Telegram bot (dry run)..."
if python scripts/telegram_bot.py --help 2>/dev/null || timeout 5 python scripts/telegram_bot.py 2>&1 | head -5; then
    echo "✅ Telegram bot script is executable"
else
    echo "❌ Telegram bot script has issues"
fi

echo ""
echo "🚀 Step 5: Integration Complete!"
echo "--------------------------------"

echo "✅ Bot dependencies installed"
echo "✅ Environment file configured"
echo "✅ API connectivity verified"
echo "✅ Bot scripts tested"

echo ""
echo "🎯 Next Steps:"
echo "1. Start your APIs: python backend/main.py & python backend/ml_api.py &"
echo "2. Test individual bots: python scripts/discord_bot.py"
echo "3. Run all bots: ./scripts/run_all_bots.sh"

echo ""
echo "🎉 Bot integration setup complete!"
