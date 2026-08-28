<script>
  import PersonaToggle from "./PersonaToggle.svelte";

  export let single = null;

  let isExpanded = false;
  let personaMode = "quant"; // "quant" | "grok"

  $: edgePct = single?.edge_pct || 0;
  $: consProb = single?.conservative_probability ? (single.conservative_probability * 100).toFixed(1) : "0.0";
  $: impliedProb = single?.implied_probability ? (single.implied_probability * 100).toFixed(1) : "0.0";
  $: odds = single?.odds || 0;
  $: market = single?.market || "Match Winner";
  $: match = single?.match || "Match";
  $: agreeingModels = typeof single?.agreeing_models === "number" && typeof single?.total_models === "number"
    ? `${single.agreeing_models} of ${single.total_models} Models`
    : "Agreement data unavailable";
  $: punditText = single?.pundit_take || single?.grok_take || null;
</script>

<div class="mt-4 rounded-xl bg-slate-950/60 border border-white/10 overflow-hidden transition-all duration-300">
  <!-- Expand Header Button -->
  <div class="w-full px-4 py-3 flex flex-wrap items-center justify-between gap-3 bg-white/[0.02]">
    <button
      type="button"
      on:click={() => (isExpanded = !isExpanded)}
      class="flex items-center gap-2 text-left hover:opacity-80 transition"
    >
      <span class="p-1 rounded-md bg-indigo-500/20 text-indigo-400 text-xs font-bold">🧠 AI Match Rationale</span>
      <span class="text-xs font-semibold text-slate-300">Why was this pick selected?</span>
      <span class="text-xs text-emerald-400 font-bold ml-2">+{edgePct}% +EV</span>
      <span class="transform transition-transform duration-200 text-xs text-slate-400 {isExpanded ? "rotate-180" : ""}">▼</span>
    </button>

    <!-- Grok vs Quant Persona Switcher -->
    {#if isExpanded}
      <PersonaToggle bind:activeMode={personaMode} />
    {/if}
  </div>

  {#if isExpanded}
    <div class="px-4 pb-4 pt-2 border-t border-white/10 space-y-4 text-xs">
      {#if personaMode === "quant"}
        <!-- 1. Quant Mode View -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1">
          <div class="p-2.5 rounded-lg bg-white/5 border border-white/5">
            <div class="text-[10px] uppercase font-bold text-slate-400">Mathematical Edge</div>
            <div class="font-black text-sm text-emerald-400 font-mono mt-0.5">+{edgePct}% +EV</div>
            <div class="text-[10px] text-slate-500">vs {impliedProb}% implied</div>
          </div>

          <div class="p-2.5 rounded-lg bg-white/5 border border-white/5">
            <div class="text-[10px] uppercase font-bold text-slate-400">Conservative Win %</div>
            <div class="font-black text-sm text-white font-mono mt-0.5">{consProb}%</div>
            <div class="text-[10px] text-slate-500">Wilson 90% floor</div>
          </div>

          <div class="p-2.5 rounded-lg bg-white/5 border border-white/5">
            <div class="text-[10px] uppercase font-bold text-slate-400">Ensemble Agreement</div>
            <div class="font-black text-sm {agreeingModels.includes("unavailable") ? "text-slate-400" : "text-indigo-400"} font-mono mt-0.5">{agreeingModels}</div>
            <div class="text-[10px] text-slate-500">GBDT, Elo, GNN</div>
          </div>

          <div class="p-2.5 rounded-lg bg-white/5 border border-white/5">
            <div class="text-[10px] uppercase font-bold text-slate-400">Locked Price</div>
            <div class="font-black text-sm text-amber-400 font-mono mt-0.5">@ {odds}</div>
            <div class="text-[10px] text-slate-500">High payout tier</div>
          </div>
        </div>

        <div class="space-y-2 pt-1">
          <div class="flex items-start gap-2 text-slate-300 leading-relaxed">
            <span class="text-emerald-400 font-bold mt-0.5">✔</span>
            <span><strong>Value Pricing:</strong> Market price implies {impliedProb}%, while the calibrated model establishes a {consProb}% probability floor, locking in a positive expected value (+EV).</span>
          </div>
          <div class="flex items-start gap-2 text-slate-300 leading-relaxed">
            <span class="text-emerald-400 font-bold mt-0.5">✔</span>
            <span><strong>Disciplined Allocation:</strong> Flat staking limits exposure and reduces bankroll volatility.</span>
          </div>
        </div>
      {:else}
        <!-- 2. Grok Pundit Mode View (Backend Generated) -->
        <div class="p-3.5 rounded-xl bg-orange-950/20 border border-orange-500/30 text-orange-200 leading-relaxed space-y-2.5">
          <div class="flex items-center gap-2 text-orange-400 font-bold">
            <span>🌶️</span>
            <span class="uppercase tracking-wider text-[11px]">Unfiltered AI Pundit Take</span>
          </div>
          {#if punditText}
            <p class="text-xs text-slate-200">
              {punditText}
            </p>
          {:else}
            <p class="text-xs text-slate-400 italic">
              Pundit analysis is currently unavailable for this selection.
            </p>
          {/if}
          <div class="p-2 rounded-lg bg-black/40 border border-white/5 text-slate-300 text-[11px] font-mono">
            🔥 <strong>Market Position:</strong> Backing <strong>{market} ({single?.selection || "Value Play"}) @ {odds}</strong> based on tactical model edge.
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>
