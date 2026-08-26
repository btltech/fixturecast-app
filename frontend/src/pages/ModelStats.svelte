<script>
  import SEOHead from "../components/SEOHead.svelte";
  import { generateModelStatsSEO } from "../services/seoService.js";
  let seoData;
  import { onMount } from "svelte";
  import { _ } from 'svelte-i18n';
  import { locale } from "../lib/i18n";
  $: seoData = generateModelStatsSEO($locale);
  import { ML_API_URL, BACKEND_API_URL } from "../config.js";
  import AccuracyTracker from "../components/AccuracyTracker.svelte";

  let stats = null;
  let backtestHistory = null;
  let timeBacktestReport = null;
  let marketMetrics = null;  // 3-market accuracy data
  let calibration = null;    // Brier / log-loss / ECE / reliability bins
  let marketEdge = null;     // model vs de-vigged bookmaker odds
  let loading = true;
  let error = null;
  let apiAvailable = false;
  let leagueSortBy = "accuracy";
  let leagueMinMatches = 5;

  const dedupeBacktestHistoryByDate = (items) => {
    if (!Array.isArray(items) || items.length === 0) return [];
    const seenDates = new Set();
    const dedupedReversed = [];
    for (let i = items.length - 1; i >= 0; i -= 1) {
      const item = items[i];
      const rawDate = typeof item?.date === "string" ? item.date : "";
      const normalizedDate = rawDate ? rawDate.slice(0, 10) : "";
      if (!normalizedDate) {
        dedupedReversed.push(item);
        continue;
      }
      if (!seenDates.has(normalizedDate)) {
        seenDates.add(normalizedDate);
        dedupedReversed.push(item);
      }
    }
    return dedupedReversed.reverse();
  };

  $: dedupedBacktestHistory = dedupeBacktestHistoryByDate(backtestHistory?.history);

  // These six endpoints are completely independent of one another, but were
  // being awaited one after the next - so the page took the SUM of six round
  // trips rather than the slowest one. On a phone against a cold backend that
  // is the difference between a moment and quite a few seconds.
  //
  // allSettled rather than all: one endpoint being unavailable should blank out
  // its own card, not abort the whole page.
  // "home_win" is fine in a JSON payload but not in a table a reader is meant
  // to scan quickly.
  const OUTCOME_LABELS = {
    home_win: "Home",
    draw: "Draw",
    away_win: "Away",
  };
  const outcomeLabel = (o) => OUTCOME_LABELS[o] || o || "—";

  async function getJson(url, options) {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error(`${res.status} ${url}`);
    return res.json();
  }

  onMount(async () => {
    const noStore = { cache: "no-store" };
    const [
      statsRes,
      historyRes,
      metricsRes,
      reportRes,
      calibRes,
      edgeRes,
    ] = await Promise.allSettled([
      getJson(`${ML_API_URL}/api/model-stats?public=1&ts=${Date.now()}`, noStore),
      getJson(`${BACKEND_API_URL}/api/metrics/backtest-history`),
      getJson(`${ML_API_URL}/api/metrics/summary`),
      getJson(`${ML_API_URL}/api/backtest/report`),
      getJson(`${ML_API_URL}/api/metrics/calibration-report?days=90&ts=${Date.now()}`, noStore),
      // Model vs bookmaker. Accuracy alone cannot separate a predictive model
      // from one that merely agrees with the favourite, so this is the number
      // that actually justifies the site existing.
      getJson(`${ML_API_URL}/api/metrics/market-edge?ts=${Date.now()}`, noStore),
    ]);

    if (statsRes.status === "fulfilled") {
      stats = statsRes.value;
      apiAvailable = true;
    } else {
      apiAvailable = false;
    }
    if (historyRes.status === "fulfilled") backtestHistory = historyRes.value;
    if (metricsRes.status === "fulfilled") marketMetrics = metricsRes.value;
    if (reportRes.status === "fulfilled") timeBacktestReport = reportRes.value;
    if (calibRes.status === "fulfilled" && calibRes.value?.available) {
      calibration = calibRes.value;
    }
    if (edgeRes.status === "fulfilled") marketEdge = edgeRes.value;

    loading = false;
  });
</script>

<SEOHead data={seoData} />

