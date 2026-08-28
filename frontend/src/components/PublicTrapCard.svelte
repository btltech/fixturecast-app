<script>
  export let trap = null;

  // Real fields without fake fallbacks
  $: isValidTrap = Boolean(
    trap &&
    trap.match &&
    trap.has_verified_volume_source === true &&
    typeof trap.crowd_sentiment_pct === "number" &&
    typeof trap.ai_probability_pct === "number" &&
    typeof trap.negative_ev === "number"
  );
</script>

{#if isValidTrap}
  <div class="glass-card p-5 sm:p-6 rounded-2xl border border-rose-500/30 bg-gradient-to-br from-slate-900 via-slate-950 to-rose-950/20 shadow-2xl relative overflow-hidden my-6">
    <!-- Glowing Danger Ambience -->
    <div class="absolute -right-8 -top-8 w-40 h-40 bg-rose-500/10 rounded-full blur-3xl pointer-events-none"></div>

    <div class="flex flex-wrap items-center justify-between gap-3 mb-3">
      <div class="flex items-center gap-2">
        <span class="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-rose-500/20 text-rose-400 border border-rose-500/30 animate-pulse">
          🚨 Public Trap Warning
        </span>
        <span class="text-xs text-slate-400 font-mono">Market Distortion</span>
      </div>
      <span class="text-xs font-bold text-rose-400 font-mono">{trap.negative_ev}% Negative EV</span>
    </div>

    <h3 class="text-lg sm:text-xl font-black text-white mb-2">
      {trap.match}
    </h3>

    <p class="text-xs text-slate-300 leading-relaxed mb-4">
      {trap.warning || "Casual public volume is heavily skewed on this favorite, but quantitative models detect significant upset vulnerability with negative expected value."}
    </p>

    <!-- Discrepancy Comparison Meter -->
    <div class="grid grid-cols-2 gap-3 p-3.5 rounded-xl bg-slate-950/60 border border-white/5">
      <div>
        <div class="text-[10px] uppercase font-bold text-slate-400">Casual Crowd Sentiment</div>
        <div class="font-black text-base text-rose-400 font-mono mt-0.5">{trap.crowd_sentiment_pct}% Backing {trap.public_favored || "Favorite"}</div>
        <div class="w-full bg-white/10 rounded-full h-1.5 mt-1.5 overflow-hidden">
          <div class="bg-rose-500 h-full rounded-full" style="width: {trap.crowd_sentiment_pct}%"></div>
        </div>
      </div>

      <div>
        <div class="text-[10px] uppercase font-bold text-slate-400">AI Calibrated Win Probability</div>
        <div class="font-black text-base text-emerald-400 font-mono mt-0.5">{trap.ai_probability_pct}% Realistic Floor</div>
        <div class="w-full bg-white/10 rounded-full h-1.5 mt-1.5 overflow-hidden">
          <div class="bg-emerald-500 h-full rounded-full" style="width: {trap.ai_probability_pct}%"></div>
        </div>
      </div>
    </div>
  </div>
{/if}
