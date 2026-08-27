<script>
  import { createEventDispatcher, onMount } from "svelte";

  export let activeMode = "quant"; // "quant" | "grok"
  const dispatch = createEventDispatcher();

  onMount(() => {
    try {
      const saved = localStorage.getItem("fc_persona_mode");
      if (saved === "grok" || saved === "quant") {
        activeMode = saved;
        dispatch("change", activeMode);
      }
    } catch {}
  });

  function setMode(mode) {
    activeMode = mode;
    try {
      localStorage.setItem("fc_persona_mode", mode);
    } catch {}
    dispatch("change", activeMode);
  }
</script>

<div class="inline-flex items-center rounded-xl bg-slate-950/80 p-1 border border-white/10 shadow-lg text-xs">
  <button
    type="button"
    on:click={() => setMode("quant")}
    class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-bold transition-all {activeMode === "quant" ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shadow-sm" : "text-slate-400 hover:text-slate-200"}"
  >
    <span>🔬</span>
    <span>Quant Mode</span>
  </button>
  <button
    type="button"
    on:click={() => setMode("grok")}
    class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-bold transition-all {activeMode === "grok" ? "bg-orange-500/20 text-orange-400 border border-orange-500/30 shadow-sm animate-pulse" : "text-slate-400 hover:text-slate-200"}"
  >
    <span>🌶️</span>
    <span>Grok Pundit</span>
  </button>
</div>
