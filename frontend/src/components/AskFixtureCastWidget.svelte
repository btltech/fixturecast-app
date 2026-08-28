<script>
  import { BACKEND_API_URL } from "../config.js";

  let isOpen = false;
  let inputMessage = "";
  let loading = false;
  let messages = [
    {
      sender: "bot",
      text: "👋 Hey! I am FixtureCast AI. Ask me about today's top value bets, match xG breakdowns, or model win probabilities across European leagues!"
    }
  ];

  async function sendMessage() {
    if (!inputMessage.trim() || loading) return;
    const userText = inputMessage.trim();
    inputMessage = "";
    messages = [...messages, { sender: "user", text: userText }];
    loading = true;

    try {
      const res = await fetch(`${BACKEND_API_URL}/api/assistant/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText })
      });
      if (res.ok) {
        const data = await res.json();
        messages = [...messages, { sender: "bot", text: data.reply || "Analysis complete." }];
      } else {
        messages = [...messages, { sender: "bot", text: "I couldn't reach the analysis engine right now. Please try asking again in a moment." }];
      }
    } catch (e) {
      messages = [...messages, { sender: "bot", text: "Live analysis is currently unavailable. Please check back shortly." }];
    } finally {
      loading = false;
    }
  }

  function handleKeydown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }
</script>

<!-- Floating Launcher Button -->
<div class="fixed bottom-20 md:bottom-6 right-4 md:right-6 z-50">
  {#if !isOpen}
    <button
      type="button"
      on:click={() => isOpen = true}
      class="flex items-center gap-2.5 px-4 py-3 rounded-full bg-gradient-to-r from-emerald-500 via-teal-500 to-indigo-600 text-slate-950 font-black text-xs shadow-2xl hover:scale-105 active:scale-95 transition-all border border-white/20"
      aria-label="Open AI Assistant"
    >
      <span class="text-base">🤖</span>
      <span class="tracking-wide">Ask FixtureCast</span>
      <span class="w-2 h-2 rounded-full bg-emerald-300 animate-ping"></span>
    </button>
  {:else}
    <!-- Open Chat Window -->
    <div class="w-80 sm:w-96 h-[460px] rounded-2xl bg-slate-950/95 border border-white/10 shadow-2xl flex flex-col overflow-hidden backdrop-blur">
      <!-- Chat Header -->
      <div class="px-4 py-3 bg-white/5 border-b border-white/10 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="p-1 rounded-md bg-emerald-500/20 text-emerald-400 text-xs">🤖</span>
          <div>
            <div class="font-bold text-xs text-white">FixtureCast AI Assistant</div>
            <div class="text-[10px] text-emerald-400 font-mono">7-Model Live Engine</div>
          </div>
        </div>
        <button
          type="button"
          on:click={() => isOpen = false}
          class="p-1 rounded-lg text-slate-400 hover:text-white text-xs font-bold"
        >
          ✕
        </button>
      </div>

      <!-- Messages Stream -->
      <div class="flex-1 p-3.5 overflow-y-auto space-y-3 text-xs">
        {#each messages as msg}
          <div class="flex flex-col {msg.sender === 'user' ? 'items-end' : 'items-start'}">
            <div class="max-w-[85%] px-3.5 py-2.5 rounded-2xl leading-relaxed {msg.sender === 'user' ? 'bg-emerald-500 text-slate-950 font-medium' : 'bg-slate-900 border border-white/10 text-slate-200'}">
              {msg.text}
            </div>
          </div>
        {/each}
        {#if loading}
          <div class="flex items-center gap-2 text-slate-400 text-[11px] italic">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            Analyzing match models and odds...
          </div>
        {/if}
      </div>

      <!-- Input Bar -->
      <div class="p-3 bg-slate-900 border-t border-white/10 flex gap-2">
        <input
          type="text"
          bind:value={inputMessage}
          on:keydown={handleKeydown}
          placeholder="Ask about matches, xG, or value bets..."
          class="flex-1 px-3 py-2 rounded-xl bg-slate-950 border border-white/10 text-white text-xs placeholder-slate-500 focus:outline-none focus:border-emerald-500"
        />
        <button
          type="button"
          on:click={sendMessage}
          disabled={loading || !inputMessage.trim()}
          class="px-3 py-2 rounded-xl bg-emerald-500 text-slate-950 font-bold text-xs disabled:opacity-40"
        >
          Send
        </button>
      </div>
    </div>
  {/if}
</div>
