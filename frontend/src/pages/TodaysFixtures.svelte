<script>
  import SEOHead from "../components/SEOHead.svelte";
  import { generateTodaysFixturesSEO } from "../services/seoService.js";
  let seoData;
  import { onMount } from "svelte";
  import { _ } from "svelte-i18n";
  import { locale } from "../lib/i18n";
  $: seoData = generateTodaysFixturesSEO($locale);
  import { Link } from "svelte-routing";
  import { API_URL, ML_API_URL } from "../config.js";
  import { compareStore } from "../services/compareStore.js";
  import SkeletonLoader from "../components/SkeletonLoader.svelte";
  import SearchBar from "../components/SearchBar.svelte";
  import ConfidenceBadge from "../components/ConfidenceBadge.svelte";
  import { getCurrentSeason } from "../services/season.js";
  import { getLeagueDisplay as leagueDisplay } from "../services/leagues.js";

  function getLeagueDisplay(leagueId) {
    return leagueDisplay(leagueId);
  }

  let todaysMatches = [];
  let matchOfTheDay = null;
  let upcomingMatches = [];
  let upcomingDaysAhead = null;
  let loading = true;
  let error = null;
  let searchQuery = "";
  const season = getCurrentSeason();
  let userTimezone = "UTC"; // populated on mount (avoids SSR value from Cloudflare worker)
  let timezoneMode = "auto";
  let manualTimezone = "UTC";
  let autoLoadPredictionsEnabled = true;

  const timezoneOptions = [
    "UTC",
    "Europe/London",
    "Europe/Madrid",
    "America/New_York",
    "America/Chicago",
    "America/Los_Angeles",
    "Africa/Lagos",
    "Asia/Tokyo",
    "Australia/Sydney",
  ];

  // Predictions state
  let predictions = {};
  let loadingPredictions = {};

  // Group matches by league
  $: matchesByLeague = groupByLeague(filteredMatches);

  function groupByLeague(matches) {
    const grouped = {};
    for (const match of matches) {
      const leagueId = match.league?.id || 0;
      if (!grouped[leagueId]) {
        grouped[leagueId] = [];
      }
      grouped[leagueId].push(match);
    }
    return grouped;
  }

  $: filteredMatches = todaysMatches.filter((fixture) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const home = fixture.teams.home.name.toLowerCase();
    const away = fixture.teams.away.name.toLowerCase();
    const league = (fixture.league?.name || "").toLowerCase();
    return home.includes(q) || away.includes(q) || league.includes(q);
  });

  function formatTime(dateStr) {
    return new Date(dateStr).toLocaleTimeString([], {
      timeZone: userTimezone,
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function formatLongDate() {
    return new Date().toLocaleDateString($locale || "en-GB", {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
      timeZone: userTimezone,
    });
  }

  function getTimezoneLabel() {
    return timezoneMode === "auto" ? `${userTimezone} (${$_("todaysFixtures.autoTimezone")})` : manualTimezone;
  }

  async function loadTodaysFixtures(retries = 2) {
    loading = true;
    error = null;

    try {
      const res = await fetch(`${API_URL}/api/fixtures/today`);
      if (res.ok) {
        const data = await res.json();
        todaysMatches = data.response || [];
        matchOfTheDay = data.match_of_the_day;
        upcomingMatches = data.upcoming_fixtures || [];
        upcomingDaysAhead = data.upcoming_days_ahead ?? null;

        // If empty response, retry (backend may still be warming up)
        if (todaysMatches.length === 0 && !matchOfTheDay && retries > 0) {
          await new Promise((r) => setTimeout(r, 2000));
          return await loadTodaysFixtures(retries - 1);
        }

        if (autoLoadPredictionsEnabled) {
          autoLoadAllPredictions(todaysMatches);
        }
      } else if (retries > 0) {
        await new Promise((r) => setTimeout(r, 2000));
        return await loadTodaysFixtures(retries - 1);
      } else {
        error = $_("errors.homeFixturesLoad");
      }
    } catch (e) {
      console.error("Error loading today's matches:", e);
      if (retries > 0) {
        await new Promise((r) => setTimeout(r, 2000));
        return await loadTodaysFixtures(retries - 1);
      }
      error = $_("errors.homeFixturesLoad");
    }
    // Only set loading=false when done (not retrying)
    loading = false;
  }

  async function autoLoadAllPredictions(matches) {
    const batchSize = 3;
    for (let i = 0; i < matches.length; i += batchSize) {
      const batch = matches.slice(i, i + batchSize);
      await Promise.allSettled(
        batch.map((m) => loadPrediction(m.fixture.id, m.league?.id || 39)),
      );
    }
  }

  async function loadPrediction(fixtureId, leagueId) {
    if (predictions[fixtureId] || loadingPredictions[fixtureId]) {
      return;
    }

    loadingPredictions[fixtureId] = true;
    loadingPredictions = { ...loadingPredictions };

    try {
      const res = await fetch(
        `${ML_API_URL}/api/prediction/${fixtureId}?league=${leagueId}&season=${season}`,
      );

      if (res.ok) {
        const data = await res.json();
        predictions[fixtureId] = data.prediction;
        predictions = { ...predictions };
      }
    } catch (e) {
      console.error(`Error loading prediction for ${fixtureId}:`, e);
    } finally {
      loadingPredictions[fixtureId] = false;
      loadingPredictions = { ...loadingPredictions };
    }
  }

  function getPredictionSummary(pred) {
    if (!pred) return null;

    const homeProb = pred.home_win_prob * 100;
    const drawProb = pred.draw_prob * 100;
    const awayProb = pred.away_win_prob * 100;

    if (homeProb > awayProb && homeProb > drawProb) {
      return { winner: "home", prob: homeProb, label: "Home Win" };
    } else if (awayProb > homeProb && awayProb > drawProb) {
      return { winner: "away", prob: awayProb, label: "Away Win" };
    } else {
      return { winner: "draw", prob: drawProb, label: "Draw" };
    }
  }

  onMount(() => {
    const detectedTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    timezoneMode = localStorage.getItem("todays-fixtures-timezone-mode") || "auto";
    manualTimezone = localStorage.getItem("todays-fixtures-manual-timezone") || detectedTimezone;
    autoLoadPredictionsEnabled = localStorage.getItem("todays-fixtures-auto-load") !== "false";
    userTimezone = timezoneMode === "manual" ? manualTimezone : detectedTimezone;
    loadTodaysFixtures();
  });

  $: if (timezoneMode === "manual") {
    userTimezone = manualTimezone;
  }

  $: if (timezoneMode === "auto" && typeof Intl !== "undefined") {
    userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  }

  function handleTimezoneModeChange(event) {
    timezoneMode = event.currentTarget.value;
    localStorage.setItem("todays-fixtures-timezone-mode", timezoneMode);
  }

  function handleManualTimezoneChange(event) {
    manualTimezone = event.currentTarget.value;
    localStorage.setItem("todays-fixtures-manual-timezone", manualTimezone);
  }

  function handleAutoLoadToggle(event) {
    autoLoadPredictionsEnabled = event.currentTarget.checked;
    localStorage.setItem("todays-fixtures-auto-load", String(autoLoadPredictionsEnabled));
    if (autoLoadPredictionsEnabled && todaysMatches.length > 0) {
      autoLoadAllPredictions(todaysMatches);
    }
  }
</script>

<SEOHead data={seoData} />

<div class="page-enter space-y-6 pb-12">
  <!-- Header -->
  <div class="flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <div>
        <h1
          class="text-2xl lg:text-3xl font-display font-bold flex items-center gap-3"
        >
          <span class="text-3xl">📅</span>
          {$_("fixtures.todaysFixtures")}
        </h1>
        <p class="text-slate-400 mt-1">
          {$_("todaysFixtures.subtitle")} • {formatLongDate()}
        </p>
        <p class="text-xs text-slate-500 mt-0.5">
          🕐 {$_("todaysFixtures.timezoneLabel")} ({getTimezoneLabel()})
        </p>
      </div>
      <button
        on:click={() => loadTodaysFixtures()}
        class="p-2.5 rounded-lg bg-white/5 hover:bg-white/10 transition-colors touch-target"
        title={$_("todaysFixtures.refresh")}
      >
        <svg
          class="w-5 h-5 {loading ? 'animate-spin' : ''}"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
      </button>
    </div>

    <div class="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto_auto] lg:items-end">
      <div class="max-w-md">
      <input
        type="text"
        bind:value={searchQuery}
        placeholder={$_("todaysFixtures.searchPlaceholder")}
        class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-400 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50"
      />
      </div>
      <div class="flex gap-2 items-center">
        <select bind:value={timezoneMode} on:change={handleTimezoneModeChange} class="px-3 py-2.5 bg-white/5 border border-white/10 rounded-xl text-white text-sm">
          <option value="auto">{$_("todaysFixtures.autoTimezone")}</option>
          <option value="manual">{$_("todaysFixtures.manualTimezone")}</option>
        </select>
        {#if timezoneMode === "manual"}
          <select bind:value={manualTimezone} on:change={handleManualTimezoneChange} class="px-3 py-2.5 bg-white/5 border border-white/10 rounded-xl text-white text-sm">
            {#each timezoneOptions as tz}
              <option value={tz}>{tz}</option>
            {/each}
          </select>
        {/if}
      </div>
      <label class="flex items-center gap-2 text-sm text-slate-300 bg-white/5 border border-white/10 rounded-xl px-3 py-2.5" title={$_("todaysFixtures.autoLoadHelp")}>
        <input type="checkbox" checked={autoLoadPredictionsEnabled} on:change={handleAutoLoadToggle} class="accent-cyan-400" />
        <span>{$_("fixtures.autoLoadPredictions")}</span>
        <span class="text-slate-500">ⓘ</span>
      </label>
    </div>
  </div>

  {#if loading}
    <!-- Loading State -->
    <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {#each Array(9) as _}
        <SkeletonLoader type="fixture" />
      {/each}
    </div>
  {:else if error}
    <!-- Error State -->
    <div class="glass-card p-12 text-center">
      <div class="text-4xl mb-4">⚠️</div>
      <h3 class="font-display font-bold text-xl mb-2 text-red-400">{error}</h3>
      <button
        on:click={() => loadTodaysFixtures()}
        class="mt-4 px-6 py-2 bg-primary/20 hover:bg-primary/30 text-primary rounded-lg font-medium"
      >
        {$_("common.retry")}
      </button>
    </div>
  {:else if todaysMatches.length === 0}
    <!-- No Matches: show upcoming fallback if available, else dead-end with link -->
    {#if upcomingMatches.length > 0}
      <div class="space-y-4">
        <div class="glass-card p-4 flex items-center gap-3 text-slate-300 border-primary/20">
          <span class="text-2xl">📅</span>
          <p class="text-sm">
            {upcomingDaysAhead === 1
              ? $_("home.upcomingTomorrow")
              : $_("home.upcomingInDays", { values: { days: upcomingDaysAhead } })}
          </p>
        </div>
        <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {#each upcomingMatches.slice(0, 9) as fixture}
            <Link
              to={`/prediction/${fixture.fixture.id}?league=${fixture.league?.id || 39}&season=${season}`}
              class="group glass-card p-4 hover:border-primary/30 transition-all hover:-translate-y-1"
            >
              <div class="flex items-center justify-between mb-3 text-xs text-slate-400">
                <span>{fixture.league?.name}</span>
                <span class="font-mono">{formatTime(fixture.fixture.date)}</span>
              </div>
              <div class="space-y-3">
                <div class="flex items-center gap-3">
                  <img src={fixture.teams.home.logo} alt={fixture.teams?.home?.name || "Home"} class="w-8 h-8 object-contain" />
                  <span class="font-medium group-hover:text-white transition-colors">{fixture.teams.home.name}</span>
                </div>
                <div class="flex items-center gap-3">
                  <img src={fixture.teams.away.logo} alt={fixture.teams?.away?.name || "Away"} class="w-8 h-8 object-contain" />
                  <span class="font-medium group-hover:text-white transition-colors">{fixture.teams.away.name}</span>
                </div>
              </div>
            </Link>
          {/each}
        </div>
      </div>
    {:else}
      <div class="glass-card p-12 text-center">
        <div class="text-6xl mb-4">😴</div>
        <h3 class="font-display font-bold text-xl mb-2">{$_("fixtures.noMatchesToday")}</h3>
        <p class="text-slate-400 mb-4">
          {$_("todaysFixtures.noMatchesScheduled")}
        </p>
        <Link
          to="/fixtures"
          class="inline-flex items-center gap-2 px-6 py-3 bg-primary/20 hover:bg-primary/30 text-primary rounded-lg font-medium"
        >
          {$_("todaysFixtures.browseUpcoming")}
          <svg
            class="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 5l7 7-7 7"
            />
          </svg>
        </Link>
      </div>
    {/if}
  {:else}
    <!-- Match of the Day Highlight -->
    {#if matchOfTheDay}
      <div
        class="glass-card p-4 md:p-6 border-amber-500/30 bg-gradient-to-r from-amber-500/10 to-transparent"
      >
        <div class="flex items-center gap-2 mb-4">
          <span class="text-amber-400 text-xl">⭐</span>
          <h2
            class="font-display font-bold text-base md:text-lg text-amber-400"
          >
            {$_("todaysFixtures.matchOfTheDay")}
          </h2>
        </div>

        <Link
          to={`/prediction/${matchOfTheDay.fixture.id}?league=${matchOfTheDay.league?.id || 39}&season=${season}`}
          class="block group"
        >
          <div class="flex items-center justify-between">
            <!-- Home Team -->
            <div class="flex-1 text-center">
              <img
                src={matchOfTheDay.teams.home.logo}
                alt={matchOfTheDay.teams.home.name}
                class="w-16 h-16 mx-auto mb-2 group-hover:scale-110 transition-transform"
              />
              <div class="font-bold text-sm sm:text-base">
                {matchOfTheDay.teams.home.name}
              </div>
            </div>

            <!-- VS & Time -->
            <div class="px-6 text-center">
              <div class="text-xs text-slate-400 mb-1">
                {getLeagueDisplay(matchOfTheDay.league?.id).emoji}
                {matchOfTheDay.league?.name}
              </div>
              <div
                class="text-xl sm:text-2xl font-display font-bold text-primary"
              >
                {formatTime(matchOfTheDay.fixture.date)}
              </div>
              <div class="text-xs text-slate-400">{getTimezoneLabel()}</div>
            </div>

            <!-- Away Team -->
            <div class="flex-1 text-center">
              <img
                src={matchOfTheDay.teams.away.logo}
                alt={matchOfTheDay.teams.away.name}
                class="w-16 h-16 mx-auto mb-2 group-hover:scale-110 transition-transform"
              />
              <div class="font-bold text-sm sm:text-base">
                {matchOfTheDay.teams.away.name}
              </div>
            </div>
          </div>

          <div class="mt-4 text-center">
            <span
              class="inline-flex items-center gap-2 px-4 py-2 bg-amber-500/20 text-amber-400 rounded-full text-sm font-medium group-hover:bg-amber-500/30 transition-colors"
            >
              🔮 {$_("todaysFixtures.viewAnalysis")}
            </span>
          </div>
        </Link>
      </div>
    {/if}

    <!-- Summary -->
    <div class="flex items-center justify-between px-2">
      <p class="text-sm text-slate-400">
        {$_("todaysFixtures.matchesPlayingToday", { values: { count: filteredMatches.length } })}
      </p>
      <p class="text-xs text-slate-500">
        {$_("todaysFixtures.leagueCount", { values: { count: Object.keys(matchesByLeague).length } })}
      </p>
    </div>

    <!-- Matches by League -->
    {#each Object.entries(matchesByLeague) as [leagueId, matches]}
      {@const league = getLeagueDisplay(parseInt(leagueId))}
      <div class="space-y-3">
        <div class="flex items-center gap-2 px-2">
          <span class="text-xl">{league.emoji}</span>
          <h2 class="font-display font-bold text-lg">
            {matches[0]?.league?.name || league.name}
          </h2>
          <span
            class="text-xs text-slate-400 bg-white/5 px-2 py-0.5 rounded-full"
          >
            {$_("todaysFixtures.matchCount", { values: { count: matches.length } })}
          </span>
        </div>

        <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {#each matches as fixture (fixture.fixture.id)}
            {@const fixtureId = fixture.fixture.id}
            {@const leagueIdNum = fixture.league?.id || 39}
            {@const pred = predictions[fixtureId]}
            {@const summary = getPredictionSummary(pred)}

            <div class="glass-card p-4 relative overflow-hidden group">
              <!-- Match Time Header -->
              <div class="flex items-center justify-between mb-3">
                <span class="text-sm text-accent font-mono font-bold">
                  {formatTime(fixture.fixture.date)}
                </span>
                <div class="flex items-center gap-2">
                  <span class="text-xs text-slate-500">
                    {fixture.fixture.venue?.name || ""}
                  </span>
                  <button
                    on:click|stopPropagation={() =>
                      compareStore.addFixture(fixtureId, leagueIdNum)}
                    class="p-1.5 rounded-md text-xs transition-colors {$compareStore?.fixtures?.includes(
                      fixtureId,
                    )
                      ? 'bg-accent/30 text-accent'
                      : 'bg-white/5 text-slate-400 hover:bg-white/10'}"
                    title="Add to compare"
                  >
                    ⚖️
                  </button>
                </div>
              </div>

              <!-- Teams -->
              <div class="flex items-center justify-between mb-4">
                <!-- Home Team -->
                <div class="flex-1 text-center">
                  <img
                    src={fixture.teams.home.logo}
                    alt={fixture.teams.home.name}
                    class="w-12 h-12 mx-auto mb-2"
                  />
                  <div class="font-medium text-sm truncate px-1">
                    {fixture.teams.home.name}
                  </div>
                </div>

                <!-- VS -->
                <div class="px-3 text-center">
                  <div class="text-xl font-bold text-slate-500">vs</div>
                </div>

                <!-- Away Team -->
                <div class="flex-1 text-center">
                  <img
                    src={fixture.teams.away.logo}
                    alt={fixture.teams.away.name}
                    class="w-12 h-12 mx-auto mb-2"
                  />
                  <div class="font-medium text-sm truncate px-1">
                    {fixture.teams.away.name}
                  </div>
                </div>
              </div>

              <!-- Prediction Section -->
              {#if pred}
                <div
                  class="bg-gradient-to-r from-accent/10 to-purple-500/10 rounded-lg p-3 border border-accent/20"
                >
                  <div class="flex justify-between items-center mb-2">
                    <span class="text-xs text-slate-400">{$_("prediction.aiPrediction")}</span>
                    <ConfidenceBadge
                      confidence={summary.prob / 100}
                      size="sm"
                      showLabel={false}
                    />
                  </div>
                  <div class="flex justify-between items-center text-xs mb-2">
                    <span
                      class="font-medium {summary.winner === 'home'
                        ? 'text-emerald-400'
                        : summary.winner === 'away'
                          ? 'text-rose-400'
                          : 'text-slate-300'}"
                    >
                      {summary.label}
                    </span>
                    <span class="text-accent font-bold"
                      >{summary.prob.toFixed(0)}%</span
                    >
                  </div>
                  <div
                    class="flex gap-1 h-2 rounded-full overflow-hidden bg-slate-700"
                  >
                    <div
                      class="bg-green-500 transition-all"
                      style="width: {pred.home_win_prob * 100}%"
                    ></div>
                    <div
                      class="bg-slate-400 transition-all"
                      style="width: {pred.draw_prob * 100}%"
                    ></div>
                    <div
                      class="bg-red-500 transition-all"
                      style="width: {pred.away_win_prob * 100}%"
                    ></div>
                  </div>
                  <Link
                    to={`/prediction/${fixtureId}?league=${leagueIdNum}&season=${season}`}
                    class="block mt-3 text-center py-2.5 bg-accent/20 hover:bg-accent/30 text-accent rounded-lg text-sm font-medium touch-target"
                  >
                    🔮 {$_("prediction.viewFullAnalysis")}
                  </Link>
                </div>
              {:else}
                <button
                  on:click={() => loadPrediction(fixtureId, leagueIdNum)}
                  disabled={loadingPredictions[fixtureId]}
                  class="w-full py-3 bg-accent/20 hover:bg-accent/30 text-accent rounded-lg font-medium text-sm flex items-center justify-center gap-2 disabled:opacity-50 touch-target"
                >
                  {#if loadingPredictions[fixtureId]}
                    <svg
                      class="w-4 h-4 animate-spin"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                      />
                    </svg>
                    {$_("fixtures.loadingPrediction")}
                  {:else}
                    🧠 {$_("fixtures.getAIPrediction")}
                  {/if}
                </button>
              {/if}
            </div>
          {/each}
        </div>
      </div>
    {/each}
  {/if}
</div>
