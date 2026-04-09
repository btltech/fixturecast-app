<script>
  import SEOHead from "../components/SEOHead.svelte";
  import { generateDailyAccasSEO } from "../services/seoService.js";
  let seoData;
  import { onMount } from "svelte";
  import { _, locale as localeStore } from "svelte-i18n";
    $: seoData = generateDailyAccasSEO($localeStore);
  import { get } from "svelte/store";
  import Navbar from "../components/Navbar.svelte";
  import { LEAGUES } from "../services/leagues.js";

  const leagueNameToEmoji = new Map(LEAGUES.map((l) => [l.name, l.emoji]));

  const BACKEND_API_URL =
    import.meta.env.VITE_API_URL ||
    "https://api.fixturecast.com";

  let accumulators = [];
  let stats = null;
  let loading = true;
  let errorKey = null;
  let emptyReason = null; // Track why no accumulators
  let selectedAcca = null;
  let nextAccaRefresh = "";

  const accaInfo = {
    "8-fold": {
      titleKey: "dailyAccas.accaTypes.8fold.title",
      descriptionKey: "dailyAccas.accaTypes.8fold.description",
      icon: "🎯",
      color: "from-blue-500 to-purple-600",
    },
    "6-fold": {
      titleKey: "dailyAccas.accaTypes.6fold.title",
      descriptionKey: "dailyAccas.accaTypes.6fold.description",
      icon: "🎲",
      color: "from-blue-500 to-purple-600",
    },
    "4-fold": {
      titleKey: "dailyAccas.accaTypes.4fold.title",
      descriptionKey: "dailyAccas.accaTypes.4fold.description",
      icon: "💎",
      color: "from-green-500 to-emerald-600",
    },
    BTTS: {
      titleKey: "dailyAccas.accaTypes.btts.title",
      descriptionKey: "dailyAccas.accaTypes.btts.description",
      icon: "⚽",
      color: "from-orange-500 to-red-600",
    },
  };

  const localeMap = {
    en: "en-US",
    es: "es-ES",
    pt: "pt-BR",
    fr: "fr-FR",
  };

  $: currentDateLabel = formatCurrentDate();
  $: nextAccaRefresh = formatNextAccaRefresh();

  onMount(async () => {
    await fetchData();
  });

  function translate(key, values) {
    const formatter = get(_);
    return formatter(key, values ? { values } : undefined);
  }

  function getDateLocale() {
    return localeMap[$localeStore] || "en-US";
  }

  function formatCurrentDate() {
    return new Date().toLocaleDateString(getDateLocale(), {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  }

  function formatNextAccaRefresh() {
    const now = new Date();
    const next = new Date(now);
    next.setUTCHours(24, 0, 0, 0);
    return next.toLocaleString(getDateLocale(), {
      weekday: "short",
      hour: "2-digit",
      minute: "2-digit",
      timeZoneName: "short",
    });
  }

  async function fetchData() {
    await Promise.all([fetchAccumulators(), fetchStats()]);
  }

  async function fetchStats() {
    try {
      const response = await fetch(
        `${BACKEND_API_URL}/api/accumulators/stats?days=30`,
      );
      if (response.ok) {
        stats = await response.json();
      }
    } catch (err) {
      console.error("Error fetching stats:", err);
    }
  }

  async function fetchAccumulators() {
    try {
      loading = true;
      const response = await fetch(`${BACKEND_API_URL}/api/accumulators/today`);

      if (!response.ok) {
        // If endpoint doesn't exist yet (404) or other error
        if (response.status === 404) {
          errorKey = "dailyAccas.deployingError";
        } else {
          errorKey = "dailyAccas.failedLoad";
        }
        return;
      }

      const data = await response.json();

      if (data.success) {
        accumulators = data.accumulators;
        errorKey = null; // Clear any previous errors
        emptyReason = null;
      } else {
        // Backend returns success: false when no accumulators
        // but this is expected, not an error - show empty state instead
        accumulators = data.accumulators || [];
        errorKey = null; // Don't treat "no accumulators" as an error
        emptyReason = {
          reason: data.reason || "unknown",
          message: data.message,
          details: data.details || {},
        };
      }
    } catch (err) {
      console.error("Error fetching accumulators:", err);
      errorKey = "dailyAccas.connectionError";
    } finally {
      loading = false;
    }
  }

  function getLeagueEmoji(leagueName) {
    return leagueNameToEmoji.get(leagueName) || "⚽";
  }

  let showCopyToast = false;

  function shareAccumulator(acca) {
    const info = accaInfo[acca.acca_type];
    const title = translate(info.titleKey);
    const selections = acca.selections
      .map((s) => `${s.home_team} vs ${s.away_team}`)
      .join(", ");
    const text = translate("dailyAccas.shareText", {
      icon: info.icon,
      title,
      selections,
    });

    if (navigator.share) {
      navigator.share({
        title,
        text: text,
        url: window.location.href,
      });
    } else {
      navigator.clipboard.writeText(window.location.href);
      showCopyToast = true;
      setTimeout(() => {
        showCopyToast = false;
      }, 2500);
    }
  }
</script>

<SEOHead data={seoData} />

<main
  class="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 pt-20 pb-12 px-4"
>
  {#if showCopyToast}
    <div class="fixed top-20 right-4 z-50 bg-slate-900/95 border border-purple-400/30 text-white text-sm px-4 py-3 rounded-xl shadow-xl">
      {$_("share.linkCopied")}
    </div>
  {/if}
  <div class="max-w-7xl mx-auto">
    <!-- Header -->
    <div class="text-center mb-12">
      <div
        class="inline-block px-4 py-2 bg-purple-600/30 rounded-full text-purple-200 text-sm font-medium mb-4"
      >
        📅 {currentDateLabel}
      </div>
      <h1 class="text-5xl font-bold text-white mb-4">{$_("dailyAccas.title")} 🎲</h1>
      <p class="text-xl text-purple-200">
        {$_("dailyAccas.subtitle")}
      </p>
      <p class="text-sm text-purple-300 mt-2">
        {$_("dailyAccas.confidenceNote")}
      </p>
    </div>

    <!-- Stats Section -->
    {#if stats && stats.settled_accumulators > 0}
      <div
        class="bg-slate-800/50 backdrop-blur-sm border border-purple-500/30 rounded-xl p-6 mb-8"
      >
        <h2 class="text-2xl font-bold text-white mb-4 flex items-center">
          <span class="mr-3">📊</span>
          {$_("dailyAccas.statsTitle")}
        </h2>
        <div class="grid grid-cols-2 gap-4">
          <div class="text-center">
            <p class="text-3xl font-bold text-green-400">
              {(stats.hit_rate * 100).toFixed(1)}%
            </p>
            <p class="text-purple-300 text-sm mt-1">{$_("dailyAccas.hitRate")}</p>
          </div>
          <div class="text-center">
            <p class="text-3xl font-bold text-white">
              {stats.won_accumulators}/{stats.settled_accumulators}
            </p>
            <p class="text-purple-300 text-sm mt-1">{$_("dailyAccas.wonTotal")}</p>
          </div>
        </div>

        {#if stats.by_type && stats.by_type.length > 0}
          <div class="mt-6 pt-6 border-t border-purple-500/30">
            <h3 class="text-lg font-semibold text-white mb-4">{$_("dailyAccas.byType")}</h3>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              {#each stats.by_type as typeStats}
                {@const settled = typeStats.settled || 0}
                {@const won = typeStats.won || 0}
                {@const hitRate = settled > 0 ? (won / settled) * 100 : 0}
                <div class="bg-slate-700/50 rounded-lg p-4">
                  <p class="text-white font-semibold mb-2">
                    {accaInfo[typeStats.acca_type]?.icon}
                    {accaInfo[typeStats.acca_type]?.title ||
                      typeStats.acca_type}
                  </p>
                  <div class="flex justify-between items-center">
                    <span class="text-purple-300 text-sm">{$_("dailyAccas.hitRate")}:</span>
                    <span class="text-green-400 font-bold"
                      >{hitRate.toFixed(1)}%</span
                    >
                  </div>
                  <div class="flex justify-between items-center mt-1">
                    <span class="text-purple-300 text-sm">{$_("dailyAccas.won")}</span>
                    <span class="text-white">{won}/{settled}</span>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    {/if}

    {#if loading}
      <div class="flex justify-center items-center py-20">
        <div
          class="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-purple-500"
        ></div>
      </div>
    {:else if errorKey}
      <div
        class="bg-yellow-500/20 border border-yellow-500 rounded-lg p-8 text-center max-w-2xl mx-auto"
      >
        <div class="text-6xl mb-4">⏳</div>
        <p class="text-yellow-100 text-xl font-semibold mb-3">{$_(errorKey)}</p>
        <p class="text-yellow-200 text-sm mb-6">
          {$_("dailyAccas.deploymentCopy")}
        </p>
        <button
          on:click={fetchAccumulators}
          class="px-8 py-3 bg-yellow-600 hover:bg-yellow-700 text-white font-semibold rounded-lg transition shadow-lg"
        >
          {$_("dailyAccas.checkAgain")}
        </button>
        <p class="text-yellow-300 text-xs mt-4">
          💡 {$_("dailyAccas.firstTip")}
        </p>
      </div>
    {:else if accumulators.length === 0}
      <div
        class="bg-slate-800/50 backdrop-blur-sm border border-purple-500/30 rounded-xl p-8 text-center max-w-2xl mx-auto"
      >
        {#if emptyReason?.reason === "no_matches"}
          <div class="text-6xl mb-4">📅</div>
          <p class="text-white text-2xl font-bold mb-3">{$_("dailyAccas.noMatchesTodayTitle")}</p>
          <p class="text-purple-200 text-base mb-6">
            {$_("dailyAccas.noMatchesTodayDesc")}
          </p>
        {:else if emptyReason?.reason === "low_confidence"}
          <div class="text-6xl mb-4">🎯</div>
          <p class="text-white text-2xl font-bold mb-3">{$_("dailyAccas.qualityCheckFailed")}</p>
          <p class="text-purple-200 text-base mb-6">
            {$_("dailyAccas.qualityCheckDesc", { values: { count: emptyReason.details.fixture_count || 0 } })}
          </p>
          <div class="bg-slate-700/50 rounded-lg p-6 text-left space-y-3">
            <p class="text-purple-300 text-sm">
              <strong class="text-white">{$_("dailyAccas.whyNoAccas")}</strong>
            </p>
            <ul class="text-purple-200 text-sm space-y-2 list-disc list-inside">
              <li>
                {$_("dailyAccas.highConfidenceFound", { values: { count: emptyReason.details.predictions_with_quality || 0 } })}
              </li>
              <li>
                {$_("dailyAccas.limitedData")}
              </li>
              <li>
                {$_("dailyAccas.confidenceThreshold")}
              </li>
              <li>{$_("dailyAccas.protectsYou")}</li>
            </ul>
          </div>
        {:else}
          <div class="text-6xl mb-4">📅</div>
          <p class="text-white text-2xl font-bold mb-3">
            {$_("dailyAccas.noAccumulatorsTitle")}
          </p>
          <p class="text-purple-200 text-base mb-6">
            {$_("dailyAccas.noAccumulatorsDesc")}
          </p>
        {/if}

        <div class="mt-6 pt-6 border-t border-purple-500/30">
          <p class="text-purple-300 text-sm mb-4">
            💡 <strong class="text-white">{$_("dailyAccas.whenCheckBack")}</strong>
          </p>
          <p class="text-purple-200 text-sm">
            {$_("dailyAccas.bestDays")}
          </p>
          <p class="text-purple-300 text-sm mt-4">
            {$_("dailyAccas.nextRefresh")} <strong class="text-white">{nextAccaRefresh}</strong>
          </p>
        </div>
        <button
          on:click={fetchData}
          class="mt-6 px-8 py-3 bg-purple-600 hover:bg-purple-700 text-white font-semibold rounded-lg transition shadow-lg"
        >
          {$_("dailyAccas.refresh")}
        </button>
      </div>
    {:else}
      <!-- Accumulator Cards -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {#each accumulators as acca}
          {@const info = accaInfo[acca.acca_type]}
          <div
            class="bg-slate-800/50 backdrop-blur-sm border border-purple-500/30 rounded-xl overflow-hidden hover:border-purple-500 transition-all duration-300 hover:shadow-xl hover:shadow-purple-500/20"
          >
            <!-- Header -->
            <div class="bg-gradient-to-r {info.color} p-6 text-white relative">
              {#if acca.status === "settled"}
                <div
                  class="absolute top-4 right-4 px-3 py-1 rounded-full text-sm font-bold {acca.won
                    ? 'bg-green-500'
                    : 'bg-red-500'}"
                >
                  {acca.won ? `✓ ${$_("dailyAccas.wonBadge")}` : `✗ ${$_("dailyAccas.lostBadge")}`}
                </div>
              {/if}
              <div class="flex items-center justify-between mb-3">
                <span class="text-4xl">{info.icon}</span>
                <span
                  class="px-3 py-1 bg-white/20 rounded-full text-sm font-semibold"
                >
                  {$_("dailyAccas.matchCount", { values: { count: acca.selections.length } })}
                </span>
              </div>
              <h2 class="text-2xl font-bold mb-2">{$_(info.titleKey)}</h2>
              <p class="text-white/90 text-sm">{$_(info.descriptionKey)}</p>
            </div>

            <!-- Picks Summary -->
            <div class="p-6 border-b border-purple-500/20">
              <p class="text-purple-300 text-sm">{$_("dailyAccas.recommendedPicks")}</p>
              <p class="text-white text-sm mt-2">{$_("dailyAccas.confidenceShown")}</p>
            </div>

            <!-- Selections Preview -->
            <div class="p-6">
              <h3 class="text-white font-semibold mb-3 flex items-center">
                <span class="mr-2">📋</span>
                {$_("dailyAccas.selections")}
              </h3>
              <div class="space-y-2 max-h-64 overflow-y-auto">
                {#each acca.selections as selection}
                  <div
                    class="bg-slate-700/50 rounded-lg p-3 hover:bg-slate-700 transition {selection.won !==
                    null
                      ? selection.won
                        ? 'border-l-4 border-green-500'
                        : 'border-l-4 border-red-500'
                      : ''}"
                  >
                    <div class="flex items-start justify-between mb-1">
                      <div class="flex-1">
                        <p
                          class="text-white text-sm font-medium flex items-center"
                        >
                          {#if selection.won !== null}
                            <span class="mr-2">{selection.won ? "✓" : "✗"}</span
                            >
                          {/if}
                          {selection.home_team} vs {selection.away_team}
                        </p>
                        <p class="text-purple-300 text-xs mt-1">
                          {getLeagueEmoji(selection.league_name)}
                          {selection.league_name}
                        </p>
                      </div>
                    </div>
                    <div class="flex items-center justify-between mt-2">
                      <span class="text-green-400 text-xs font-medium">
                        {selection.selection_value ||
                          selection.predicted_outcome}
                      </span>
                      <span class="text-purple-300 text-xs">
                        {$_("dailyAccas.confidenceLabel", { values: { count: selection.confidence?.toFixed(0) || 0 } })}
                      </span>
                    </div>
                    {#if selection.result}
                      <p class="text-xs text-purple-300 mt-1 italic">
                        {selection.result}
                      </p>
                    {/if}
                  </div>
                {/each}
              </div>
            </div>

            <!-- Actions -->
            <div class="p-6 pt-0">
              <button
                on:click={() => shareAccumulator(acca)}
                class="w-full py-3 bg-gradient-to-r {info.color} text-white rounded-lg font-semibold hover:opacity-90 transition flex items-center justify-center"
              >
                <span class="mr-2">📤</span>
                {$_("dailyAccas.shareAccumulator")}
              </button>
            </div>
          </div>
        {/each}
      </div>

      <!-- Disclaimer -->
      <div
        class="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-6 text-center"
      >
        <p class="text-yellow-200 text-sm">
          ⚠️ <strong>{$_("dailyAccas.disclaimer")}</strong> {$_("dailyAccas.disclaimerText")}
        </p>
      </div>
    {/if}
  </div>
</main>

<style>
  :global(body) {
    overflow-x: hidden;
  }
</style>
