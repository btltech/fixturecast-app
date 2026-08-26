<script>
  import { onMount } from "svelte";
  import SEOHead from "../components/SEOHead.svelte";
  import BankrollChart from "../components/BankrollChart.svelte";
  import { BACKEND_API_URL } from "../config.js";

  let recordData = null;
  let loading = true;
  let error = null;
  let activeTab = "singles"; // "singles" | "accas"
  let filterResult = "all"; // "all" | "won" | "lost"

  const seoData = {
    title: "Verified Public Track Record | FixtureCast",
    description: "100% transparent, forward-recorded performance for FixtureCast qualified singles and accumulators. No backfill, all losses included.",
    keywords: "football betting track record, verified prediction record, accumulator history, value betting ROI",
    canonical: "https://fixturecast.com/track-record",
  };

  onMount(async () => {
    try {
      loading = true;
      const res = await fetch(`${BACKEND_API_URL}/api/records/track-record`, {
        cache: "no-store",
      });
      if (!res.ok) {
        throw new Error(`Failed to load track record (${res.status})`);
      }
      recordData = await res.json();
    } catch (err) {
      console.error("Track record fetch error:", err);
      error = err.message || "Failed to load track record";
    } finally {
      loading = false;
    }
  });

  $: currentList = activeTab === "singles" 
    ? (recordData?.singles?.history || []) 
    : (recordData?.accas?.history || []);

  $: filteredList = currentList.filter(item => {
    if (filterResult === "won") return item.won;
    if (filterResult === "lost") return !item.won;
    return true;
  });

  $: currentSummary = activeTab === "singles"
    ? recordData?.singles?.summary
    : recordData?.accas?.summary;
</script>

<SEOHead
  title={seoData.title}
  description={seoData.description}
  keywords={seoData.keywords}
  canonical={seoData.canonical}
/>

