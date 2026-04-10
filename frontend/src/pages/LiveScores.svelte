<script>
  import SEOHead from "../components/SEOHead.svelte";
  import { generateLiveScoresSEO } from "../services/seoService.js";
  const seoData = generateLiveScoresSEO();
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { API_URL, ML_API_URL } from "../config.js";
  import SharePrediction from "../components/SharePrediction.svelte";
  import { getLeagueSeason } from "../services/season.js";
  import { FEATURED_LEAGUE_IDS } from "../services/leagues.js";
  import { _ } from "svelte-i18n";

  let liveMatches = [];
  let loading = true;
  let error = null;
  let refreshInterval;
  let predictions = {}; // fixtureId -> prediction (cached for session)
  let loadingPrediction = {}; // fixtureId -> boolean (prevent duplicate requests)
  let expandedStats = {}; // fixtureId -> boolean
  let expandedEvents = {}; // fixtureId -> boolean
  let collapsedLeagues = {}; // leagueId -> boolean

  // Auto-refresh countdown
  let countdown = 30;
  let countdownInterval;
  let lastRefresh = new Date();

  async function fetchLiveScores() {
    try {
      const response = await fetch(`${API_URL}/api/live`);
      if (!response.ok) throw new Error("Failed to fetch live scores");
      const data = await response.json();
      liveMatches = data.response || [];
      error = null;
      lastRefresh = new Date();
      countdown = 30;

      // Fetch predictions for all live matches
      fetchPredictionsForMatches(liveMatches);
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  async function fetchPredictionsForMatches(matches) {
    for (const match of matches) {
      const fixtureId = match.fixture.id;
      // Only fetch if not already cached - predictions don't change during a match
      if (!predictions[fixtureId] && !loadingPrediction[fixtureId]) {
        loadingPrediction[fixtureId] = true;
        try {
          const season = getLeagueSeason(match.league.id, match.fixture?.date);
          const res = await fetch(
            `${ML_API_URL}/api/prediction/${fixtureId}?league=${match.league.id}&season=${season}`,
          );
          if (res.ok) {
            const data = await res.json();
            predictions[fixtureId] = data.prediction;
            predictions = { ...predictions };
          }
        } catch (e) {
          // Silently fail for predictions
        } finally {
          loadingPrediction[fixtureId] = false;
        }
      }
    }
  }

  onMount(() => {
    fetchLiveScores();
    // Refresh every 30 seconds
    refreshInterval = setInterval(fetchLiveScores, 30000);
    // Countdown timer
    countdownInterval = setInterval(() => {
      countdown = Math.max(0, countdown - 1);
    }, 1000);
    return () => {
      clearInterval(refreshInterval);
      clearInterval(countdownInterval);
    };
  });

  function getMinute(fixture) {
    return fixture.fixture.status.elapsed || "0";
  }

  // Get match status badge
  function getStatusBadge(status) {
    const short = status.short;
    const elapsed = status.elapsed;

    switch (short) {
      case "1H":
        return { label: "1H", color: "bg-green-500", text: `${elapsed}'` };
      case "HT":
        return { label: "HT", color: "bg-amber-500", text: "Half Time" };
      case "2H":
        return { label: "2H", color: "bg-green-500", text: `${elapsed}'` };
      case "ET":
        return { label: "ET", color: "bg-purple-500", text: `${elapsed}'` };
      case "P":
        return { label: "PEN", color: "bg-red-500", text: "Penalties" };
      case "FT":
        return { label: "FT", color: "bg-slate-500", text: "Full Time" };
      case "AET":
        return { label: "AET", color: "bg-slate-500", text: "After ET" };
      case "PEN":
        return { label: "PEN", color: "bg-slate-500", text: "After Pens" };
      case "BT":
        return { label: "BT", color: "bg-amber-500", text: "Break" };
      case "SUSP":
        return { label: "SUSP", color: "bg-red-600", text: "Suspended" };
      case "INT":
        return { label: "INT", color: "bg-amber-600", text: "Interrupted" };
      default:
        return {
          label: short,
          color: "bg-green-500",
          text: `${elapsed || 0}'`,
        };
    }
  }

  // Featured leagues in priority order
  const FEATURED_LEAGUES = FEATURED_LEAGUE_IDS;

  // Group matches by league
  function groupByLeague(matches) {
    const groups = {};
    for (const match of matches) {
      const leagueId = match.league.id;
      if (!groups[leagueId]) {
        groups[leagueId] = {
          league: match.league,
          matches: [],
        };
      }
      groups[leagueId].matches.push(match);
    }

    // Sort: featured leagues first (in order), then others by match count
    return Object.values(groups).sort((a, b) => {
      const aIndex = FEATURED_LEAGUES.indexOf(a.league.id);
      const bIndex = FEATURED_LEAGUES.indexOf(b.league.id);

      // Both are featured: sort by priority order
      if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;
      // Only a is featured: a comes first
      if (aIndex !== -1) return -1;
      // Only b is featured: b comes first
      if (bIndex !== -1) return 1;
      // Neither featured: sort by match count
      return b.matches.length - a.matches.length;
    });
  }

  // Get event icon
  function getEventIcon(type, detail) {
    // Goal events
    if (type === "Goal") {
      if (detail?.includes("Missed Penalty")) {
        return '<svg class="w-5 h-5 inline" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="10" stroke-width="2" class="text-red-500"/><path d="M8 8l8 8M16 8l-8 8" stroke-width="2" class="text-red-500"/></svg>';
      }
      if (detail?.includes("Penalty")) {
        return '<svg class="w-5 h-5 inline text-green-400" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3" fill="white"/></svg>';
      }
      if (detail?.includes("Own Goal")) {
        return '<svg class="w-5 h-5 inline text-red-400" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2" stroke="white" stroke-width="1.5" stroke-linecap="round"/></svg>';
      }
      return '<svg class="w-5 h-5 inline text-green-400" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2" stroke="white" stroke-width="1.5" stroke-linecap="round"/></svg>';
    }
    // Card events
    if (type === "Card") {
      if (detail === "Red Card") {
        return '<svg class="w-4 h-5 inline" viewBox="0 0 16 20" fill="none"><rect width="16" height="20" rx="1" fill="#ef4444"/><rect x="1" y="1" width="14" height="18" rx="0.5" fill="#dc2626"/></svg>';
      }
      if (detail === "Second Yellow card") {
        return '<svg class="w-8 h-5 inline" viewBox="0 0 32 20" fill="none"><rect width="16" height="20" rx="1" fill="#eab308"/><rect x="1" y="1" width="14" height="18" rx="0.5" fill="#ca8a04"/><rect x="18" width="16" height="20" rx="1" fill="#ef4444"/><rect x="19" y="1" width="14" height="18" rx="0.5" fill="#dc2626"/></svg>';
      }
      return '<svg class="w-4 h-5 inline" viewBox="0 0 16 20" fill="none"><rect width="16" height="20" rx="1" fill="#eab308"/><rect x="1" y="1" width="14" height="18" rx="0.5" fill="#ca8a04"/></svg>';
    }
    // Substitution
    if (type === "subst") {
      return '<svg class="w-5 h-5 inline text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 16V4M7 4L3 8M7 4l4 4M17 8v12M17 20l4-4M17 20l-4-4"/></svg>';
    }
    // VAR events
    if (type === "Var") {
      const baseIcon =
        '<svg class="w-5 h-5 inline text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>';
      if (
        detail?.includes("Goal cancelled") ||
        detail?.includes("offside") ||
        detail?.includes("Disallowed")
      ) {
        return '<svg class="w-5 h-5 inline text-red-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/><path d="M9 7l6 6M15 7l-6 6" stroke-width="2.5"/></svg>';
      }
      if (detail?.includes("confirmed")) {
        return '<svg class="w-5 h-5 inline text-green-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/><path d="M9 10l2 2 4-4" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
      }
      return baseIcon;
    }
    return '<span class="w-1 h-1 inline-block bg-slate-500 rounded-full"></span>';
  }

  // Get prediction summary
  function getPredictionSummary(pred) {
    if (!pred) return null;
    const homeProb = pred.home_win_prob * 100;
    const drawProb = pred.draw_prob * 100;
    const awayProb = pred.away_win_prob * 100;

    if (homeProb > awayProb && homeProb > drawProb) {
      return { winner: "home", prob: homeProb, label: "Home" };
    } else if (awayProb > homeProb && awayProb > drawProb) {
      return { winner: "away", prob: awayProb, label: "Away" };
    }
    return { winner: "draw", prob: drawProb, label: "Draw" };
  }

  // Check if prediction matches current score trend
  function isPredictionMatching(pred, homeGoals, awayGoals) {
    if (!pred) return null;
    const summary = getPredictionSummary(pred);
    if (!summary) return null;

    if (summary.winner === "home" && homeGoals > awayGoals) return true;
    if (summary.winner === "away" && awayGoals > homeGoals) return true;
    if (summary.winner === "draw" && homeGoals === awayGoals) return true;
    return false;
  }

  function toggleStats(fixtureId) {
    expandedStats[fixtureId] = !expandedStats[fixtureId];
    expandedStats = { ...expandedStats };
  }

  function toggleEvents(fixtureId) {
    expandedEvents[fixtureId] = !expandedEvents[fixtureId];
    expandedEvents = { ...expandedEvents };
  }

  function toggleLeague(leagueId) {
    collapsedLeagues[leagueId] = !collapsedLeagues[leagueId];
    collapsedLeagues = { ...collapsedLeagues };
  }

  $: groupedMatches = groupByLeague(liveMatches);
  $: totalMatches = liveMatches.length;
</script>

<SEOHead data={seoData} />

<div class="space-y-6 page-enter">
  <!-- Header -->
  <div class="glass-card p-6 element-enter">
    <div
      class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4"
    >
      <div>
        <h1 class="text-2xl md:text-3xl font-bold mb-2 flex items-center gap-2">
          <span class="relative flex h-3 w-3">
            <span
              class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"
            ></span>
            <span class="relative inline-flex rounded-full h-3 w-3 bg-red-500"
            ></span>
          </span>
          Live Scores
        </h1>
        <p class="text-sm md:text-base text-slate-400">
          {totalMatches} {totalMatches === 1 ? $_('live.matchSingular') : $_('live.matchPlural')} live
        </p>
      </div>

      <!-- Auto-refresh indicator -->
      <div class="flex items-center gap-4">
        <div
          class="flex items-center gap-3 px-4 py-2 bg-white/5 rounded-lg border border-white/10"
        >
          <div class="relative w-8 h-8">
            <svg class="w-8 h-8 transform -rotate-90">
              <circle
                cx="16"
                cy="16"
                r="14"
                stroke="currentColor"
                stroke-width="2"
                fill="transparent"
                class="text-white/10"
              />
              <circle
                cx="16"
                cy="16"
                r="14"
                stroke="currentColor"
                stroke-width="2"
                fill="transparent"
                class="text-accent"
                stroke-dasharray="88"
                stroke-dashoffset={88 - (88 * countdown) / 30}
                stroke-linecap="round"
              />
            </svg>
            <span
              class="absolute inset-0 flex items-center justify-center text-xs font-bold text-accent"
            >
              {countdown}
            </span>
          </div>
          <div class="text-xs text-slate-400">
            <div class="font-medium text-white">{$_('live.autoRefresh')}</div>
            <div>
              {$_('live.last')} {lastRefresh.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })}
            </div>
          </div>
        </div>

        <button
          on:click={() => {
            fetchLiveScores();
            countdown = 30;
          }}
          class="px-4 py-2.5 bg-accent/20 text-accent rounded-lg hover:bg-accent/30 flex items-center gap-2 btn-interact touch-target"
        >
          <svg
            class="w-4 h-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0115.5-8.5l4 4M22 12.5a10 10 0 01-15.5 8.5l-4-4"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
          <span class="hidden sm:inline">{$_('live.refresh')}</span>
        </button>
      </div>
    </div>
  </div>

  {#if loading}
    <div class="glass-card p-12 text-center">
      <div
        class="inline-block w-12 h-12 border-4 border-accent border-t-transparent rounded-full animate-spin"
      ></div>
      <p class="mt-4 text-slate-400">{$_('live.loading')}</p>
    </div>
  {:else if error}
    <div class="glass-card p-8 text-center border border-red-500/30">
      <svg
        class="w-12 h-12 mx-auto mb-3 text-red-400"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M15 9l-6 6M9 9l6 6" stroke-linecap="round" />
      </svg>
      <p class="text-red-400">{error}</p>
    </div>
  {:else if liveMatches.length === 0}
    <div class="glass-card p-12 text-center">
      <svg
        class="w-20 h-20 mx-auto mb-4 text-slate-600"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
      >
        <circle cx="12" cy="12" r="10" />
        <path
          d="M12 2a10 10 0 0010 10M2 12a10 10 0 0010 10M12 2c0 2.5-2 4.5-4.5 7S3 14 2 16.5M12 2c0 2.5 2 4.5 4.5 7S21 14 22 16.5"
          stroke-linecap="round"
        />
      </svg>
      <p class="text-xl font-bold mb-2">{$_('live.noMatchesTitle')}</p>
      <p class="text-slate-400 mb-6">
        {$_('live.noMatchesDesc')}
      </p>
      <div class="flex flex-col sm:flex-row justify-center gap-3">
        <Link
          to="/today"
          class="inline-flex items-center justify-center gap-2 px-5 py-3 bg-primary/20 hover:bg-primary/30 text-primary rounded-xl font-medium transition-colors"
        >
          📅 {$_('live.todaysFixtures')}
        </Link>
        <Link
          to="/results"
          class="inline-flex items-center justify-center gap-2 px-5 py-3 bg-white/5 hover:bg-white/10 text-slate-300 rounded-xl font-medium border border-white/10 transition-colors"
        >
          📊 {$_('live.recentResults')}
        </Link>
        <Link
          to="/accumulators"
          class="inline-flex items-center justify-center gap-2 px-5 py-3 bg-white/5 hover:bg-white/10 text-slate-300 rounded-xl font-medium border border-white/10 transition-colors"
        >
          🎲 {$_('live.dailyAccas')}
        </Link>
      </div>
    </div>
  {:else}
    <!-- Grouped by League -->
    <div class="space-y-6 element-enter stagger-1">
      {#each groupedMatches as group}
        {@const leagueId = group.league.id}
        {@const isCollapsed = collapsedLeagues[leagueId]}

        <!-- League Header -->
        <div class="glass-card overflow-hidden">
          <button
            on:click={() => toggleLeague(leagueId)}
            class="w-full p-4 flex items-center justify-between bg-white/5 hover:bg-white/10 transition-colors"
          >
            <div class="flex items-center gap-3">
              <img
                src={group.league.logo}
                alt={group.league.name}
                class="w-8 h-8 object-contain"
                on:error={(e) => {
                  const img = e.target;
                  if (img instanceof HTMLImageElement)
                    img.style.display = "none";
                }}
              />
              <div class="text-left">
                <div class="font-bold text-lg">{group.league.name}</div>
                <div class="text-xs text-slate-400">
                  {group.league.country} • {group.matches.length}
                  {group.matches.length === 1 ? "match" : "matches"}
                </div>
              </div>
            </div>
            <svg
              class="w-5 h-5 text-slate-400 transition-transform {isCollapsed
                ? ''
                : 'rotate-180'}"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>

          <!-- Matches in this League -->
          {#if !isCollapsed}
            <div class="divide-y divide-white/10">
              {#each group.matches as match}
                {@const fixtureId = match.fixture.id}
                {@const status = getStatusBadge(match.fixture.status)}
                {@const pred = predictions[fixtureId]}
                {@const predSummary = getPredictionSummary(pred)}
                {@const homeGoals = match.goals?.home ?? 0}
                {@const awayGoals = match.goals?.away ?? 0}
                {@const predMatching = isPredictionMatching(
                  pred,
                  homeGoals,
                  awayGoals,
                )}
                {@const stats = match.statistics}
                {@const events = match.events || []}

                <div
                  class="p-4 md:p-6 border-l-4 {status.label === 'HT' ||
                  status.label === 'BT'
                    ? 'border-amber-500'
                    : 'border-red-500'}"
                >
                  <!-- Status Badge Row -->
                  <div class="flex items-center justify-between mb-4">
                    <div class="flex items-center gap-3">
                      <!-- Live Indicator & Status -->
                      <div class="flex items-center gap-2">
                        {#if status.label !== "FT" && status.label !== "AET" && status.label !== "PEN"}
                          <span class="relative flex h-2 w-2">
                            <span
                              class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"
                            ></span>
                            <span
                              class="relative inline-flex rounded-full h-2 w-2 bg-red-500"
                            ></span>
                          </span>
                        {/if}
                        <span
                          class="px-2 py-1 rounded text-xs font-bold {status.color} text-white"
                        >
                          {status.label}
                        </span>
                        <span class="text-sm font-mono font-bold text-white"
                          >{status.text}</span
                        >
                      </div>
                    </div>

                    <!-- Prediction Badge & Share -->
                    {#if predSummary}
                      <div class="flex flex-wrap items-center gap-2">
                        <span class="text-xs text-slate-400">{$_('live.predicted')}</span>
                        <span
                          class="px-2 py-1 rounded text-xs font-bold {predMatching ===
                          true
                            ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                            : predMatching === false
                              ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                              : 'bg-slate-500/20 text-slate-400 border border-slate-500/30'}"
                        >
                          {predSummary.label}
                          {predSummary.prob.toFixed(0)}%
                        </span>
                        {#if pred?.data_quality === "limited"}
                          <span
                            class="px-1.5 py-0.5 rounded text-[10px] bg-orange-500/20 text-orange-400 border border-orange-500/30"
                            title="Limited historical data available for these teams"
                          >
                            {$_('live.limitedData')}
                          </span>
                        {/if}
                        <SharePrediction {match} prediction={pred} />
                      </div>
                    {/if}
                  </div>

                  <!-- Teams and Score -->
                  <div
                    class="flex flex-col sm:grid sm:grid-cols-[1fr_auto_1fr] gap-4 items-center mb-4"
                  >
                    <Link
                      to="/team/{match.teams.home.id}?league={match.league.id}"
                      class="flex items-center gap-2 sm:gap-3 justify-end hover:text-accent transition-colors order-1 sm:order-none"
                    >
                      <span
                        class="text-base sm:text-lg font-bold text-right truncate"
                        >{match.teams.home.name}</span
                      >
                      <img
                        src={match.teams.home.logo}
                        alt={match.teams.home.name}
                        class="w-10 h-10 sm:w-12 sm:h-12 flex-shrink-0"
                      />
                    </Link>

                    <!-- Enhanced Score Display -->
                    <div class="text-center order-3 sm:order-none">
                      <div class="relative">
                        <!-- Minute Counter Above Score -->
                        {#if status.label !== "FT" && status.label !== "AET" && status.label !== "HT"}
                          <div
                            class="absolute -top-6 left-1/2 transform -translate-x-1/2"
                          >
                            <span
                              class="text-xs font-bold text-red-400 animate-pulse flex items-center gap-1"
                            >
                              <span class="w-1.5 h-1.5 bg-red-500 rounded-full"
                              ></span>
                              {match.fixture.status.elapsed}'
                            </span>
                          </div>
                        {/if}

                        <div
                          class="text-4xl sm:text-5xl md:text-6xl font-bold px-6 py-3 sm:px-8 sm:py-4 bg-gradient-to-br from-white/10 to-white/5 rounded-xl min-w-[120px] sm:min-w-[160px] border border-white/10 shadow-lg relative overflow-hidden"
                        >
                          <!-- Glow effect for active matches -->
                          {#if status.label !== "FT" && status.label !== "AET"}
                            <div
                              class="absolute inset-0 bg-gradient-to-r from-green-500/10 via-transparent to-red-500/10"
                            ></div>
                          {/if}
                          <span class="relative z-10 tabular-nums"
                            >{homeGoals}</span
                          >
                          <span class="relative z-10 mx-2 text-slate-500"
                            >-</span
                          >
                          <span class="relative z-10 tabular-nums"
                            >{awayGoals}</span
                          >
                        </div>

                        <!-- Half-time score if available and in 2nd half -->
                        {#if match.score?.halftime && (status.label === "2H" || status.label === "FT" || status.label === "ET")}
                          <div class="mt-1 text-xs text-slate-500">
                            HT: {match.score.halftime.home ?? 0} - {match.score
                              .halftime.away ?? 0}
                          </div>
                        {/if}
                      </div>
                    </div>

                    <Link
                      to="/team/{match.teams.away.id}?league={match.league.id}"
                      class="flex items-center gap-2 sm:gap-3 hover:text-accent transition-colors order-2 sm:order-none"
                    >
                      <img
                        src={match.teams.away.logo}
                        alt={match.teams.away.name}
                        class="w-10 h-10 sm:w-12 sm:h-12 flex-shrink-0"
                      />
                      <span class="text-base sm:text-lg font-bold truncate"
                        >{match.teams.away.name}</span
                      >
                    </Link>
                  </div>

                  <!-- Quick Stats Bar (if available) -->
                  {#if stats && stats.length >= 2}
                    {@const homeStats = stats[0]?.statistics || []}
                    {@const awayStats = stats[1]?.statistics || []}
                    {@const possession = homeStats.find(
                      (s) => s.type === "Ball Possession",
                    )}
                    {@const homePoss = possession
                      ? parseInt(possession.value) || 50
                      : 50}
                    {@const awayPoss = 100 - homePoss}
                    {@const homeCorners =
                      homeStats.find((s) => s.type === "Corner Kicks")?.value ??
                      0}
                    {@const awayCorners =
                      awayStats.find((s) => s.type === "Corner Kicks")?.value ??
                      0}
                    {@const homeYellow =
                      homeStats.find((s) => s.type === "Yellow Cards")?.value ??
                      0}
                    {@const awayYellow =
                      awayStats.find((s) => s.type === "Yellow Cards")?.value ??
                      0}
                    {@const homeRed =
                      homeStats.find((s) => s.type === "Red Cards")?.value ?? 0}
                    {@const awayRed =
                      awayStats.find((s) => s.type === "Red Cards")?.value ?? 0}
                    {@const homeShots =
                      homeStats.find((s) => s.type === "Total Shots")?.value ??
                      0}
                    {@const awayShots =
                      awayStats.find((s) => s.type === "Total Shots")?.value ??
                      0}
                    {@const homeShotsOn =
                      homeStats.find((s) => s.type === "Shots on Goal")
                        ?.value ?? 0}
                    {@const awayShotsOn =
                      awayStats.find((s) => s.type === "Shots on Goal")
                        ?.value ?? 0}

                    <div class="mb-4">
                      <!-- Possession Bar -->
                      <div class="flex items-center gap-2 mb-2">
                        <span class="text-xs text-slate-400 w-8"
                          >{homePoss}%</span
                        >
                        <div
                          class="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden flex"
                        >
                          <div
                            class="bg-blue-500 transition-all"
                            style="width: {homePoss}%"
                          ></div>
                          <div
                            class="bg-red-500 transition-all"
                            style="width: {awayPoss}%"
                          ></div>
                        </div>
                        <span class="text-xs text-slate-400 w-8 text-right"
                          >{awayPoss}%</span
                        >
                      </div>
                      <div class="text-center text-xs text-slate-500 mb-3">
                        {$_('live.possession')}
                      </div>

                      <!-- Key Stats Row - Always Visible -->
                      <div
                        class="grid grid-cols-5 gap-2 text-center py-2 px-3 bg-white/5 rounded-lg border border-white/10"
                      >
                        <!-- Corners -->
                        <div class="flex flex-col items-center">
                          <div class="flex items-center gap-1">
                            <span class="text-sm font-bold text-blue-400"
                              >{homeCorners}</span
                            >
                            <span class="text-lg">🚩</span>
                            <span class="text-sm font-bold text-red-400"
                              >{awayCorners}</span
                            >
                          </div>
                          <span class="text-[10px] text-slate-500">Corners</span
                          >
                        </div>
                        <!-- Shots on Target -->
                        <div class="flex flex-col items-center">
                          <div class="flex items-center gap-1">
                            <span class="text-sm font-bold text-blue-400"
                              >{homeShotsOn}</span
                            >
                            <span class="text-lg">🎯</span>
                            <span class="text-sm font-bold text-red-400"
                              >{awayShotsOn}</span
                            >
                          </div>
                          <span class="text-[10px] text-slate-500"
                            >On Target</span
                          >
                        </div>
                        <!-- Total Shots -->
                        <div class="flex flex-col items-center">
                          <div class="flex items-center gap-1">
                            <span class="text-sm font-bold text-blue-400"
                              >{homeShots}</span
                            >
                            <span class="text-lg">⚽</span>
                            <span class="text-sm font-bold text-red-400"
                              >{awayShots}</span
                            >
                          </div>
                          <span class="text-[10px] text-slate-500">Shots</span>
                        </div>
                        <!-- Yellow Cards -->
                        <div class="flex flex-col items-center">
                          <div class="flex items-center gap-1">
                            <span class="text-sm font-bold text-blue-400"
                              >{homeYellow}</span
                            >
                            <span class="text-lg">🟨</span>
                            <span class="text-sm font-bold text-red-400"
                              >{awayYellow}</span
                            >
                          </div>
                          <span class="text-[10px] text-slate-500">Yellows</span
                          >
                        </div>
                        <!-- Red Cards -->
                        <div class="flex flex-col items-center">
                          <div class="flex items-center gap-1">
                            <span class="text-sm font-bold text-blue-400"
                              >{homeRed}</span
                            >
                            <span class="text-lg">🟥</span>
                            <span class="text-sm font-bold text-red-400"
                              >{awayRed}</span
                            >
                          </div>
                          <span class="text-[10px] text-slate-500">Reds</span>
                        </div>
                      </div>

                      <!-- Expandable Stats -->
                      <button
                        on:click={() => toggleStats(fixtureId)}
                        class="w-full mt-2 py-2 text-xs text-slate-400 hover:text-white flex items-center justify-center gap-1"
                      >
                        <span
                          >{expandedStats[fixtureId] ? $_('live.hideStats') : $_('live.showStats')}</span
                        >
                        <svg
                          class="w-4 h-4 transition-transform {expandedStats[
                            fixtureId
                          ]
                            ? 'rotate-180'
                            : ''}"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M19 9l-7 7-7-7"
                          />
                        </svg>
                      </button>

                      {#if expandedStats[fixtureId]}
                        <div
                          class="mt-3 grid grid-cols-3 gap-2 text-center text-sm"
                        >
                          {#each ["Shots on Goal", "Total Shots", "Corner Kicks", "Fouls", "Offsides"] as statType}
                            {@const homeStat = homeStats.find(
                              (s) => s.type === statType,
                            )}
                            {@const awayStat = awayStats.find(
                              (s) => s.type === statType,
                            )}
                            {#if homeStat || awayStat}
                              <div class="text-accent font-bold">
                                {homeStat?.value ?? 0}
                              </div>
                              <div class="text-slate-400 text-xs">
                                {statType === "Shots on Goal"
                                  ? "Shots OT"
                                  : statType === "Total Shots"
                                    ? "Shots"
                                    : statType === "Corner Kicks"
                                      ? "Corners"
                                      : statType}
                              </div>
                              <div class="text-accent font-bold">
                                {awayStat?.value ?? 0}
                              </div>
                            {/if}
                          {/each}
                        </div>
                      {/if}
                    </div>
                  {/if}

                  <!-- Events Timeline -->
                  {#if events.length > 0}
                    <div class="border-t border-white/10 pt-3">
                      <button
                        on:click={() => toggleEvents(fixtureId)}
                        class="w-full py-2 text-xs text-slate-400 hover:text-white flex items-center justify-center gap-1"
                      >
                        <svg
                          class="w-4 h-4 inline text-yellow-400"
                          viewBox="0 0 24 24"
                          fill="currentColor"
                        >
                          <path d="M13 2L3 14h8l-1 8 10-12h-8l1-8z" />
                        </svg>
                        <span class="ml-1"
                          >{events.length}
                          {events.length === 1 ? $_('live.eventSingular') : $_('live.eventPlural')}</span
                        >
                        <svg
                          class="w-4 h-4 transition-transform {expandedEvents[
                            fixtureId
                          ]
                            ? 'rotate-180'
                            : ''}"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M19 9l-7 7-7-7"
                          />
                        </svg>
                      </button>

                      {#if expandedEvents[fixtureId]}
                        <div class="mt-2 space-y-2 max-h-48 overflow-y-auto">
                          {#each events.slice().reverse().slice(0, 10) as event}
                            {@const isHome =
                              event.team?.id === match.teams.home.id}
                            <div
                              class="flex items-center gap-2 text-sm {isHome
                                ? 'justify-start'
                                : 'justify-end'}"
                            >
                              {#if isHome}
                                <span class="text-slate-500 font-mono w-8"
                                  >{event.time?.elapsed}'</span
                                >
                                <span
                                  >{@html getEventIcon(
                                    event.type,
                                    event.detail,
                                  )}</span
                                >
                                <span class="text-slate-300"
                                  >{event.player?.name || event.detail}</span
                                >
                              {:else}
                                <span class="text-slate-300"
                                  >{event.player?.name || event.detail}</span
                                >
                                <span
                                  >{@html getEventIcon(
                                    event.type,
                                    event.detail,
                                  )}</span
                                >
                                <span
                                  class="text-slate-500 font-mono w-8 text-right"
                                  >{event.time?.elapsed}'</span
                                >
                              {/if}
                            </div>
                          {/each}
                        </div>
                      {:else}
                        <!-- Show last event preview -->
                        {@const lastEvent = events[events.length - 1]}
                        {#if lastEvent}
                          <div class="text-center text-sm text-slate-400">
                            <span
                              >{@html getEventIcon(
                                lastEvent.type,
                                lastEvent.detail,
                              )}</span
                            >
                            <span class="ml-1"
                              >{lastEvent.time?.elapsed}' - {lastEvent.player
                                ?.name || lastEvent.detail}</span
                            >
                          </div>
                        {/if}
                      {/if}
                    </div>
                  {/if}
                </div>
              {/each}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>
