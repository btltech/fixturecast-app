/**
 * FixtureCast AI Chat Widget - Simplified HTTP Version
 * Optimized for Cloudflare free tier (no WebSocket/Durable Objects)
 */

(function() {
  'use strict';

  const config = {
    apiUrl: 'https://ai-assistant-simple.btltech.workers.dev/chat',
    sessionId: 'fixturecast-' + Date.now(),
    primaryColor: '#06b6d4'
  };

  const widgetHTML = `
    <style>
      .fc-widget-btn {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: linear-gradient(135deg, #06b6d4, #0891b2);
        border: none;
        box-shadow: 0 4px 12px rgba(6, 182, 212, 0.4);
        cursor: pointer;
        z-index: 999999;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: transform 0.2s;
      }
      .fc-widget-btn:hover { transform: scale(1.1); }
      .fc-widget-btn svg { width: 28px; height: 28px; fill: white; }
      
      .fc-widget-window {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 380px;
        max-width: calc(100vw - 40px);
        height: 600px;
        max-height: calc(100vh - 40px);
        background: linear-gradient(135deg, #0c4a6e, #075985);
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        z-index: 1000000;
        display: none;
        flex-direction: column;
        overflow: hidden;
      }
      .fc-widget-window.open { display: flex; }
      
      .fc-widget-header {
        background: linear-gradient(135deg, #06b6d4, #0891b2);
        color: white;
        padding: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .fc-widget-title { font-size: 18px; font-weight: 600; }
      .fc-widget-status { font-size: 12px; opacity: 0.9; margin-top: 2px; }
      .fc-close-btn {
        background: none;
        border: none;
        color: white;
        font-size: 24px;
        cursor: pointer;
        padding: 0;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        transition: background 0.2s;
      }
      .fc-close-btn:hover { background: rgba(255,255,255,0.2); }
      
      .fc-messages {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
        background: linear-gradient(135deg, #0c4a6e, #075985);
      }
      .fc-message {
        margin-bottom: 12px;
        padding: 12px 16px;
        border-radius: 12px;
        max-width: 85%;
        word-wrap: break-word;
        animation: fadeIn 0.3s;
      }
      @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
      .fc-message-user {
        background: rgba(255, 255, 255, 0.15);
        color: white;
        margin-left: auto;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-bottom-right-radius: 4px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
      }
      .fc-message-assistant {
        background: rgba(255, 255, 255, 0.1);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-bottom-left-radius: 4px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
      }
      .fc-message-assistant strong { color: #06b6d4; }
      
      .fc-quick-actions {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-top: 12px;
      }
      .fc-quick-btn {
        padding: 8px 12px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        background: rgba(255, 255, 255, 0.1);
        color: white;
        border-radius: 8px;
        cursor: pointer;
        font-size: 13px;
        transition: all 0.2s;
      }
      .fc-quick-btn:hover {
        background: rgba(255, 255, 255, 0.2);
        border-color: rgba(255, 255, 255, 0.5);
        color: white;
      }
      
      .fc-input-container {
        display: flex;
        gap: 8px;
        padding: 16px;
        border-top: 1px solid rgba(255, 255, 255, 0.2);
        background: rgba(0, 0, 0, 0.2);
      }
      .fc-input {
        flex: 1;
        padding: 12px;
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-radius: 8px;
        font-size: 14px;
        color: white;
        background: rgba(255, 255, 255, 0.1);
        resize: none;
        font-family: inherit;
      }
      .fc-input:focus { outline: none; border-color: #38bdf8; box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.3); }
      .fc-input::placeholder { color: rgba(255, 255, 255, 0.6); }
      .fc-send-btn {
        padding: 12px 16px;
        background: #06b6d4;
        color: white;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.2s;
      }
      .fc-send-btn:hover { background: #0891b2; }
      .fc-send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
      .fc-send-btn svg { width: 20px; height: 20px; stroke: currentColor; fill: none; }
      
      .fc-typing {
        display: flex;
        gap: 4px;
        padding: 12px;
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 12px;
        width: fit-content;
      }
      .fc-typing span {
        width: 8px;
        height: 8px;
        background: rgba(255, 255, 255, 0.7);
        border-radius: 50%;
        animation: bounce 1.4s infinite;
      }
      .fc-typing span:nth-child(2) { animation-delay: 0.2s; }
      .fc-typing span:nth-child(3) { animation-delay: 0.4s; }
      @keyframes bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-10px); } }
      
      @media (max-width: 480px) {
        .fc-widget-window {
          width: 100vw;
          height: 100vh;
          bottom: 0;
          right: 0;
          border-radius: 0;
          max-width: 100vw;
          max-height: 100vh;
        }
        .fc-widget-btn { bottom: 16px; right: 16px; }
      }
    </style>

    <button class="fc-widget-btn" id="fc-widget-btn">
      <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 3.3c.41.23.68.66.68 1.15 0 .72-.58 1.3-1.3 1.3-.72 0-1.3-.58-1.3-1.3 0-.49.27-.92.68-1.15.1-.06.2-.1.31-.13.11-.02.23-.03.31-.03s.2.01.31.03c.11.03.21.07.31.13zm-3.5.7c.72 0 1.3.58 1.3 1.3 0 .72-.58 1.3-1.3 1.3-.72 0-1.3-.58-1.3-1.3 0-.72.58-1.3 1.3-1.3zm7 0c.72 0 1.3.58 1.3 1.3 0 .72-.58 1.3-1.3 1.3-.72 0-1.3-.58-1.3-1.3 0-.72.58-1.3 1.3-1.3z"/></svg>
    </button>

    <div class="fc-widget-window" id="fc-widget-window">
      <div class="fc-widget-header">
        <div>
          <div class="fc-widget-title">&#x26BD; FixtureCast AI</div>
          <div class="fc-widget-status">AI-Powered Football Predictions</div>
        </div>
        <button class="fc-close-btn" id="fc-close-btn">&#x2715;</button>
      </div>

      <div class="fc-messages" id="fc-messages">
        <div class="fc-message fc-message-assistant">
          <strong>Welcome to FixtureCast! &#x26BD;</strong><br><br>
          I'm your AI assistant for football predictions. Quick actions:
          <div class="fc-quick-actions">
            <button class="fc-quick-btn" data-msg="What are today's fixtures?">&#x1F4C5; Today's Fixtures</button>
            <button class="fc-quick-btn" data-msg="What's the match of the day?">&#x2B50; Match of the Day</button>
            <button class="fc-quick-btn" data-msg="Show me the Premier League table">&#x1F3C6; PL Table</button>
            <button class="fc-quick-btn" data-msg="Give me accumulator tips">&#x1F4B0; Acca Tips</button>
          </div>
        </div>
      </div>

      <div class="fc-input-container">
        <textarea id="fc-input" class="fc-input" placeholder="Ask about predictions..." rows="1"></textarea>
        <button id="fc-send-btn" class="fc-send-btn">
          <svg viewBox="0 0 24 24" stroke-width="2"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
        </button>
      </div>
    </div>
  `;

  // Inject widget
  const container = document.createElement('div');
  container.innerHTML = widgetHTML;
  document.body.appendChild(container);

  // Elements
  const widgetBtn = document.getElementById('fc-widget-btn');
  const widgetWindow = document.getElementById('fc-widget-window');
  const closeBtn = document.getElementById('fc-close-btn');
  const messagesContainer = document.getElementById('fc-messages');
  const input = document.getElementById('fc-input');
  const sendBtn = document.getElementById('fc-send-btn');

  // Toggle widget
  widgetBtn.addEventListener('click', () => {
    widgetWindow.classList.add('open');
    input.focus();
  });
  closeBtn.addEventListener('click', () => {
    widgetWindow.classList.remove('open');
  });

  // Quick actions
  document.querySelectorAll('.fc-quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const message = btn.getAttribute('data-msg');
      if (message) sendMessage(message);
    });
  });

  // Send message
  async function sendMessage(text) {
    const message = text || input.value.trim();
    if (!message) return;

    // Clear input
    input.value = '';
    input.style.height = 'auto';

    // Add user message
    addMessage(message, 'user');

    // Show typing indicator
    const typingId = showTyping();

    // Disable input
    input.disabled = true;
    sendBtn.disabled = true;

    try {
      const response = await fetch(config.apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message, 
          sessionId: config.sessionId,
          pageUrl: window.location.href
        })
      });

      if (!response.ok) {
        const error = await response.json();
        if (error.retryAfter) {
          throw new Error('You\'re asking too quickly! Please wait ' + error.retryAfter + ' seconds.');
        }
        throw new Error(error.error || 'Failed to send message');
      }

      const data = await response.json();
      removeTyping(typingId);
      addMessage(data.response, 'assistant');

    } catch (error) {
      removeTyping(typingId);
      addMessage('Sorry, something went wrong: ' + error.message, 'assistant');
    } finally {
      input.disabled = false;
      sendBtn.disabled = false;
      input.focus();
    }
  }

  // Add message to UI — uses textContent to prevent XSS
  function addMessage(text, type) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'fc-message fc-message-' + type;
    msgDiv.textContent = text;
    messagesContainer.appendChild(msgDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  // Typing indicator
  function showTyping() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'fc-typing';
    typingDiv.innerHTML = '<span></span><span></span><span></span>';
    typingDiv.id = 'typing-' + Date.now();
    messagesContainer.appendChild(typingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    return typingDiv.id;
  }

  function removeTyping(id) {
    const typingDiv = document.getElementById(id);
    if (typingDiv) typingDiv.remove();
  }

  // Event listeners
  sendBtn.addEventListener('click', () => sendMessage());
  input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Auto-resize textarea
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  });

  console.log('FixtureCast AI Widget loaded');
})();
