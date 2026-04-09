<script>
  // Prediction Accuracy Tracker Component
  // Shows real model accuracy when available, otherwise shows "tracking in progress"
  export let league = 39;
  export let modelAccuracy = null;
  export let compact = false;
  export let showAllLeagues = false; // New prop to show all leagues breakdown
  export let sortBy = "accuracy";
  export let minMatches = 5;

  import { onMount } from "svelte";
  import { _ } from "svelte-i18n";
  import { ML_API_URL } from "../config.js";
  import { getLeagueDisplay, getLeague } from "../services/leagues.js";

  let accuracyData = null;
  let hasRealData = false;
  let loading = true;

  function normalizeAccuracy(value) {
    if (value === null || value === undefined) return null;
    const num = Number(value);
    if (!Number.isFinite(num)) return null;
    if (num < 0) return null;
    if (num > 1) return num <= 100 ? num / 100 : null;
    return num;
  }

  // Transform API response to expected format
  function transformApiResponse(data) {
    const result = {
      overall: data?.overall?.accuracy ?? null,
      totalMatches: data?.overall?.total ?? 0,
      high_confidence: data?.by_confidence?.high?.accuracy ?? null,
      by_league: {}
    };

    // Transform league data
    if (data?.by_league) {
      for (const [leagueId, stats] of Object.entries(data.by_league)) {
        const display = getLeagueDisplay(leagueId);
        const league = getLeague(leagueId);

        // Build display name with country/region differentiator
        let displayName = stats.name || display.name || `League ${leagueId}`;

        // Add country/region for clarity if we have it
        if (league?.country) {
          // Add country for leagues that might be ambiguous
          displayName = `${displayName} (${league.country})`;
        }

        result.by_league[leagueId] = {
          name: displayName,
          accuracy: stats.accuracy ?? null,
          matches: stats.total || 0
        };
      }
    }

    return result;
  }

  onMount(async () => {
    try {
      // Try to fetch from feedback API
      const res = await fetch(`${ML_API_URL}/api/feedback/performance`);
      if (res.ok) {
        const data = await res.json();
        // Only use real data if we have meaningful predictions (at least 10)
        if (data?.overall?.total >= 10) {
          accuracyData = transformApiResponse(data);
          hasRealData = true;
        }
      }
    } catch (e) {
      // Silent fail - we'll show tracking message
    } finally {
      loading = false;
    }
  });

  $: leagueData = hasRealData ? accuracyData?.by_league?.[league] : null;
  $: overallAccuracy = hasRealData ? accuracyData?.overall : null;
  $: highConfAccuracy = hasRealData ? accuracyData?.high_confidence : null;
  $: totalMatches = hasRealData ? accuracyData?.totalMatches : 0;

  $: propOverallAccuracy = normalizeAccuracy(modelAccuracy);
  $: effectiveHasAccuracy = hasRealData || propOverallAccuracy !== null;
  $: effectiveOverallAccuracy = propOverallAccuracy !== null ? propOverallAccuracy : overallAccuracy;

  // Get all leagues sorted by match count
  $: allLeagues = hasRealData && accuracyData?.by_league
    ? Object.entries(accuracyData.by_league)
        .filter(([_, data]) => data.matches >= minMatches)
        .sort((a, b) => {
          if (sortBy === "matches") {
            return b[1].matches - a[1].matches;
          }
          if (sortBy === "name") {
            return a[1].name.localeCompare(b[1].name);
          }
          return (b[1].accuracy ?? 0) - (a[1].accuracy ?? 0);
        })
    : [];

  function getAccuracyColor(acc) {
    if (acc === null) return "text-slate-400";
    if (acc >= 0.75) return "text-emerald-400";
    if (acc >= 0.65) return "text-blue-400";
    if (acc >= 0.55) return "text-amber-400";
    return "text-red-400";
  }

  function getAccuracyBg(acc) {
    if (acc === null) return "bg-slate-500";
    if (acc >= 0.75) return "bg-emerald-500";
    if (acc >= 0.65) return "bg-blue-500";
    if (acc >= 0.55) return "bg-amber-500";
    return "bg-red-500";
  }
</script>

