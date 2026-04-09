<script>
  import { onMount, onDestroy } from "svelte";
  import { Link, navigate } from "svelte-routing";
  import { _, locale } from "svelte-i18n";
  import { API_URL, ML_API_URL } from "../config.js";
  import SkeletonLoader from "../components/SkeletonLoader.svelte";
  import SearchBar from "../components/SearchBar.svelte";
  import ConfidenceBadge from "../components/ConfidenceBadge.svelte";
  import AccuracyTracker from "../components/AccuracyTracker.svelte";
  import SharePrediction from "../components/SharePrediction.svelte";
  import ReminderButton from "../components/ReminderButton.svelte";
  import { compareStore } from "../services/compareStore.js";
  import { getCurrentSeason } from "../services/season.js";
  import { initReminders } from "../services/remindersStore.js";
  import { getSavedLeague, saveLeague } from "../services/preferences.js";
  import { LEAGUES } from "../services/leagues.js";
  import SEOHead from "../components/SEOHead.svelte";
  import { generateFixturesSEO } from "../services/seoService.js";
  import { formatDate } from "../lib/i18n/format.js";

  let seoData;
  $: seoData = generateFixturesSEO($locale);

  // Use reactive auto-subscription ($ prefix) - automatically unsubscribes
  $: compareFixtures = $compareStore?.fixtures || [];
  $: compareLeagues = $compareStore?.fixtureLeagues || {};

  function toggleCompare(fixtureId) {
    compareStore.addFixture(fixtureId, selectedLeague);
  }

  function isInCompare(fixtureId) {
    return compareFixtures.includes(fixtureId);
  }

  // Collapsible league tier state
  let collapsedTiers = { 0: false, 1: false, 2: true, 3: true }; // European & Top open by default

  function toggleTier(tier) {
    collapsedTiers[tier] = !collapsedTiers[tier];
    collapsedTiers = { ...collapsedTiers };
  }

  // Date navigation - initialize from URL params
  let selectedDate = new Date();
  let dateOffset = 0; // days from today (start from Today)
  let showAllDates = false; // Default: show today's fixtures

  // Read initial state from URL query params
  function initFromUrl() {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const dateParam = params.get("date");
      if (dateParam === "today" || !dateParam) {
        // Default to today
        showAllDates = false;
        dateOffset = 0;
        selectedDate = getUKDate();
      } else if (dateParam) {
        showAllDates = false;
        selectedDate = new Date(dateParam);
        const today = getUKDate();
        today.setHours(0, 0, 0, 0);
        selectedDate.setHours(0, 0, 0, 0);
        dateOffset = Math.round(
          (selectedDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24),
        );
      }
      const leagueParam = params.get("league");
      if (leagueParam) {
        selectedLeague = parseInt(leagueParam, 10) || 39;
      }
    }
  }

  // Update URL when filter changes (without full page reload)
  function updateUrl() {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams();
      params.set("league", selectedLeague.toString());
      if (!showAllDates) {
        if (dateOffset === 0) {
          params.set("date", "today");
        } else {
          const targetYear = selectedDate.getFullYear();
          const targetMonth = String(selectedDate.getMonth() + 1).padStart(
            2,
            "0",
          );
          const targetDay = String(selectedDate.getDate()).padStart(2, "0");
          params.set("date", `${targetYear}-${targetMonth}-${targetDay}`);
        }
      }
      const newUrl = `${window.location.pathname}?${params.toString()}`;
      window.history.replaceState({}, "", newUrl);
    }
  }

  function formatDateNav(date) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const targetDate = new Date(date);
    targetDate.setHours(0, 0, 0, 0);
    const diff = Math.round(
      (targetDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24),
    );

    if (diff === 0) return $_("common.today");
    if (diff === 1) return $_("common.tomorrow");
    if (diff === -1) return $_("common.yesterday");
    return formatDate(targetDate, $locale, {
      weekday: "short",
      day: "numeric",
      month: "short",
    });
  }

  async function changeDate(offset) {
    dateOffset = offset;
    showAllDates = false;

    const ukBase = getUKDate();
    ukBase.setHours(0, 0, 0, 0);
    ukBase.setDate(ukBase.getDate() + offset);
    selectedDate = ukBase;

    updateUrl();

    const targetYear = selectedDate.getFullYear();
    const targetMonth = String(selectedDate.getMonth() + 1).padStart(2, "0");
    const targetDay = String(selectedDate.getDate()).padStart(2, "0");
    const targetDateStr = `${targetYear}-${targetMonth}-${targetDay}`;
    await loadFixtures(targetDateStr);
  }

  function showAll() {
    showAllDates = true;
    dateOffset = 0;
    selectedDate = getUKDate();
    updateUrl();
    loadFixtures();
  }

  // All supported leagues
  const leagues = LEAGUES;

  // Create league map for quick lookup
  const leaguesMap = {};
  leagues.forEach((l) => (leaguesMap[l.id] = l));

  let selectedLeague = getSavedLeague(39); // Default: Premier League (persisted)
  let season = getCurrentSeason();
  let fixtures = [];
  let deduplicatedFixtures = [];
  let loading = false;
  let showLeagueSelector = false;
  let fixturesRequestToken = 0;

  // Predictions state - on demand
  let predictions = {}; // fixture_id -> prediction data
  let loadingPredictions = {}; // fixture_id -> boolean
  let predictionRequestTokens = {}; // fixture_id -> request token
  let searchQuery = "";

  // Auto-load predictions setting
  let autoLoadPredictions = true;

  function filterByDate(fixtureList) {
    if (showAllDates) return fixtureList;

    const targetYear = selectedDate.getFullYear();
    const targetMonth = String(selectedDate.getMonth() + 1).padStart(2, "0");
    const targetDay = String(selectedDate.getDate()).padStart(2, "0");
    const targetDateStr = `${targetYear}-${targetMonth}-${targetDay}`;

    return fixtureList.filter((fixture) => {
      const fixtureDate = new Date(fixture.fixture.date);
      const ukDateStr = new Intl.DateTimeFormat("en-CA", {
        timeZone: "Europe/London",
      }).format(fixtureDate);
      return ukDateStr === targetDateStr;
    });
  }

  // Reactive filtered fixtures
  $: displayedFixtures = filterByDate(deduplicatedFixtures);

  // UK timezone helpers
  function getUKDate() {
    const now = new Date();
    const ukTime = new Date(
      now.toLocaleString("en-US", { timeZone: "Europe/London" }),
    );
    return ukTime;
  }

  function formatUKDate(date) {
    return formatDate(date, $locale, {
      timeZone: "Europe/London",
      weekday: "short",
      day: "numeric",
      month: "short",
    });
  }

  function formatUKTime(date) {
    return formatDate(date, $locale, {
      timeZone: "Europe/London",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function getUKMidnightInfo() {
    const ukNow = getUKDate();
    const hours = ukNow.getHours();
    const mins = ukNow.getMinutes();
    const secs = ukNow.getSeconds();
    return `${hours.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")} UK`;
  }

  $: currentLeague = leaguesMap[selectedLeague] || leagues[0];
  let ukTimeNow = getUKMidnightInfo();
  let clockInterval;

  // Deduplicate fixtures - one game per team
  function deduplicateFixtures(fixtureList) {
    const seenTeams = new Set();
    const result = [];

    const sorted = [...fixtureList].sort(
      (a, b) =>
        new Date(a.fixture.date).getTime() - new Date(b.fixture.date).getTime(),
    );

    for (const fixture of sorted) {
      const homeId = fixture.teams.home.id;
      const awayId = fixture.teams.away.id;

      if (!seenTeams.has(homeId) && !seenTeams.has(awayId)) {
        result.push(fixture);
        seenTeams.add(homeId);
        seenTeams.add(awayId);
      }
    }

    return result;
  }

  async function loadFixtures(date = null) {
    loading = true;
    fixtures = [];
    deduplicatedFixtures = [];
    predictions = {};
    const requestId = ++fixturesRequestToken;

    try {
      // When a specific date is selected, fetch ALL leagues
      // When no date (showing next games), fetch only selected league
      if (date) {
        // Fetch all leagues in parallel for the selected date
        const allLeagueIds = leagues.map((l) => l.id);
        const fetchPromises = allLeagueIds.map(async (leagueId) => {
          const url = `${API_URL}/api/fixtures?league=${leagueId}&season=${season}&date=${date}`;
          try {
            const res = await fetch(url);
            const data = await res.json();
            if (data.response && Array.isArray(data.response)) {
              return data.response;
            }
            return [];
          } catch (e) {
            console.warn(`Failed to fetch league ${leagueId}:`, e);
            return [];
          }
        });

        const allResults = await Promise.all(fetchPromises);
        const allFixtures = allResults.flat();

        if (requestId === fixturesRequestToken) {
          // Show all games for the date (including finished)
          fixtures = allFixtures;
          deduplicatedFixtures = deduplicateFixtures(fixtures);

          // Auto-load predictions for first 4 fixtures if enabled
          if (autoLoadPredictions && deduplicatedFixtures.length > 0) {
            const topFixtures = deduplicatedFixtures.slice(0, 4);
            topFixtures.forEach((fixture) => {
              loadPrediction(fixture.fixture.id);
            });
          }
        }
      } else {
        // No date selected - fetch next games for selected league only
        const url = `${API_URL}/api/fixtures?league=${selectedLeague}&season=${season}&next=40`;
        const res = await fetch(url);
        const data = await res.json();

        if (
          requestId === fixturesRequestToken &&
          data.response &&
          Array.isArray(data.response)
        ) {
          fixtures = data.response.filter(
            (f) =>
              f.fixture.status?.short === "NS" ||
              f.fixture.status?.short === "TBD",
          );
          deduplicatedFixtures = deduplicateFixtures(fixtures);

          // Auto-load predictions for first 4 fixtures if enabled
          if (autoLoadPredictions && deduplicatedFixtures.length > 0) {
            const topFixtures = deduplicatedFixtures.slice(0, 4);
            topFixtures.forEach((fixture) => {
              loadPrediction(fixture.fixture.id);
            });
          }
        }
      }
    } catch (e) {
      if (requestId === fixturesRequestToken) {
        console.error("Error loading fixtures:", e);
      }
    } finally {
      if (requestId === fixturesRequestToken) {
        loading = false;
      }
    }
  }

  async function changeLeague(leagueId) {
    selectedLeague = leagueId;
    saveLeague(leagueId);
    showLeagueSelector = false;
    updateUrl();

    if (!showAllDates && selectedDate) {
      const targetYear = selectedDate.getFullYear();
      const targetMonth = String(selectedDate.getMonth() + 1).padStart(2, "0");
      const targetDay = String(selectedDate.getDate()).padStart(2, "0");
      const targetDateStr = `${targetYear}-${targetMonth}-${targetDay}`;
      await loadFixtures(targetDateStr);
    } else {
      await loadFixtures();
    }
  }

  async function loadPrediction(fixtureId) {
    if (predictions[fixtureId] || loadingPredictions[fixtureId]) {
      return;
    }

    loadingPredictions[fixtureId] = true;
    loadingPredictions = { ...loadingPredictions };
    const requestId = (predictionRequestTokens[fixtureId] || 0) + 1;
    predictionRequestTokens[fixtureId] = requestId;
    predictionRequestTokens = { ...predictionRequestTokens };

    try {
      const res = await fetch(
        `${ML_API_URL}/api/prediction/${fixtureId}?league=${selectedLeague}&season=${season}`,
      );

      if (res.ok) {
        const data = await res.json();
        if (predictionRequestTokens[fixtureId] === requestId) {
          predictions[fixtureId] = data.prediction;
          predictions = { ...predictions };
        }
      }
    } catch (e) {
      console.error(`Error loading prediction for ${fixtureId}:`, e);
    } finally {
      if (predictionRequestTokens[fixtureId] === requestId) {
        loadingPredictions[fixtureId] = false;
        loadingPredictions = { ...loadingPredictions };
      }
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

  $: filteredFixtures = displayedFixtures.filter((fixture) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const home = fixture.teams.home.name.toLowerCase();
    const away = fixture.teams.away.name.toLowerCase();
    return home.includes(q) || away.includes(q);
  });

  // Group fixtures by league when showing a specific date
  $: fixturesByLeague = (() => {
    if (showAllDates) return null; // Don't group when showing "All"

    const grouped = {};
    for (const fixture of filteredFixtures) {
      const leagueId = fixture.league.id;
      if (!grouped[leagueId]) {
        grouped[leagueId] = {
          league: leaguesMap[leagueId] || {
            id: leagueId,
            name: fixture.league.name,
            emoji: "⚽",
            country: fixture.league.country,
          },
          fixtures: [],
        };
      }
      grouped[leagueId].fixtures.push(fixture);
    }

    // Sort by tier then name
    return Object.values(grouped).sort((a, b) => {
      const tierA = a.league.tier ?? 99;
      const tierB = b.league.tier ?? 99;
      if (tierA !== tierB) return tierA - tierB;
      return a.league.name.localeCompare(b.league.name);
    });
  })();

  // Check if we're in "all leagues" mode (date selected)
  $: isAllLeaguesMode = !showAllDates && Boolean(selectedDate);

  function handleClickOutside(event) {
    if (showLeagueSelector && !event.target.closest(".league-selector")) {
      showLeagueSelector = false;
    }
  }

  onMount(() => {
    // Initialize state from URL params (for back button support)
    initFromUrl();

    // Initialize reminders (schedule any pending notifications)
    initReminders();

    // Start live UK clock with seconds
    clockInterval = setInterval(() => {
      ukTimeNow = getUKMidnightInfo();
    }, 1000);

    // Load fixtures based on initial state
    if (!showAllDates) {
      const targetYear = selectedDate.getFullYear();
      const targetMonth = String(selectedDate.getMonth() + 1).padStart(2, "0");
      const targetDay = String(selectedDate.getDate()).padStart(2, "0");
      const targetDateStr = `${targetYear}-${targetMonth}-${targetDay}`;
      loadFixtures(targetDateStr);
    } else {
      loadFixtures();
    }
  });

  onDestroy(() => {
    if (clockInterval) {
      clearInterval(clockInterval);
    }
  });
</script>

<svelte:window on:click={handleClickOutside} />

<SEOHead data={seoData} />

<div class="page-enter flex flex-col lg:flex-row gap-4 lg:gap-8">
  <!-- Mobile League Selector Button -->
  <div class="lg:hidden league-selector element-enter">
    <button
      on:click={() => (showLeagueSelector = !showLeagueSelector)}
      class="w-full glass-card p-4 flex items-center justify-between touch-target btn-interact"
    >
      <div class="flex items-center gap-3">
        <span class="text-xl">{currentLeague.emoji}</span>
        <div>
          <div class="font-bold">{currentLeague.name}</div>
          <div class="text-xs text-slate-400">One game per team • UK Time</div>
        </div>
      </div>
      <svg
        class="w-5 h-5 text-slate-400 transition-transform {showLeagueSelector
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

    <!-- Mobile League Dropdown -->
    {#if showLeagueSelector}
      <div class="glass-card mt-2 p-2 max-h-80 overflow-y-auto">
        <!-- European Competitions -->
        <div class="text-xs text-slate-400 px-2 py-1 font-bold">
          EUROPEAN COMPETITIONS
        </div>
        {#each leagues.filter((l) => l.tier === 0) as league}
          <button
            class="w-full text-left px-3 py-3 rounded-lg text-sm transition-colors flex items-center gap-3 touch-target {selectedLeague ===
            league.id
              ? 'bg-accent text-white font-bold'
              : 'text-slate-300 hover:bg-white/10'}"
            on:click={() => changeLeague(league.id)}
          >
            <span>{league.emoji}</span>
            <span class="flex-1">{league.name}</span>
          </button>
        {/each}

        <div class="text-xs text-slate-400 px-2 py-1 font-bold mt-3">
          {$_("fixtures.topLeagues")}
        </div>
        {#each leagues.filter((l) => l.tier === 1) as league}
          <button
            class="w-full text-left px-3 py-3 rounded-lg text-sm transition-colors flex items-center gap-3 touch-target {selectedLeague ===
            league.id
              ? 'bg-accent text-white font-bold'
              : 'text-slate-300 hover:bg-white/10'}"
            on:click={() => changeLeague(league.id)}
          >
            <span>{league.emoji}</span>
            <span class="flex-1">{league.name}</span>
          </button>
        {/each}

        <div class="text-xs text-slate-400 px-2 py-1 font-bold mt-3">
          MORE LEAGUES
        </div>
        {#each leagues.filter((l) => l.tier === 2) as league}
          <button
            class="w-full text-left px-3 py-3 rounded-lg text-sm transition-colors flex items-center gap-3 touch-target {selectedLeague ===
            league.id
              ? 'bg-accent text-white font-bold'
              : 'text-slate-300 hover:bg-white/10'}"
            on:click={() => changeLeague(league.id)}
          >
            <span>{league.emoji}</span>
            <span class="flex-1">{league.name}</span>
          </button>
        {/each}

        <div class="text-xs text-slate-400 px-2 py-1 font-bold mt-3">
          {$_("fixtures.domesticCups")}
        </div>
        {#each leagues.filter((l) => l.tier === 3) as league}
          <button
            class="w-full text-left px-3 py-3 rounded-lg text-sm transition-colors flex items-center gap-3 touch-target {selectedLeague ===
            league.id
              ? 'bg-accent text-white font-bold'
              : 'text-slate-300 hover:bg-white/10'}"
            on:click={() => changeLeague(league.id)}
          >
            <span>{league.emoji}</span>
            <span class="flex-1">{league.name}</span>
          </button>
        {/each}

        <div class="text-xs text-slate-400 px-2 py-1 font-bold mt-3">
          FRIENDLIES
        </div>
        {#each leagues.filter((l) => l.tier === 4) as league}
          <button
            class="w-full text-left px-3 py-3 rounded-lg text-sm transition-colors flex items-center gap-3 touch-target {selectedLeague ===
            league.id
              ? 'bg-accent text-white font-bold'
              : 'text-slate-300 hover:bg-white/10'}"
            on:click={() => changeLeague(league.id)}
          >
            <span>{league.emoji}</span>
            <span class="flex-1">{league.name}</span>
          </button>
        {/each}
      </div>
    {/if}
  </div>
  <aside
    class="hidden lg:block w-64 flex-shrink-0 league-selector element-enter stagger-1"
  >
    <div
      class="glass-card p-4 sticky top-24 max-h-[calc(100vh-6rem)] overflow-y-auto"
    >
      <h3 class="text-lg font-bold mb-4 text-slate-300">
        {$_("fixtures.selectLeague")}
      </h3>
      <p class="text-xs text-slate-500 mb-4">
        🕐 {$_("fixtures.currentUKTime")}: {ukTimeNow}
      </p>

      <!-- Auto-load toggle -->
      <label class="flex items-center gap-2 mb-4 cursor-pointer group">
        <input
          type="checkbox"
          bind:checked={autoLoadPredictions}
          class="w-4 h-4 rounded bg-white/10 border-white/20 text-accent focus:ring-accent"
        />
        <span
          class="text-xs text-slate-400 group-hover:text-slate-300 transition-colors"
        >
          {$_("fixtures.autoLoadPredictions")}
        </span>
      </label>

      <div class="space-y-2">
        <!-- European Competitions -->
        <div>
          <button
            on:click={() => toggleTier(0)}
            class="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-yellow-400 uppercase tracking-wider hover:bg-white/5 rounded-lg transition-colors"
          >
            <span>European</span>
            <svg
              class="w-4 h-4 transition-transform {collapsedTiers[0]
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
          {#if !collapsedTiers[0]}
            <div class="space-y-1 mt-1">
              {#each leagues.filter((l) => l.tier === 0) as league}
                <button
                  class="w-full text-left px-3 py-2 rounded-md text-sm transition-colors {selectedLeague ===
                  league.id
                    ? 'bg-accent text-primary font-bold'
                    : 'text-slate-400 hover:bg-white/5 hover:text-white'}"
                  on:click={() => changeLeague(league.id)}
                >
                  <div class="flex justify-between items-center">
                    <span>{league.name}</span>
                    <span class="text-xs opacity-60">{league.emoji}</span>
                  </div>
                </button>
              {/each}
            </div>
          {/if}
        </div>

        <!-- Top Leagues -->
        <div>
          <button
            on:click={() => toggleTier(1)}
            class="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-accent uppercase tracking-wider hover:bg-white/5 rounded-lg transition-colors border-t border-white/10 pt-3"
          >
            <span>{$_("fixtures.topLeagues")}</span>
            <svg
              class="w-4 h-4 transition-transform {collapsedTiers[1]
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
          {#if !collapsedTiers[1]}
            <div class="space-y-1 mt-1">
              {#each leagues.filter((l) => l.tier === 1) as league}
                <button
                  class="w-full text-left px-3 py-2 rounded-md text-sm transition-colors {selectedLeague ===
                  league.id
                    ? 'bg-accent text-primary font-bold'
                    : 'text-slate-400 hover:bg-white/5 hover:text-white'}"
                  on:click={() => changeLeague(league.id)}
                >
                  <div class="flex justify-between items-center">
                    <span>{league.name}</span>
                    <span class="text-xs opacity-60">{league.emoji}</span>
                  </div>
                </button>
              {/each}
            </div>
          {/if}
        </div>

        <!-- More Leagues -->
        <div>
          <button
            on:click={() => toggleTier(2)}
            class="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-emerald-400 uppercase tracking-wider hover:bg-white/5 rounded-lg transition-colors border-t border-white/10 pt-3"
          >
            <span>{$_("fixtures.champLeagues")}</span>
            <svg
              class="w-4 h-4 transition-transform {collapsedTiers[2]
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
          {#if !collapsedTiers[2]}
            <div class="space-y-1 mt-1">
              {#each leagues.filter((l) => l.tier === 2) as league}
                <button
                  class="w-full text-left px-3 py-2 rounded-md text-sm transition-colors {selectedLeague ===
                  league.id
                    ? 'bg-accent text-primary font-bold'
                    : 'text-slate-400 hover:bg-white/5 hover:text-white'}"
                  on:click={() => changeLeague(league.id)}
                >
                  <div class="flex justify-between items-center">
                    <span>{league.name}</span>
                    <span class="text-xs opacity-60">{league.emoji}</span>
                  </div>
                </button>
              {/each}
            </div>
          {/if}
        </div>

        <!-- Domestic Cups -->
        <div>
          <button
            on:click={() => toggleTier(3)}
            class="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-orange-400 uppercase tracking-wider hover:bg-white/5 rounded-lg transition-colors border-t border-white/10 pt-3"
          >
            <span>{$_("fixtures.domesticCups")}</span>
            <svg
              class="w-4 h-4 transition-transform {collapsedTiers[3]
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
          {#if !collapsedTiers[3]}
            <div class="space-y-1 mt-1">
              {#each leagues.filter((l) => l.tier === 3) as league}
                <button
                  class="w-full text-left px-3 py-2 rounded-md text-sm transition-colors {selectedLeague ===
                  league.id
                    ? 'bg-accent text-primary font-bold'
                    : 'text-slate-400 hover:bg-white/5 hover:text-white'}"
                  on:click={() => changeLeague(league.id)}
                >
                  <div class="flex justify-between items-center">
                    <span>{league.name}</span>
                    <span class="text-xs opacity-60">{league.emoji}</span>
                  </div>
                </button>
              {/each}
            </div>
          {/if}
        </div>
      </div>
    </div>
  </aside>

  <!-- Main Content -->
  <div class="flex-grow element-enter stagger-2">
    <!-- Date Navigation -->
    <div
      class="flex items-center gap-2 mb-4 overflow-x-auto pb-2 scrollbar-hide"
    >
      {#each [0, 1, 2, 3, 4, 5, 6] as offset}
        {@const date = new Date()}
        {@const _ = date.setDate(date.getDate() + offset)}
        <button
          on:click={() => changeDate(offset)}
          class="px-4 py-2 rounded-lg text-sm font-medium transition-all flex-shrink-0 {!showAllDates &&
          dateOffset === offset
            ? 'bg-accent text-white shadow-lg shadow-accent/20'
            : 'bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white'}"
        >
          {formatDateNav(date)}
        </button>
      {/each}
    </div>

    <div class="flex flex-col gap-3 mb-4 lg:mb-6">
      <div class="flex items-center justify-between gap-3">
        <div>
          {#if isAllLeaguesMode}
            <h2 class="text-xl lg:text-2xl font-bold">
              ⚽ {$_("fixtures.allLeagues")} - {formatDateNav(selectedDate)}
            </h2>
            <p class="text-sm text-slate-400">
              {filteredFixtures.length}
              {$_("fixtures.matchesAcrossLeagues", {
                values: { count: fixturesByLeague?.length || 0 },
              })}
            </p>
          {:else}
            <h2 class="text-xl lg:text-2xl font-bold">
              {currentLeague.emoji}
              {currentLeague.name}
              {$_("fixtures.title")}
            </h2>
            <p class="text-sm text-slate-400">
              {$_("fixtures.onePerTeam")}
            </p>
          {/if}
        </div>
        <button
          on:click={() =>
            isAllLeaguesMode
              ? loadFixtures(selectedDate.toISOString().split("T")[0])
              : loadFixtures()}
          class="p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
          title="Refresh fixtures"
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
      <SearchBar bind:searchQuery {selectedLeague} />
    </div>

    {#if isAllLeaguesMode && fixturesByLeague && fixturesByLeague.length > 0}
      <div class="glass-card p-3 mb-4">
        <div
          class="text-xs text-slate-400 mb-2 font-semibold uppercase tracking-wide"
        >
          Jump to league
        </div>
        <div class="flex flex-wrap gap-2">
          {#each fixturesByLeague as group (group.league.id)}
            <a
              href={`#league-${group.league.id}`}
              class="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 transition-colors text-sm text-slate-200"
            >
              <span class="mr-1">{group.league.emoji || "⚽"}</span>
              <span>{group.league.name}</span>
            </a>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Info Banner -->
    <div
      class="bg-accent/10 border border-accent/30 rounded-lg p-3 mb-4 text-sm"
    >
      <div class="flex items-start gap-2">
        <span class="text-accent">🎯</span>
        <p class="text-slate-300">
          <strong class="text-white">{$_("fixtures.smartFixtures")}:</strong>
          {$_("fixtures.smartFixturesDesc")}
        </p>
      </div>
    </div>

    <!-- Accuracy Tracker -->
    <div class="mb-4">
      <AccuracyTracker league={selectedLeague} compact={true} />
    </div>

    {#if loading}
      <!-- Skeleton Loading -->
      <div class="grid gap-4 md:grid-cols-2">
        {#each Array(6) as _}
          <SkeletonLoader type="fixture" />
        {/each}
      </div>
    {:else if filteredFixtures.length > 0}
      {#if isAllLeaguesMode && fixturesByLeague}
        <!-- Grouped by League View -->
        {#each fixturesByLeague as group (group.league.id)}
          <div class="mb-6" id={`league-${group.league.id}`}>
            <h3
              class="text-lg font-bold mb-3 flex items-center gap-2 text-slate-200"
            >
              <span>{group.league.emoji || "⚽"}</span>
              <span>{group.league.name}</span>
              <span class="text-sm font-normal text-slate-400"
                >({group.fixtures.length})</span
              >
            </h3>
            <div class="grid gap-4 md:grid-cols-2">
              {#each group.fixtures as fixture (fixture.fixture.id)}
                {@const fixtureId = fixture.fixture.id}
                {@const pred = predictions[fixtureId]}
                {@const summary = getPredictionSummary(pred)}
                {@const fixtureLeague =
                  leaguesMap[fixture.league.id] || group.league}

                <div
                  class="glass-card p-4 relative overflow-hidden group fixture-card"
                >
                  <!-- Compare Button (top right) -->
                  <button
                    on:click|stopPropagation={() => toggleCompare(fixtureId)}
                    class="absolute top-2 right-2 p-1.5 rounded-lg transition-all z-10 {isInCompare(
                      fixtureId,
                    )
                      ? 'bg-accent text-white'
                      : 'bg-white/10 text-slate-400 opacity-0 group-hover:opacity-100 hover:bg-white/20'}"
                    title={isInCompare(fixtureId)
                      ? "Remove from compare"
                      : "Add to compare"}
                  >
                    ⚖️
                  </button>

                  <!-- Match Time Header -->
                  <div class="flex items-center justify-between mb-3 pr-8">
                    <span class="text-xs text-slate-400">
                      {formatUKDate(fixture.fixture.date)}
                    </span>
                    <span class="text-sm text-accent font-mono font-bold">
                      {formatUKTime(fixture.fixture.date)} UK
                    </span>
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
                        <span class="text-xs text-slate-400">AI Prediction</span
                        >
                        <div class="flex items-center gap-2">
                          <ConfidenceBadge
                            confidence={summary.prob / 100}
                            size="sm"
                            showLabel={false}
                          />
                          <ReminderButton
                            {fixtureId}
                            homeTeam={fixture.teams.home.name}
                            awayTeam={fixture.teams.away.name}
                            kickoffTime={fixture.fixture.date}
                            leagueName={fixtureLeague.name}
                            compact={true}
                          />
                          <SharePrediction
                            match={{
                              teams: fixture.teams,
                              league: {
                                id: fixtureLeague.id,
                                name: fixtureLeague.name,
                              },
                            }}
                            prediction={pred}
                          />
                        </div>
                      </div>
                      <div
                        class="flex justify-between items-center text-xs mb-2"
                      >
                        <span
                          class="font-medium {summary.winner === 'home'
                            ? 'text-emerald-400'
                            : summary.winner === 'away'
                              ? 'text-rose-400'
                              : 'text-slate-300'}">{summary.label}</span
                        >
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
                          title="Home: {(pred.home_win_prob * 100).toFixed(1)}%"
                        ></div>
                        <div
                          class="bg-slate-400 transition-all"
                          style="width: {pred.draw_prob * 100}%"
                          title="Draw: {(pred.draw_prob * 100).toFixed(1)}%"
                        ></div>
                        <div
                          class="bg-red-500 transition-all"
                          style="width: {pred.away_win_prob * 100}%"
                          title="Away: {(pred.away_win_prob * 100).toFixed(1)}%"
                        ></div>
                      </div>
                      <div
                        class="flex justify-between text-xs mt-1 text-slate-500"
                      >
                        <span>H: {(pred.home_win_prob * 100).toFixed(0)}%</span>
                        <span>D: {(pred.draw_prob * 100).toFixed(0)}%</span>
                        <span>A: {(pred.away_win_prob * 100).toFixed(0)}%</span>
                      </div>
                      <Link
                        to={`/prediction/${fixtureId}?league=${fixtureLeague.id}&season=${season}`}
                        class="view-analysis-btn"
                      >
                        <span>🔮</span>
                        <span>{$_("prediction.viewFullAnalysis")}</span>
                        <svg
                          class="arrow-icon"
                          width="16"
                          height="16"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          stroke-width="2"
                        >
                          <path d="M5 12h14M12 5l7 7-7 7" />
                        </svg>
                      </Link>
                    </div>
                  {:else}
                    <button
                      on:click={() => loadPrediction(fixtureId)}
                      disabled={loadingPredictions[fixtureId]}
                      class="w-full py-3 bg-accent/20 hover:bg-accent/30 text-accent rounded-lg font-medium text-sm flex items-center justify-center gap-2 disabled:opacity-50 btn-interact"
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
      {:else}
        <!-- Single League View (original) -->
        <div class="grid gap-4 md:grid-cols-2">
          {#each filteredFixtures as fixture (fixture.fixture.id)}
            {@const fixtureId = fixture.fixture.id}
            {@const pred = predictions[fixtureId]}
            {@const summary = getPredictionSummary(pred)}

            <div
              class="glass-card p-4 relative overflow-hidden group fixture-card"
            >
              <!-- Compare Button (top right) -->
              <button
                on:click|stopPropagation={() => toggleCompare(fixtureId)}
                class="absolute top-2 right-2 p-1.5 rounded-lg transition-all z-10 {isInCompare(
                  fixtureId,
                )
                  ? 'bg-accent text-white'
                  : 'bg-white/10 text-slate-400 opacity-0 group-hover:opacity-100 hover:bg-white/20'}"
                title={isInCompare(fixtureId)
                  ? "Remove from compare"
                  : "Add to compare"}
              >
                ⚖️
              </button>

              <!-- Match Time Header -->
              <div class="flex items-center justify-between mb-3 pr-8">
                <span class="text-xs text-slate-400">
                  {formatUKDate(fixture.fixture.date)}
                </span>
                <span class="text-sm text-accent font-mono font-bold">
                  {formatUKTime(fixture.fixture.date)} UK
                </span>
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
                <!-- Show prediction result with confidence badge -->
                <div
                  class="bg-gradient-to-r from-accent/10 to-purple-500/10 rounded-lg p-3 border border-accent/20"
                >
                  <div class="flex justify-between items-center mb-2">
                    <span class="text-xs text-slate-400">AI Prediction</span>
                    <div class="flex items-center gap-2">
                      <ConfidenceBadge
                        confidence={summary.prob / 100}
                        size="sm"
                        showLabel={false}
                      />
                      <ReminderButton
                        {fixtureId}
                        homeTeam={fixture.teams.home.name}
                        awayTeam={fixture.teams.away.name}
                        kickoffTime={fixture.fixture.date}
                        leagueName={currentLeague.name}
                        compact={true}
                      />
                      <SharePrediction
                        match={{
                          teams: fixture.teams,
                          league: {
                            id: selectedLeague,
                            name: currentLeague.name,
                          },
                        }}
                        prediction={pred}
                      />
                    </div>
                  </div>
                  <div class="flex justify-between items-center text-xs mb-2">
                    <span
                      class="font-medium {summary.winner === 'home'
                        ? 'text-emerald-400'
                        : summary.winner === 'away'
                          ? 'text-rose-400'
                          : 'text-slate-300'}">{summary.label}</span
                    >
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
                      title="Home: {(pred.home_win_prob * 100).toFixed(1)}%"
                    ></div>
                    <div
                      class="bg-slate-400 transition-all"
                      style="width: {pred.draw_prob * 100}%"
                      title="Draw: {(pred.draw_prob * 100).toFixed(1)}%"
                    ></div>
                    <div
                      class="bg-red-500 transition-all"
                      style="width: {pred.away_win_prob * 100}%"
                      title="Away: {(pred.away_win_prob * 100).toFixed(1)}%"
                    ></div>
                  </div>
                  <div class="flex justify-between text-xs mt-1 text-slate-500">
                    <span>H: {(pred.home_win_prob * 100).toFixed(0)}%</span>
                    <span>D: {(pred.draw_prob * 100).toFixed(0)}%</span>
                    <span>A: {(pred.away_win_prob * 100).toFixed(0)}%</span>
                  </div>
                  <Link
                    to={`/prediction/${fixtureId}?league=${selectedLeague}&season=${season}`}
                    class="view-analysis-btn"
                  >
                    <span>🔮</span>
                    <span>{$_("prediction.viewFullAnalysis")}</span>
                    <svg
                      class="arrow-icon"
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path d="M5 12h14M12 5l7 7-7 7" />
                    </svg>
                  </Link>
                </div>
              {:else}
                <!-- Show get prediction button -->
                <button
                  on:click={() => loadPrediction(fixtureId)}
                  disabled={loadingPredictions[fixtureId]}
                  class="w-full py-3 bg-accent/20 hover:bg-accent/30 text-accent rounded-lg font-medium text-sm flex items-center justify-center gap-2 disabled:opacity-50 btn-interact"
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
      {/if}

      <!-- Summary -->
      <div class="mt-4 text-center text-sm text-slate-500">
        <p>
          Showing {displayedFixtures.length} fixture{displayedFixtures.length !==
          1
            ? "s"
            : ""}
          {#if !showAllDates}
            for {formatDateNav(selectedDate)}
          {:else}
            (one per team)
          {/if}
        </p>
        {#if !showAllDates && displayedFixtures.length === 0}
          <button on:click={showAll} class="text-accent hover:underline mt-2">
            {$_("fixtures.showAllUpcoming")}
          </button>
        {/if}
      </div>
    {:else}
      <div class="text-center py-12 text-slate-500 glass-card">
        <div class="text-4xl mb-4">📅</div>
        <p class="font-medium text-lg mb-2">
          {#if !showAllDates}
            {$_("fixtures.noFixturesOnDate", {
              values: { date: formatDateNav(selectedDate) },
            })}
          {:else}
            {$_("fixtures.noUpcomingFixtures")}
          {/if}
        </p>
        <p class="text-sm text-slate-400">
          {#if !showAllDates}
            {$_("fixtures.tryDifferentDate")}
          {:else}
            {$_("fixtures.noScheduledFixtures", {
              values: { league: currentLeague.name },
            })}
          {/if}
        </p>
        {#if !showAllDates}
          <button
            on:click={showAll}
            class="mt-4 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/80 transition-colors"
          >
            {$_("fixtures.showAllUpcoming")}
          </button>
        {:else}
          <p class="text-xs text-slate-500 mt-4">
            {$_("fixtures.tryDifferentLeague")}
          </p>
        {/if}
      </div>
    {/if}
  </div>
</div>

<style>
  .scrollbar-hide {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
  .scrollbar-hide::-webkit-scrollbar {
    display: none;
  }

  :global(.view-analysis-btn) {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    margin-top: 12px;
    padding: 12px 16px;
    background: linear-gradient(
      135deg,
      rgba(139, 92, 246, 0.2),
      rgba(236, 72, 153, 0.15)
    );
    border: 1px solid rgba(139, 92, 246, 0.4);
    border-radius: 10px;
    color: #c4b5fd;
    font-size: 0.875rem;
    font-weight: 600;
    text-decoration: none;
    transition: all 0.2s ease;
    cursor: pointer;
    min-height: 44px;
  }

  :global(.view-analysis-btn:hover) {
    background: linear-gradient(
      135deg,
      rgba(139, 92, 246, 0.35),
      rgba(236, 72, 153, 0.25)
    );
    border-color: rgba(139, 92, 246, 0.6);
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(139, 92, 246, 0.25);
  }

  :global(.view-analysis-btn:active) {
    transform: translateY(0) scale(0.98);
  }

  :global(.view-analysis-btn .arrow-icon) {
    transition: transform 0.2s ease;
  }

  :global(.view-analysis-btn:hover .arrow-icon) {
    transform: translateX(3px);
  }
</style>
