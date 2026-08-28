<script>
  import PersonaToggle from "./PersonaToggle.svelte";

  export let single = null;

  let isExpanded = false;
  let personaMode = "quant"; // "quant" | "grok"

  $: edgePct = typeof single?.edge_pct === "number" ? single.edge_pct : null;
  $: consProb = typeof single?.conservative_probability === "number" ? (single.conservative_probability * 100).toFixed(1) : null;
  $: impliedProb = typeof single?.implied_probability === "number" ? (single.implied_probability * 100).toFixed(1) : null;
  $: odds = typeof single?.odds === "number" && single.odds > 0 ? single.odds : null;
  $: market = single?.market || null;
  $: match = single?.match || null;
  $: agreeingModels = typeof single?.agreeing_models === "number" && typeof single?.total_models === "number"
    ? `${single.agreeing_models} of ${single.total_models} Models`
    : "Agreement data unavailable";
  $: agreeingModelNames = Array.isArray(single?.agreeing_model_names) && single.agreeing_model_names.length > 0
    ? single.agreeing_model_names.join(", ")
    : null;
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
      {#if edgePct !== null}
        <span class="text-xs text-emerald-400 font-bold ml-2">+{edgePct}% +EV</span>
      {/if}
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
            <div class="font-black text-sm text-emerald-400 font-mono mt-0.5">
              {edgePct !== null ? `+${edgePct}% +EV` : "Unavailable"}
            </div>
            <div class="text-[10px] text-slate-500">
              {impliedProb ? `vs ${impliedProb}% implied` : "Market floor"}
            </div>
          </div>

          <div class="p-2.5 rounded-lg bg-white/5 border border-white/5">
            <div class="text-[10px] uppercase font-bold text-slate-400">Conservative Win %</div>
            <div class="font-black text-sm text-white font-mono mt-0.5">
              {consProb ? `${consProb}%` : "Unavailable"}
            </div>
            <div class="text-[10px] text-slate-500">Wilson 90% floor</div>
          </div>

          <div class="p-2.5 rounded-lg bg-white/5 border border-white/5">
            <div class="text-[10px] uppercase font-bold text-slate-400">Ensemble Agreement</div>
            <div class="font-black text-sm {agreeingModels.includes("unavailable") ? "text-slate-400" : "text-indigo-400"} font-mono mt-0.5">
              {agreeingModels}
            </div>
            <div class="text-[10px] text-slate-500">
              {agreeingModelNames || "Model details unavailable"}
            </div>
          </div>

          <div class="p-2.5 rounded-lg bg-white/5 border border-white/5">
            <div class="text-[10px] uppercase font-bold text-slate-400">Locked Price</div>
            <div class="font-black text-sm text-amber-400 font-mono mt-0.5">
              {odds ? `@ ${odds}` : "Unavailable"}
            </div>
            <div class="text-[10px] text-slate-500">
              {odds ? "Pre-kickoff price" : "Price pending"}
            </div>
          </div>
        </div>

        <div class="space-y-2 pt-1">
          <div class="flex items-start gap-2 text-slate-300 leading-relaxed">
            <span class="text-emerald-400 font-bold mt-0.5">✔</span>
            <span>
              <strong>Value Pricing:</strong> {impliedProb ? `Market price implies ${impliedProb}%, while the calibrated model establishes a ${consProb || "valid"}% probability floor, locking in positive expected value (+EV).` : "Calibrated models identify positive expected value relative to market price."}
            </span>
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
          {#if market && odds}
            <div class="p-2 rounded-lg bg-black/40 border border-white/5 text-slate-300 text-[11px] font-mono">
              🔥 <strong>Market Position:</strong> Backing <strong>{market} ({single?.selection || "Value Play"}) @ {odds}</strong> based on tactical model edge.
            </div>
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</div>
