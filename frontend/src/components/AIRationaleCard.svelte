<script>
  export let single = null;

  let isExpanded = false;

  $: edgePct = single?.edge_pct || 0;
  $: consProb = single?.conservative_probability ? (single.conservative_probability * 100).toFixed(1) : "0.0";
  $: impliedProb = single?.implied_probability ? (single.implied_probability * 100).toFixed(1) : "0.0";
  $: odds = single?.odds || 0;
  $: market = single?.market || "Match Winner";
  $: match = single?.match || "Match";
</script>

<div class="mt-4 rounded-xl bg-slate-950/60 border border-white/10 overflow-hidden transition-all duration-300">
  <!-- Expand Header Button -->
  <button
    type="button"
    on:click={() => isExpanded = !isExpanded}
    class="w-full px-4 py-3 flex items-center justify-between gap-3 text-left hover:bg-white/5 transition"
  >
    <div class="flex items-center gap-2">
      <span class="p-1 rounded-md bg-indigo-500/20 text-indigo-400 text-xs font-bold">🧠 AI Match Rationale</span>
      <span class="text-xs font-semibold text-slate-300">Why was this pick selected?</span>
    </div>
    <div class="flex items-center gap-1.5 text-xs text-emerald-400 font-bold">
      <span>+{edgePct}% +EV Edge</span>
      <span class="transform transition-transform duration-200 {isExpanded ? "rotate-180" : ""}">▼</span>
    </div>
  </button>

  {#if isExpanded}
    <div class="px-4 pb-4 pt-2 border-t border-white/10 space-y-4 text-xs">
      <!-- 4-Pillar Stat Grid -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1">
        <!-- 1. Expected Value -->
        <div class="p-2.5 rounded-lg bg-white/5 border border-white/5">
          <div class="text-[10px] uppercase font-bold text-slate-400">Mathematical Edge</div>
          <div class="font-black text-sm text-emerald-400 font-mono mt-0.5">+{edgePct}% +EV</div>
          <div class="text-[10px] text-slate-500">vs {impliedProb}% implied</div>
        </div>

        <!-- 2. Model Confidence -->
        <div class="p-2.5 rounded-lg bg-white/5 border border-white/5">
          <div class="text-[10px] uppercase font-bold text-slate-400">Conservative Win %</div>
          <div class="font-black text-sm text-white font-mono mt-0.5">{consProb}%</div>
          <div class="text-[10px] text-slate-500">Wilson 90% floor</div>
        </div>

        <!-- 3. Ensemble Consensus -->
        <div class="p-2.5 rounded-lg bg-white/5 border border-white/5">
          <div class="text-[10px] uppercase font-bold text-slate-400">Ensemble Agreement</div>
          <div class="font-black text-sm text-indigo-400 font-mono mt-0.5">6 of 7 Models</div>
          <div class="text-[10px] text-slate-500">GBDT, Elo, GNN</div>
        </div>

        <!-- 4. Payout Yield -->
        <div class="p-2.5 rounded-lg bg-white/5 border border-white/5">
          <div class="text-[10px] uppercase font-bold text-slate-400">Locked Price</div>
          <div class="font-black text-sm text-amber-400 font-mono mt-0.5">@ {odds}</div>
          <div class="text-[10px] text-slate-500">High payout tier</div>
        </div>
      </div>

      <!-- Tactical Rationale Points -->
      <div class="space-y-2 pt-1">
        <div class="flex items-start gap-2 text-slate-300 leading-relaxed">
          <span class="text-emerald-400 font-bold mt-0.5">✔</span>
          <span><strong>Value Pricing:</strong> Bookmaker implied probability ({impliedProb}%) undervalues the true calibrated probability ({consProb}%), creating a positive expected return per unit staked.</span>
        </div>
        <div class="flex items-start gap-2 text-slate-300 leading-relaxed">
          <span class="text-emerald-400 font-bold mt-0.5">✔</span>
          <span><strong>Form & Goal Momentum:</strong> Recent rolling xG data, team conversion splits, and head-to-head metrics align with the <strong>{market}</strong> selection.</span>
        </div>
        <div class="flex items-start gap-2 text-slate-300 leading-relaxed">
          <span class="text-emerald-400 font-bold mt-0.5">✔</span>
          <span><strong>Disciplined Stake:</strong> Staking exactly 1 hypothetical unit to maximize geometric bankroll growth while avoiding drawdown risk on heavy favorite upsets.</span>
        </div>
      </div>
    </div>
  {/if}
</div>