<div class="max-w-6xl mx-auto px-4 py-8">
  <!-- Page Header -->
  <div class="text-center mb-8">
    <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 mb-4">
      <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
      Strictly Forward-Recorded
    </div>
    <h1 class="text-3xl md:text-5xl font-black text-slate-900 dark:text-white tracking-tight mb-3">
      Verified Public Track Record
    </h1>
    <p class="text-base md:text-lg text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">
      Every selection recorded and time-stamped strictly before match kickoff. 100% transparent with zero historical backfilling.
    </p>
  </div>

  <!-- Trust Badges & Principles Banner -->
  <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
    <div class="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 flex items-start gap-3">
      <div class="p-2 rounded-lg bg-indigo-500/10 text-indigo-500 dark:text-indigo-400 shrink-0">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      </div>
      <div>
        <h4 class="text-sm font-bold text-slate-900 dark:text-white">Record Started 20 Aug 2026</h4>
        <p class="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
          Recorded live in production from day one. No simulated past history.
        </p>
      </div>
    </div>

    <div class="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 flex items-start gap-3">
      <div class="p-2 rounded-lg bg-emerald-500/10 text-emerald-500 dark:text-emerald-400 shrink-0">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      </div>
      <div>
        <h4 class="text-sm font-bold text-slate-900 dark:text-white">No Historical Backfill</h4>
        <p class="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
          Only picks that met canonical pre-kickoff qualification rules are published.
        </p>
      </div>
    </div>

    <div class="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 flex items-start gap-3">
      <div class="p-2 rounded-lg bg-amber-500/10 text-amber-500 dark:text-amber-400 shrink-0">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>
      <div>
        <h4 class="text-sm font-bold text-slate-900 dark:text-white">Full Transparency</h4>
        <p class="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
          Every single loss is published. Past performance does not guarantee future results.
        </p>
      </div>
    </div>
  </div>

  {#if loading}
    <div class="flex flex-col items-center justify-center py-20">
      <div class="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mb-4"></div>
      <p class="text-slate-500 dark:text-slate-400">Loading verified forward record...</p>
    </div>
  {:else if error}
    <div class="p-6 rounded-2xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800 text-center my-8">
      <p class="text-rose-600 dark:text-rose-400 font-semibold mb-2">{error}</p>
      <button 
        on:click={() => location.reload()}
        class="px-4 py-2 bg-rose-600 text-white rounded-lg text-sm font-medium hover:bg-rose-700 transition"
      >
        Retry
      </button>
    </div>
  {:else if recordData}
    <!-- Summary Metrics Cards -->
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 md:gap-4 mb-8">
      <div class="p-4 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700/60 shadow-sm">
        <span class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">Total Bets</span>
        <div class="text-2xl font-black text-slate-900 dark:text-white">{currentSummary?.total_bets || 0}</div>
        <div class="text-xs text-slate-500 mt-1">{currentSummary?.won || 0}W - {currentSummary?.lost || 0}L</div>
      </div>

      <div class="p-4 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700/60 shadow-sm">
        <span class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">Win Rate</span>
        <div class="text-2xl font-black text-slate-900 dark:text-white">{currentSummary?.win_rate_pct || 0}%</div>
        <div class="text-xs text-slate-500 mt-1">Settled picks</div>
      </div>

      <div class="p-4 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700/60 shadow-sm">
        <span class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">Total Staked</span>
        <div class="text-2xl font-black text-slate-900 dark:text-white">{currentSummary?.staked_units || 0}u</div>
        <div class="text-xs text-slate-500 mt-1">1 unit flat stake</div>
      </div>

      <div class="p-4 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700/60 shadow-sm">
        <span class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">Net Profit</span>
        <div class="text-2xl font-black {(currentSummary?.profit_units || 0) >= 0 ? 'text-emerald-500' : 'text-rose-500'}">
          {(currentSummary?.profit_units || 0) >= 0 ? '+' : ''}{currentSummary?.profit_units || 0}u
        </div>
        <div class="text-xs text-slate-500 mt-1">Cumulative P&L</div>
      </div>

      <div class="p-4 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700/60 shadow-sm">
        <span class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">Yield / ROI</span>
        <div class="text-2xl font-black {(currentSummary?.roi_pct || 0) >= 0 ? 'text-emerald-500' : 'text-rose-500'}">
          {(currentSummary?.roi_pct || 0) >= 0 ? '+' : ''}{currentSummary?.roi_pct || 0}%
        </div>
        <div class="text-xs text-slate-500 mt-1">On staked capital</div>
      </div>

      <div class="p-4 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700/60 shadow-sm">
        <span class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">Avg Odds</span>
        <div class="text-2xl font-black text-slate-900 dark:text-white">{currentSummary?.avg_odds || 0}</div>
        <div class="text-xs text-slate-500 mt-1">Max Loss Streak: {currentSummary?.longest_losing_streak || 0}</div>
      </div>
    </div>

    <!-- Visual Bankroll Equity Curve Chart -->
    <BankrollChart
      history={currentList}
      startingBank={100}
      label={activeTab === "singles" ? "Singles Bankroll (100u)" : "Accas Bankroll (100u)"}
    />

    <!-- Tab & Filter Bar -->
    <div class="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-4 mb-6">
      <div class="inline-flex rounded-xl bg-slate-100 dark:bg-slate-800 p-1 border border-slate-200 dark:border-slate-700/60">
        <button
          on:click={() => activeTab = "singles"}
          class="px-5 py-2 rounded-lg text-sm font-bold transition-all {activeTab === 'singles' ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'}"
        >
          Qualified Singles ({recordData?.singles?.summary?.total_bets || 0})
        </button>
        <button
          on:click={() => activeTab = "accas"}
          class="px-5 py-2 rounded-lg text-sm font-bold transition-all {activeTab === 'accas' ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'}"
        >
          Qualified Accas ({recordData?.accas?.summary?.total_bets || 0})
        </button>
      </div>

      <div class="flex items-center gap-2">
        <span class="text-xs font-semibold text-slate-500">Filter:</span>
        <div class="inline-flex rounded-lg bg-slate-100 dark:bg-slate-800 p-1 border border-slate-200 dark:border-slate-700/60 text-xs">
          <button
            on:click={() => filterResult = "all"}
            class="px-3 py-1 rounded font-medium transition {filterResult === 'all' ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white font-bold shadow-xs' : 'text-slate-600 dark:text-slate-400'}"
          >
            All
          </button>
          <button
            on:click={() => filterResult = "won"}
            class="px-3 py-1 rounded font-medium transition {filterResult === 'won' ? 'bg-white dark:bg-slate-700 text-emerald-600 dark:text-emerald-400 font-bold shadow-xs' : 'text-slate-600 dark:text-slate-400'}"
          >
            Won
          </button>
          <button
            on:click={() => filterResult = "lost"}
            class="px-3 py-1 rounded font-medium transition {filterResult === 'lost' ? 'bg-white dark:bg-slate-700 text-rose-600 dark:text-rose-400 font-bold shadow-xs' : 'text-slate-600 dark:text-slate-400'}"
          >
            Lost
          </button>
        </div>
      </div>
    </div>

    <!-- History Table -->
    {#if filteredList.length === 0}
      <div class="p-12 text-center rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/60">
        <p class="text-base font-semibold text-slate-700 dark:text-slate-300">No settled records match this filter yet.</p>
        <p class="text-xs text-slate-500 mt-1">As upcoming matches kick off and settle, results are time-stamped and recorded automatically.</p>
      </div>
    {:else}
      {#if activeTab === "singles"}
        <!-- Singles Table -->
        <div class="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-700/60 bg-white dark:bg-slate-800 shadow-sm">
          <table class="w-full text-left border-collapse text-sm">
            <thead>
              <tr class="border-b border-slate-200 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/50 text-xs font-bold text-slate-500 uppercase tracking-wider">
                <th class="py-3.5 px-4">Date</th>
                <th class="py-3.5 px-4">Match & League</th>
                <th class="py-3.5 px-4">Selection</th>
                <th class="py-3.5 px-3 text-right">Odds</th>
                <th class="py-3.5 px-3 text-right">Conservative Prob</th>
                <th class="py-3.5 px-3 text-right">Implied</th>
                <th class="py-3.5 px-3 text-right">Edge</th>
                <th class="py-3.5 px-4 text-center">Result</th>
                <th class="py-3.5 px-3 text-right">Unit P&L</th>
                <th class="py-3.5 px-4 text-right">Running Units</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 dark:divide-slate-700/40 font-medium">
              {#each filteredList as item}
                <tr class="hover:bg-slate-50/80 dark:hover:bg-slate-700/30 transition-colors">
                  <td class="py-3 px-4 text-xs text-slate-500 whitespace-nowrap">{item.date}</td>
                  <td class="py-3 px-4">
                    <div class="font-bold text-slate-900 dark:text-white">{item.match}</div>
                    <div class="text-xs text-slate-500">{item.league}</div>
                  </td>
                  <td class="py-3 px-4">
                    <div class="font-semibold text-slate-800 dark:text-slate-200">{item.selection}</div>
                    <div class="text-xs text-slate-400">{item.market}</div>
                  </td>
                  <td class="py-3 px-3 text-right font-mono font-bold text-slate-900 dark:text-white">{item.odds}</td>
                  <td class="py-3 px-3 text-right font-mono text-slate-600 dark:text-slate-300">{(item.conservative_probability * 100).toFixed(1)}%</td>
                  <td class="py-3 px-3 text-right font-mono text-slate-500">{(item.implied_probability * 100).toFixed(1)}%</td>
                  <td class="py-3 px-3 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">+{(item.edge * 100).toFixed(1)}%</td>
                  <td class="py-3 px-4 text-center whitespace-nowrap">
                    <span class="inline-block px-2.5 py-0.5 rounded-full text-xs font-extrabold {item.won ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20'}">
                      {item.result}
                    </span>
                  </td>
                  <td class="py-3 px-3 text-right font-mono font-bold {item.unit_pnl >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-500'}">
                    {item.unit_pnl >= 0 ? '+' : ''}{item.unit_pnl}u
                  </td>
                  <td class="py-3 px-4 text-right font-mono font-bold {item.running_units >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-500'}">
                    {item.running_units >= 0 ? '+' : ''}{item.running_units}u
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else}
        <!-- Accas Table / Cards -->
        <div class="space-y-4">
          {#each filteredList as acca}
            <div class="p-5 rounded-2xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700/60 shadow-sm">
              <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-4 border-b border-slate-100 dark:border-slate-700/40">
                <div>
                  <div class="flex items-center gap-2">
                    <span class="px-2.5 py-0.5 rounded-md text-xs font-black uppercase bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
                      {acca.acca_type}
                    </span>
                    <span class="text-xs text-slate-500">{acca.date}</span>
                    <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400">
                      {acca.qualifier_version || 'v1.0-wilson-market'}
                    </span>
                  </div>
                  <div class="text-lg font-black text-slate-900 dark:text-white mt-1">
                    Combined Odds: <span class="font-mono text-emerald-600 dark:text-emerald-400">{acca.total_odds}</span> ({acca.legs_count} Legs)
                  </div>
                </div>

                <div class="flex items-center gap-3">
                  <span class="px-3 py-1 rounded-full text-xs font-black {acca.won ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20'}">
                    {acca.result}
                  </span>
                  <div class="text-right">
                    <div class="text-sm font-bold {acca.unit_pnl >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-500'}">
                      {acca.unit_pnl >= 0 ? '+' : ''}{acca.unit_pnl}u
                    </div>
                    <div class="text-xs text-slate-400 font-mono">Running: {acca.running_units >= 0 ? '+' : ''}{acca.running_units}u</div>
                  </div>
                </div>
              </div>

              <!-- Legs Breakdown with Full Qualification Evidence -->
              <div class="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
                {#each acca.legs as leg}
                  <div class="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/40 text-xs flex flex-col justify-between">
                    <div>
                      <div class="font-bold text-slate-900 dark:text-white truncate">{leg.match}</div>
                      <div class="text-slate-500 text-[11px] truncate mb-2">{leg.league}</div>
                      <div class="font-semibold text-slate-800 dark:text-slate-200 mb-2">{leg.selection}</div>
                    </div>

                    <div class="pt-2 border-t border-slate-200/60 dark:border-slate-700/40 space-y-1">
                      <div class="flex justify-between items-center text-[11px]">
                        <span class="text-slate-500">Odds:</span>
                        <span class="font-mono font-bold {leg.won ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-500'}">
                          {leg.odds} {leg.won ? '✓' : '✗'}
                        </span>
                      </div>
                      {#if leg.conservative_probability !== null && leg.conservative_probability !== undefined}
                        <div class="flex justify-between items-center text-[11px]">
                          <span class="text-slate-500">Cons. Prob:</span>
                          <span class="font-mono text-slate-700 dark:text-slate-300">{(leg.conservative_probability * 100).toFixed(1)}%</span>
                        </div>
                      {/if}
                      {#if leg.edge !== null && leg.edge !== undefined}
                        <div class="flex justify-between items-center text-[11px]">
                          <span class="text-slate-500">Edge:</span>
                          <span class="font-mono font-bold text-emerald-600 dark:text-emerald-400">+{(leg.edge * 100).toFixed(1)}%</span>
                        </div>
                      {/if}
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/each}
        </div>
      {/if}
    {/if}
  {/if}
</div>