{#if loading}
  <div class="skeleton-shimmer {compact ? 'h-4' : 'h-16'} bg-white/5 rounded-lg"></div>
{:else if compact}
  <!-- Compact inline version -->
  {#if effectiveHasAccuracy && effectiveOverallAccuracy !== null}
    <div class="inline-flex items-center gap-2 text-xs">
      <span class="text-slate-400">{$_("modelStats.modelAccuracy")}</span>
      <span class="font-bold {getAccuracyColor(effectiveOverallAccuracy)}">
        {(effectiveOverallAccuracy * 100).toFixed(0)}%
      </span>
      {#if leagueData && leagueData.accuracy !== null}
        <span class="text-slate-500">•</span>
        <span class="text-slate-400">{leagueData.name}:</span>
        <span class="font-bold {getAccuracyColor(leagueData.accuracy)}">
          {(leagueData.accuracy * 100).toFixed(0)}%
        </span>
      {/if}
    </div>
  {:else}
    <div class="inline-flex items-center gap-2 text-xs text-slate-400">
      <span>📊</span>
      <span>{$_("modelStats.performanceTracking")}</span>
    </div>
  {/if}
{:else}
  <!-- Full card version -->
  <div class="glass-card p-4 element-enter">
    <div class="flex items-center gap-2 mb-3">
      <span class="text-lg">📈</span>
      <h4 class="font-bold text-sm">{$_("modelStats.modelPerformance")}</h4>
    </div>

    {#if effectiveHasAccuracy && effectiveOverallAccuracy !== null}
      <!-- Real data available -->
      <div class="grid grid-cols-2 gap-3">
        <!-- Overall Accuracy -->
        <div class="bg-white/5 rounded-lg p-3">
          <div class="text-xs text-slate-400 mb-1">{$_("modelStats.overallAccuracy")}</div>
          <div class="flex items-end gap-1">
            <span class="text-2xl font-bold {getAccuracyColor(effectiveOverallAccuracy)}">
              {(effectiveOverallAccuracy * 100).toFixed(0)}%
            </span>
          </div>
          <div class="mt-2 h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div
              class="h-full rounded-full bar-fill {getAccuracyBg(effectiveOverallAccuracy)}"
              style="width: {effectiveOverallAccuracy * 100}%"
            ></div>
          </div>
        </div>

        <!-- High Confidence -->
        <div class="bg-white/5 rounded-lg p-3">
          <div class="text-xs text-slate-400 mb-1">{$_("modelStats.highConfidence")}</div>
          {#if highConfAccuracy !== null}
            <div class="flex items-end gap-1">
              <span class="text-2xl font-bold {getAccuracyColor(highConfAccuracy)}">
                {(highConfAccuracy * 100).toFixed(0)}%
              </span>
            </div>
            <div class="mt-2 h-1.5 bg-white/10 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full bar-fill {getAccuracyBg(highConfAccuracy)}"
                style="width: {highConfAccuracy * 100}%"
              ></div>
            </div>
          {:else}
            <div class="text-sm text-slate-500">{$_("modelStats.pending")}</div>
          {/if}
        </div>
      </div>

      {#if leagueData && leagueData.accuracy !== null}
        <div class="mt-3 pt-3 border-t border-white/10">
          <div class="flex items-center justify-between">
            <span class="text-xs text-slate-400">{leagueData.name} {$_("modelStats.accuracySuffix")}</span>
            <span class="text-sm font-bold {getAccuracyColor(leagueData.accuracy)}">
              {(leagueData.accuracy * 100).toFixed(0)}%
            </span>
          </div>
          <div class="text-xs text-slate-500 mt-1">
            {$_("modelStats.basedOnMatches", { values: { count: leagueData.matches } })}
          </div>
        </div>
      {/if}

      <!-- All Leagues Breakdown -->
      {#if showAllLeagues && allLeagues.length > 0}
        <div class="mt-4 pt-3 border-t border-white/10">
          <div class="flex items-center gap-2 mb-3">
            <span class="text-sm">🏆</span>
            <h5 class="text-xs font-semibold text-slate-300">Accuracy by League</h5>
          </div>
          <div class="space-y-2 max-h-64 overflow-y-auto pr-1">
            {#each allLeagues as [leagueId, data]}
              <div class="flex items-center justify-between bg-white/5 rounded-lg px-3 py-2">
                <div class="flex-1 min-w-0">
                  <div class="text-xs font-medium text-white truncate">{data.name}</div>
                  <div class="text-[10px] text-slate-500">{$_("modelStats.matchCountShort", { values: { count: data.matches } })}</div>
                </div>
                <div class="flex items-center gap-2 ml-2">
                  <div class="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
                    <div
                      class="h-full rounded-full {getAccuracyBg(data.accuracy)}"
                      style="width: {(data.accuracy || 0) * 100}%"
                    ></div>
                  </div>
                  <span class="text-sm font-bold {getAccuracyColor(data.accuracy)} min-w-[40px] text-right">
                    {data.accuracy !== null ? `${(data.accuracy * 100).toFixed(0)}%` : '-'}
                  </span>
                </div>
              </div>
            {/each}
          </div>
        </div>
      {/if}

      <div class="mt-3 text-xs text-slate-500 text-center">
        {$_("modelStats.basedOnPredictions", { values: { count: totalMatches } })}
      </div>
    {:else}
      <!-- No real data yet - show tracking message -->
      <div class="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4 text-center">
        <div class="text-amber-400 text-sm font-medium mb-1">
          📊 Performance Tracking In Progress
        </div>
        <div class="text-xs text-slate-400">
          {$_("modelStats.trackingDesc")}
        </div>
      </div>
      <div class="mt-3 text-xs text-slate-500 text-center">
        {$_("modelStats.backtestsAuto")}
      </div>
    {/if}
  </div>
{/if}