<div class="space-y-6">
  <div class="glass-card p-6">
    <h1 class="text-2xl md:text-3xl font-bold mb-2">{$_('modelStats.title')}</h1>
    <p class="text-slate-400 text-sm md:text-base">
      {$_('modelStats.subtitle')}
    </p>
    {#if !apiAvailable || !stats}
      <p class="text-xs text-slate-500 mt-2">
        📊 {$_('modelStats.availableAfterVerification')}
      </p>
    {/if}
  </div>

  {#if loading}
    <div class="glass-card p-12 text-center">
      <div
        class="inline-block w-12 h-12 border-4 border-accent border-t-transparent rounded-full animate-spin"
      ></div>
      <p class="mt-4 text-slate-400">{$_('common.loading')}</p>
    </div>
  {:else}
    <!--
      Model vs bookmaker. Deliberately the first thing on the page: a raw
      accuracy figure cannot tell a predictive model apart from one that just
      agrees with the favourite, so this is the only section that speaks to
      whether the predictions are worth anything. It is shown even while the
      dataset is still building, because "we are still measuring" is a more
      honest headline than a number with nothing to compare it to.
    -->
    {#if marketEdge}
      <div class="glass-card p-6 border border-amber-500/30">
        <h2 class="text-xl font-bold text-amber-400 mb-1">
          Do we beat the bookmakers?
        </h2>
        <p class="text-slate-400 text-sm mb-4">
          Being right often is easy — always backing the favourite gets you into the
          mid-50s. The real test is whether our probabilities are better calibrated
          than the bookmakers' own, with their margin stripped out.
        </p>

        {#if marketEdge.status === 'ready'}
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <div class="text-xs text-slate-400 uppercase tracking-wide">Matches scored</div>
              <div class="text-2xl font-bold">{marketEdge.matches}</div>
            </div>
            <div>
              <div class="text-xs text-slate-400 uppercase tracking-wide">Our Brier</div>
              <div class="text-2xl font-bold">{marketEdge.model_brier}</div>
            </div>
            <div>
              <div class="text-xs text-slate-400 uppercase tracking-wide">Market Brier</div>
              <div class="text-2xl font-bold">{marketEdge.market_brier}</div>
            </div>
            <div>
              <div class="text-xs text-slate-400 uppercase tracking-wide">Our accuracy vs market</div>
              <div class="text-2xl font-bold">
                {marketEdge.model_accuracy}% <span class="text-slate-500 text-base">vs {marketEdge.market_accuracy}%</span>
              </div>
            </div>
          </div>

          <div
            class="rounded-lg p-4 text-sm {marketEdge.statistically_significant && marketEdge.mean_brier_diff < 0
              ? 'bg-green-500/10 text-green-300'
              : 'bg-slate-500/10 text-slate-300'}"
          >
            <strong>{marketEdge.verdict}</strong>
            <p class="text-xs text-slate-400 mt-2">
              Lower Brier is better. We only claim an edge when the gap is large enough
              to be unlikely to be chance — currently t = {marketEdge.t_stat}, and we
              require |t| ≥ 1.96. Published whichever way it falls.
            </p>
          </div>

          <!--
            The auditable part. A summary asks you to take our word for it; this
            lets anyone check the individual matches - our probability, the
            bookmaker's price, and what actually happened. Collapsed by default
            so the summary stays readable, and it renders the losses exactly as
            plainly as the wins.
          -->
          {#if marketEdge.matches_detail?.length}
            <details class="mt-4 group">
              <summary
                class="cursor-pointer select-none text-sm text-cyan-400 hover:text-cyan-300 py-2"
              >
                Check the individual matches ({marketEdge.matches_detail.length})
              </summary>

              <p class="text-xs text-slate-500 mt-1 mb-3">
                Every match scored, newest first. "Ours" and "Book" are the outcome each
                gave the highest chance to, recorded before kickoff.
                {#if marketEdge.matches_detail_truncated}
                  Showing the most recent {marketEdge.matches_detail.length}.
                {/if}
              </p>

              <div class="overflow-x-auto -mx-2 px-2">
                <table class="w-full text-xs min-w-[520px]">
                  <thead class="text-slate-400 border-b border-white/10">
                    <tr>
                      <th class="text-left py-2 pr-2 font-medium">Match</th>
                      <th class="text-left py-2 px-2 font-medium">Result</th>
                      <th class="text-left py-2 px-2 font-medium">Ours</th>
                      <th class="text-left py-2 px-2 font-medium">Book</th>
                      <th class="text-right py-2 pl-2 font-medium">Closer</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each marketEdge.matches_detail as m}
                      <tr class="border-b border-white/5">
                        <td class="py-2 pr-2">
                          <span class="text-slate-200">{m.home} v {m.away}</span>
                          {#if m.kickoff}
                            <span class="block text-slate-500"
                              >{new Date(m.kickoff).toLocaleDateString()}</span
                            >
                          {/if}
                        </td>
                        <td class="py-2 px-2 text-slate-300">{outcomeLabel(m.outcome)}</td>
                        <td class="py-2 px-2 {m.model_correct ? 'text-green-400' : 'text-slate-500'}">
                          {outcomeLabel(m.model_pick)}
                        </td>
                        <td class="py-2 px-2 {m.market_correct ? 'text-green-400' : 'text-slate-500'}">
                          {outcomeLabel(m.market_pick)}
                        </td>
                        <td
                          class="py-2 pl-2 text-right {m.brier_diff < 0
                            ? 'text-green-400'
                            : 'text-amber-400'}"
                        >
                          {m.brier_diff < 0 ? "us" : "book"}
                        </td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            </details>
          {/if}
        {:else}
          <div class="rounded-lg p-4 bg-slate-500/10 text-slate-300 text-sm">
            <strong>Still collecting — no claim yet.</strong>
            <p class="text-xs text-slate-400 mt-2">
              {marketEdge.matches || 0} matches scored so far.
              {#if marketEdge.matches_needed}
                About {marketEdge.matches_needed} more needed before the comparison
                means anything.
              {/if}
              Bookmakers withdraw their prices once a match kicks off, so this can
              only be built forward from live data — it cannot be backfilled.
            </p>
          </div>
        {/if}
      </div>
    {/if}

    <!-- Calibration & scoring (honest proper-scoring-rule metrics) -->
    {#if calibration && calibration.one_x_two}
      {@const oxt = calibration.one_x_two}
      {@const rel = oxt.reliability || { bins: [], ece: 0 }}
      <div class="glass-card p-6 border border-cyan-500/30">
        <h2 class="text-xl font-bold text-cyan-400 mb-1">
          {$_('modelStats.calibrationTitle') || 'Calibration & Scoring'}
        </h2>
        <p class="text-slate-400 text-sm mb-4">
          Last {calibration.window_days} days · {oxt.n} settled matches{calibration.excluded_low_confidence ? ' · low-confidence picks excluded' : ''}.
          Lower Brier / log-loss is better; ECE near 0 means the probabilities are honest.
        </p>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div class="bg-slate-800/50 rounded-lg p-4">
            <div class="text-xs text-slate-400 uppercase tracking-wide">Brier</div>
            <div class="text-2xl font-bold">{oxt.brier.toFixed(3)}</div>
            <div class="text-xs text-slate-500">vs {oxt.brier_baseline_uniform.toFixed(3)} random</div>
          </div>
          <div class="bg-slate-800/50 rounded-lg p-4">
            <div class="text-xs text-slate-400 uppercase tracking-wide">Log loss</div>
            <div class="text-2xl font-bold">{oxt.log_loss.toFixed(3)}</div>
            <div class="text-xs text-slate-500">vs {oxt.log_loss_baseline_uniform.toFixed(3)} random</div>
          </div>
          <div class="bg-slate-800/50 rounded-lg p-4">
            <div class="text-xs text-slate-400 uppercase tracking-wide">Calibration error (ECE)</div>
            <div class="text-2xl font-bold">{(rel.ece * 100).toFixed(1)}%</div>
            <div class="text-xs text-slate-500">accuracy {(oxt.accuracy * 100).toFixed(1)}%</div>
          </div>
        </div>

        <!-- Reliability: stated confidence vs actual hit-rate, per bucket -->
        <h3 class="text-sm font-semibold text-slate-300 mb-2">Reliability — does "X%" actually happen X% of the time?</h3>
        <div class="space-y-2 mb-2">
          {#each rel.bins.filter((b) => b.count > 0) as b}
            <div class="flex items-center gap-3 text-xs">
              <div class="w-20 text-slate-400 shrink-0">{Math.round(b.lo * 100)}–{Math.round(b.hi * 100)}%</div>
              <div class="flex-1 space-y-1">
                <div class="h-2.5 rounded bg-slate-700/60" style="width: {Math.max(b.mean_confidence * 100, 2)}%"></div>
                <div class="h-2.5 rounded bg-cyan-500" style="width: {Math.max(b.accuracy * 100, 2)}%"></div>
              </div>
              <div class="w-28 text-right text-slate-400 shrink-0">
                said {(b.mean_confidence * 100).toFixed(0)}% · hit {(b.accuracy * 100).toFixed(0)}%
              </div>
              <div class="w-12 text-right text-slate-500 shrink-0">n={b.count}</div>
            </div>
          {/each}
        </div>
        <div class="text-xs text-slate-500 mb-4">
          <span class="inline-block w-3 h-2 rounded bg-slate-700/60 align-middle"></span> stated confidence ·
          <span class="inline-block w-3 h-2 rounded bg-cyan-500 align-middle"></span> actual hit-rate
        </div>

        {#if calibration.markets && calibration.markets.length > 0}
          <h3 class="text-sm font-semibold text-slate-300 mb-2">By market</h3>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="text-slate-400 text-left text-xs uppercase">
                  <th class="py-1 pr-4">Market</th>
                  <th class="py-1 pr-4">Hit rate</th>
                  <th class="py-1 pr-4">Brier</th>
                  <th class="py-1 pr-4">Sample</th>
                </tr>
              </thead>
              <tbody>
                {#each calibration.markets as m}
                  <tr class="border-t border-slate-700/50">
                    <td class="py-1.5 pr-4 font-medium">{m.market}</td>
                    <td class="py-1.5 pr-4">{(m.accuracy * 100).toFixed(1)}%</td>
                    <td class="py-1.5 pr-4">{m.brier.toFixed(3)}</td>
                    <td class="py-1.5 pr-4 text-slate-400">n={m.n}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>
    {/if}

    <!-- Weekly Performance Section (Backtest Results) - Only show if we have real data -->
    {#if dedupedBacktestHistory && dedupedBacktestHistory.length > 0}
      <div class="glass-card p-6 border border-green-500/30">
        <div class="flex items-center justify-between mb-4">
          <div>
            <h2 class="text-xl font-bold text-green-400">
              ✅ {$_('modelStats.weeklyPerformance')}
            </h2>
            <p class="text-xs text-slate-400">
              {$_('modelStats.verifiedResults')}
            </p>
          </div>
          <div class="text-right">
            <div class="text-2xl font-bold text-white">
              {backtestHistory.summary.avg_accuracy.toFixed(1)}%
            </div>
            <div class="text-xs text-slate-400">{$_('modelStats.avgAccuracy')}</div>
          </div>
        </div>

        <div class="space-y-3">
          {#each dedupedBacktestHistory.slice().reverse().slice(0, 3) as week}
            <div
              class="bg-white/5 rounded p-3 flex justify-between items-center"
            >
              <div>
                <div class="font-bold text-sm">
                  {$_('common.weekOf')} {new Date(week.date).toLocaleDateString($locale || 'en-US')}
                </div>
                <div class="text-xs text-slate-400">
                  {week.summary.evaluated} {$_('modelStats.matchesEvaluated')}
                </div>
              </div>
              <div class="text-right">
                <div
                  class="font-bold {week.summary.accuracy >= 40
                    ? 'text-green-400'
                    : 'text-amber-400'}"
                >
                  {week.summary.accuracy.toFixed(1)}%
                </div>
              </div>
            </div>
          {/each}
        </div>
      </div>
    {:else}
      <!-- No backtest data yet -->
      <div class="glass-card p-6 border border-amber-500/30">
        <div class="flex items-start gap-3">
          <span class="text-2xl">📊</span>
          <div>
            <h3 class="font-bold text-amber-400">
              {$_('modelStats.performanceTracking')}
            </h3>
            <p class="text-sm text-slate-400 mt-1">
              {$_('modelStats.trackingDesc')}
            </p>
            <p class="text-xs text-slate-500 mt-2">
              {$_('modelStats.backtestsAuto')}
            </p>
          </div>
        </div>
      </div>
    {/if}

    <!-- League-Specific Accuracy Breakdown -->
    <div class="glass-card p-6 border border-purple-500/30">
      <div class="flex flex-col gap-4 mb-4 md:flex-row md:items-end md:justify-between">
        <div class="flex items-center gap-2">
          <span class="text-xl">🏆</span>
          <div>
            <h2 class="text-xl font-bold text-purple-400">
              {$_('modelStats.accuracyByLeague')}
            </h2>
            <p class="text-xs text-slate-400">
              {$_('modelStats.leagueBreakdownDesc')}
            </p>
          </div>
        </div>
        <div class="flex flex-col gap-3 text-sm md:flex-row md:items-center">
          <label class="flex items-center gap-2">
            <span class="text-slate-400">{$_('modelStats.sortLeagues')}</span>
            <select bind:value={leagueSortBy} class="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white">
              <option value="accuracy">{$_('modelStats.sortAccuracy')}</option>
              <option value="matches">{$_('modelStats.sortMatches')}</option>
              <option value="name">{$_('modelStats.sortName')}</option>
            </select>
          </label>
          <label class="flex items-center gap-2">
            <span class="text-slate-400">{$_('modelStats.minMatches')}</span>
            <select bind:value={leagueMinMatches} class="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white">
              <option value={3}>3+</option>
              <option value={5}>5+</option>
              <option value={10}>10+</option>
            </select>
          </label>
        </div>
      </div>
      <AccuracyTracker showAllLeagues={true} sortBy={leagueSortBy} minMatches={Number(leagueMinMatches)} />
    </div>

    <!-- 3-Market Accuracy Section -->
    {#if marketMetrics && (marketMetrics["7_day"] || marketMetrics["all_time"])}
      {@const m = marketMetrics["7_day"] || {}}
      {@const allTime = marketMetrics["all_time"] || {}}
      {@const total = m.total_predictions || allTime.total_predictions || 0}
      <div class="glass-card p-6 border border-blue-500/30">
        <div class="flex items-center justify-between mb-4">
          <div>
            <h2 class="text-xl font-bold text-blue-400">
              📊 {$_('modelStats.marketAccuracy')}
            </h2>
            <p class="text-xs text-slate-400">
              {$_('modelStats.allMarkets')}
            </p>
          </div>
          <div class="text-right">
            <div class="text-lg font-bold text-slate-300">
              {allTime.total_predictions || total} {$_('common.matches')}
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <!-- 1X2 Match Result -->
          <div class="bg-gradient-to-br from-green-500/20 to-emerald-600/20 rounded-lg p-4 border border-green-500/30">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-xl">⚽</span>
              <span class="font-bold text-green-400">{$_('modelStats.matchResult')}</span>
            </div>
            <div class="text-3xl font-bold text-white">
              {#if m.match_result}
                {(m.match_result.accuracy * 100).toFixed(1)}%
              {:else if allTime.accuracy}
                {(allTime.accuracy * 100).toFixed(1)}%
              {:else}
                --
              {/if}
            </div>
            <div class="text-xs text-slate-400 mt-1">
              {m.match_result?.correct || allTime.correct_predictions || 0}/{m.match_result?.total || allTime.total_predictions || 0} {$_('common.correct')}
            </div>
          </div>

          <!-- BTTS -->
          <div class="bg-gradient-to-br from-purple-500/20 to-pink-600/20 rounded-lg p-4 border border-purple-500/30">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-xl">🎯</span>
              <span class="font-bold text-purple-400">{$_('modelStats.bttsMarket')}</span>
            </div>
            <div class="text-3xl font-bold text-white">
              {#if m.btts}
                {(m.btts.accuracy * 100).toFixed(1)}%
              {:else if allTime.btts_accuracy}
                {(allTime.btts_accuracy * 100).toFixed(1)}%
              {:else}
                --
              {/if}
            </div>
            <div class="text-xs text-slate-400 mt-1">
              {$_('prediction.btts')}
            </div>
          </div>

          <!-- Over 2.5 Goals -->
          <div class="bg-gradient-to-br from-orange-500/20 to-red-600/20 rounded-lg p-4 border border-orange-500/30">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-xl">📈</span>
              <span class="font-bold text-orange-400">{$_('modelStats.over25Market')}</span>
            </div>
            <div class="text-3xl font-bold text-white">
              {#if m.over25}
                {(m.over25.accuracy * 100).toFixed(1)}%
              {:else if allTime.over25_accuracy}
                {(allTime.over25_accuracy * 100).toFixed(1)}%
              {:else}
                --
              {/if}
            </div>
            <div class="text-xs text-slate-400 mt-1">
              {$_('prediction.over25')}
            </div>
          </div>
        </div>

        <!-- Exact Score bonus -->
        {#if (m.exact_score && m.exact_score.correct > 0) || allTime.exact_score_count > 0}
          <div class="mt-4 bg-white/5 rounded-lg p-3 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="text-lg">🏆</span>
              <span class="text-sm text-slate-300">{$_('modelStats.exactScore')}</span>
            </div>
            <div class="text-sm font-bold text-amber-400">
              {#if m.exact_score}
                {m.exact_score.correct} correct ({(m.exact_score.accuracy * 100).toFixed(1)}%)
              {:else}
                {allTime.exact_score_count} correct ({(allTime.exact_score_rate * 100).toFixed(1)}%)
              {/if}
            </div>
          </div>
        {/if}
      </div>
    {/if}

    {#if apiAvailable && stats}
      <!-- Ensemble overview only -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
        <div class="glass-card p-6">
          <div class="text-sm text-slate-400 mb-2">{$_('modelStats.activeModels')}</div>
          <div class="text-3xl md:text-4xl font-bold text-green-400">
            {stats.active_model_count ?? 0}
          </div>
          <div class="text-xs text-slate-500 mt-1">
            {$_('modelStats.contributingTo')}
          </div>
        </div>
        <div class="glass-card p-6">
          <div class="text-sm text-slate-400 mb-2">{$_('modelStats.trackingSince')}</div>
          <div class="text-xl md:text-2xl font-bold">
            {#if stats.tracking_since}
              {new Date(stats.tracking_since).toLocaleDateString($locale || 'en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
            {:else}
              Nov 25, 2025
            {/if}
          </div>
          <div class="text-xs text-slate-500 mt-1">
            {$_('modelStats.appLaunchDate')}
          </div>
        </div>
      </div>

      {#if stats.note}
        <div class="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
          <p class="text-sm text-blue-300">💡 {stats.note}</p>
        </div>
      {/if}

      <div class="glass-card p-4 md:p-6">
        <h2 class="text-xl md:text-2xl font-bold mb-6">
          {$_('modelStats.ensembleSummary')}
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="bg-white/5 rounded-lg p-4">
            <div class="text-xs text-slate-400 mb-1">{$_('modelStats.activeComponents')}</div>
            <div class="text-2xl font-bold text-green-400">{stats.active_model_count ?? 0}</div>
          </div>
          <div class="bg-white/5 rounded-lg p-4">
            <div class="text-xs text-slate-400 mb-1">{$_('modelStats.auxiliaryComponents')}</div>
            <div class="text-2xl font-bold text-slate-200">{stats.auxiliary_model_count ?? 0}</div>
          </div>
          <div class="bg-white/5 rounded-lg p-4">
            <div class="text-xs text-slate-400 mb-1">{$_('modelStats.avgEnsembleConfidence')}</div>
            <div class="text-2xl font-bold text-accent">{((stats.avg_ensemble_confidence || 0) * 100).toFixed(1)}%</div>
          </div>
        </div>
      </div>
    {:else}
      <!-- No stats available - Show model descriptions only -->
      <div class="glass-card p-4 md:p-6 border border-amber-500/30">
        <div class="flex items-start gap-3 mb-4">
          <span class="text-2xl">📊</span>
          <div>
            <h3 class="font-bold text-amber-400">
              {$_('modelStats.performanceTrackingSoon')}
            </h3>
            <p class="text-sm text-slate-400 mt-1">
              {$_('modelStats.liveMetricsSoon')}
            </p>
          </div>
        </div>
      </div>

      <!-- How It Works -->
      <div class="glass-card p-4 md:p-6">
        <h3 class="text-lg md:text-xl font-bold mb-4">
          {$_('modelStats.howItWorks')}
        </h3>
        <div class="space-y-4 text-sm text-slate-300">
          <div class="flex gap-3">
            <span class="text-accent font-bold">1.</span>
            <p>{$_('modelStats.step1')}</p>
          </div>
          <div class="flex gap-3">
            <span class="text-accent font-bold">2.</span>
            <p>{$_('modelStats.step2')}</p>
          </div>
          <div class="flex gap-3">
            <span class="text-accent font-bold">3.</span>
            <p>{$_('modelStats.step3')}</p>
          </div>
          <div class="flex gap-3">
            <span class="text-accent font-bold">4.</span>
            <p>{$_('modelStats.step4')}</p>
          </div>
        </div>
      </div>
    {/if}
  {/if}
</div>
