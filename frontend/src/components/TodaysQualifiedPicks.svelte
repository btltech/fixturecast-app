<script>
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { API_URL } from "../config.js";

  let loading = true;
  let error = null;
  let data = null;

  onMount(async () => {
    try {
      const res = await fetch(`${API_URL}/api/recommendations/today`);
      if (res.ok) {
        data = await res.json();
      } else {
        error = "Failed to load today's recommendations.";
      }
    } catch (e) {
      console.error("Error loading today's qualified picks:", e);
      error = "Failed to load today's recommendations.";
    } finally {
      loading = false;
    }
  });
</script>

<div class="mb-12">
  <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mb-6">
    <div>
      <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mb-2">
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        Canonical Qualification Pipeline
      </div>
      <h2 class="text-2xl sm:text-3xl font-black text-white tracking-tight flex items-center gap-3">
        Today’s Qualified Picks
      </h2>
    </div>

    <Link
      to="/track-record"
      class="text-xs sm:text-sm font-bold text-emerald-400 hover:text-emerald-300 flex items-center gap-1.5 transition-colors group"
    >
      <span>Verified Forward Record</span>
      <span class="transition-transform group-hover:translate-x-1">→</span>
    </Link>
  </div>

  {#if loading}
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="glass-card p-6 rounded-2xl animate-pulse space-y-4">
        <div class="h-6 w-32 bg-white/10 rounded"></div>
        <div class="h-8 w-48 bg-white/10 rounded"></div>
        <div class="h-16 bg-white/5 rounded-xl"></div>
      </div>
      <div class="glass-card p-6 rounded-2xl animate-pulse space-y-4">
        <div class="h-6 w-32 bg-white/10 rounded"></div>
        <div class="h-8 w-48 bg-white/10 rounded"></div>
        <div class="h-16 bg-white/5 rounded-xl"></div>
      </div>
    </div>
  {:else if data}
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- 1. Qualified Single Card -->
      <div class="glass-card p-6 sm:p-7 rounded-2xl border border-white/10 bg-slate-900/60 flex flex-col justify-between relative overflow-hidden">
        <div class="absolute -right-10 -bottom-10 w-40 h-40 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none"></div>

        <div>
          <div class="flex items-center justify-between gap-2 mb-4">
            <div class="flex items-center gap-2">
              <span class="px-3 py-1 rounded-lg text-xs font-black uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Today's Daily Pick
              </span>
              {#if data.single?.has_pick && data.single?.match_phase}
                <span class="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider {data.single.match_phase === 'LIVE' ? 'bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse' : data.single.match_phase === 'SETTLED' ? 'bg-slate-700 text-slate-300' : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'}">
                  {data.single.match_phase}
                </span>
              {/if}
            </div>
            <span class="text-xs text-slate-400 font-mono">{data.date}</span>
          </div>

          {#if data.single?.has_pick}
            <div class="mb-4">
              <div class="text-xl sm:text-2xl font-black text-white mb-1">
                {data.single.match}
              </div>
              <div class="text-xs text-slate-400 font-medium">
                {data.single.league}
              </div>
            </div>

            <div class="p-4 rounded-xl bg-white/5 border border-white/10 mb-4 space-y-3">
              <div class="flex justify-between items-center">
                <span class="text-sm font-semibold text-slate-300">{data.single.selection}</span>
                <span class="font-mono font-black text-lg text-emerald-400">@ {data.single.odds}</span>
              </div>

              <div class="grid grid-cols-3 gap-2 pt-2 border-t border-white/10 text-center">
                <div>
                  <div class="text-[10px] text-slate-400 uppercase font-semibold">Conservative Prob</div>
                  <div class="font-mono font-bold text-xs text-white">{(data.single.conservative_probability * 100).toFixed(1)}%</div>
                </div>
                <div>
                  <div class="text-[10px] text-slate-400 uppercase font-semibold">Implied</div>
                  <div class="font-mono font-bold text-xs text-slate-300">{(data.single.implied_probability * 100).toFixed(1)}%</div>
                </div>
                <div>
                  <div class="text-[10px] text-slate-400 uppercase font-semibold">Conservative Edge</div>
                  <div class="font-mono font-black text-xs text-emerald-400">+{data.single.edge_pct}%</div>
                </div>
              </div>
            </div>

            <p class="text-xs text-slate-400 leading-relaxed mb-4">
              {data.single.rationale}
            </p>
          {:else}
            <!-- Explicit No-Pick State -->
            <div class="py-6 text-center space-y-3">
              <div class="w-12 h-12 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center mx-auto text-slate-400 text-lg font-bold">
                {data?.freeze_status === 'pending' ? '⏳' : '🛡️'}
              </div>
              <h4 class="text-base font-bold text-white">
                {data?.freeze_status === 'pending' ? 'Qualification Pending' : 'No Qualifying Single Today'}
              </h4>
              <p class="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
                {data.single?.reason || "No single selection cleared our conservative probability and edge qualification criteria."}
              </p>
            </div>
          {/if}
        </div>

        <div class="pt-4 border-t border-white/10 flex items-center justify-between">
          {#if data.single?.has_pick}
            <Link
              to={`/match/${data.single.fixture_id}`}
              class="text-xs font-bold text-emerald-400 hover:underline flex items-center gap-1"
            >
              <span>Match Analysis</span>
              <span>→</span>
            </Link>
          {:else}
            <span class="text-[11px] text-slate-500">Disciplined Value Selection</span>
          {/if}
          <Link
            to="/track-record"
            class="text-[11px] text-slate-400 hover:text-white transition-colors"
          >
            Ledger Audit Log
          </Link>
        </div>
      </div>

      <!-- 2. Qualified Acca Card -->
      <div class="glass-card p-6 sm:p-7 rounded-2xl border border-white/10 bg-slate-900/60 flex flex-col justify-between relative overflow-hidden">
        <div class="absolute -right-10 -bottom-10 w-40 h-40 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none"></div>

        <div>
          <div class="flex items-center justify-between gap-2 mb-4">
            <span class="px-3 py-1 rounded-lg text-xs font-black uppercase tracking-wider bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              Today's Qualified Acca
            </span>
            <span class="text-xs text-slate-400 font-mono">{data.date}</span>
          </div>

          {#if data.acca?.has_pick}
            <div class="mb-4 flex justify-between items-baseline">
              <div class="text-lg sm:text-xl font-black text-white">
                {data.acca.acca_type} ({data.acca.legs_count} Legs)
              </div>
              <div class="font-mono font-black text-lg text-emerald-400">
                Total Odds: {data.acca.total_odds}
              </div>
            </div>

            <div class="space-y-2 mb-4">
              {#each data.acca.legs as leg}
                <div class="p-2.5 rounded-xl bg-white/5 border border-white/10 text-xs flex items-center justify-between">
                  <div class="truncate mr-2">
                    <div class="font-bold text-white truncate">{leg.match}</div>
                    <div class="text-[11px] text-slate-400">{leg.selection}</div>
                  </div>
                  <div class="text-right shrink-0">
                    <div class="font-mono font-bold text-emerald-400">{leg.odds}</div>
                    {#if (leg.conservative_edge !== null && leg.conservative_edge !== undefined) || (leg.edge !== null && leg.edge !== undefined)}
                      <div class="text-[10px] font-mono text-slate-400">+{(((leg.conservative_edge !== null && leg.conservative_edge !== undefined) ? leg.conservative_edge : leg.edge) * 100).toFixed(1)}% edge</div>
                    {/if}
                  </div>
                </div>
              {/each}
            </div>
          {:else}
            <!-- Explicit No-Acca State -->
            <div class="py-6 text-center space-y-3">
              <div class="w-12 h-12 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center mx-auto text-slate-400 text-lg font-bold">
                🎲
              </div>
              <h4 class="text-base font-bold text-white">No Qualified Acca Today</h4>
              <p class="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
                {data.acca?.reason || "No accumulator today passed all canonical single-leg edge checks and strict 4-leg qualification constraints."}
              </p>
            </div>
          {/if}
        </div>

        <div class="pt-4 border-t border-white/10 flex items-center justify-between">
          <Link
            to="/accumulators"
            class="text-xs font-bold text-indigo-400 hover:underline flex items-center gap-1"
          >
            <span>Explore All Daily Accas</span>
            <span>→</span>
          </Link>
          <Link
            to="/track-record"
            class="text-[11px] text-slate-400 hover:text-white transition-colors"
          >
            Verified Forward Record
          </Link>
        </div>
      </div>
    </div>
  {/if}
</div>
