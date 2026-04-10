<script>
  import { Link } from "svelte-routing";
  import { onMount } from "svelte";
  import { _ } from "svelte-i18n";
  import { locale } from "../lib/i18n";
  import { API_URL } from "../config.js";
  import { getLeagueSeason } from "../services/season.js";
  import { getLeagueDisplay as leagueDisplay } from "../services/leagues.js";
  import MatchCardSkeleton from "../components/MatchCardSkeleton.svelte";
  import EmailSignup from "../components/EmailSignup.svelte";
  import NotificationSettings from "../components/NotificationSettings.svelte";
  import MatchCountdown from "../components/MatchCountdown.svelte";
  import AccumulatorCard from "../components/AccumulatorCard.svelte";
  import SEOHead from "../components/SEOHead.svelte";
  import { generateHomeSEO } from "../services/seoService.js";

  let seoData;
  $: seoData = generateHomeSEO($locale);

  let matchOfTheDay = null;
  let todaysMatches = [];
  let upcomingMatches = [];
  let upcomingDaysAhead = null;
  let loading = true;
  let error = null;

  function getLeagueDisplay(leagueId) {
    return leagueDisplay(leagueId);
  }

  function getFixtureSeason(fixture, fallbackLeagueId = 39) {
    return getLeagueSeason(
      fixture?.league?.id || fallbackLeagueId,
      fixture?.fixture?.date,
    );
  }

  onMount(async () => {
    await loadTodaysData();
  });

  async function loadTodaysData(retries = 2) {
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

        // Fallback: if no match_of_the_day but we have fixtures, use the first one
        if (!matchOfTheDay && todaysMatches.length > 0) {
          matchOfTheDay = todaysMatches[0];
        }

        // If we got an empty response, retry (backend may still be warming up)
        if (todaysMatches.length === 0 && !matchOfTheDay && retries > 0) {
          await new Promise((r) => setTimeout(r, 2000));
          return await loadTodaysData(retries - 1);
        }
      } else if (retries > 0) {
        await new Promise((r) => setTimeout(r, 2000));
        return await loadTodaysData(retries - 1);
      } else {
        error = $_("errors.homeFixturesLoad");
      }
    } catch (e) {
      console.error("Error loading today's matches:", e);
      if (retries > 0) {
        await new Promise((r) => setTimeout(r, 2000));
        return await loadTodaysData(retries - 1);
      }
      error = $_("errors.homeFixturesLoad");
    }
    // Only set loading=false when we're done (not retrying)
    loading = false;
  }

  function formatTime(dateStr) {
    return new Date(dateStr).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  }
</script>

<SEOHead data={seoData} />

<div class="space-y-8 md:space-y-12 page-enter pb-12">
  <!-- Hero Section -->
  <div class="relative isolate overflow-hidden">
    <!-- Background Effects -->
    <div class="absolute inset-0 -z-10">
      <div
        class="absolute top-0 right-0 -translate-y-12 translate-x-12 w-96 h-96 bg-primary/20 rounded-full blur-3xl opacity-50"
      ></div>
      <div
        class="absolute bottom-0 left-0 translate-y-12 -translate-x-12 w-96 h-96 bg-secondary/20 rounded-full blur-3xl opacity-50"
      ></div>
    </div>

    <div
      class="glass-card p-8 md:p-12 lg:p-16 text-center relative overflow-hidden group border-white/5"
    >
      <div
        class="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700"
      ></div>

      <div
        class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-sm font-medium text-accent mb-6 backdrop-blur-md"
      >
        <span class="relative flex h-2.5 w-2.5">
          <span
            class="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75"
          ></span>
          <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-accent"
          ></span>
        </span>
        {#if loading}
          {$_("common.loading")}
        {:else if todaysMatches.length > 0}
          <span class="font-bold text-white">{todaysMatches.length}</span>
          {$_("fixtures.title")}
        {:else}
          {$_("home.hero.subtitle")}
        {/if}
      </div>

      <h1
        class="font-display text-4xl sm:text-5xl md:text-6xl lg:text-7xl xl:text-8xl font-bold mb-6 tracking-tight leading-none"
      >
        <span
          class="text-transparent bg-clip-text bg-gradient-to-r from-white via-white to-slate-400"
          >Fixture</span
        ><span
          class="text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent"
          >Cast</span
        >
      </h1>

      <p
        class="font-light text-lg sm:text-xl md:text-2xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed"
      >
        Next-generation football forecasting powered by <span
          class="text-white font-medium">advanced AI</span
        >.
      </p>

      <div
        class="flex flex-col sm:flex-row justify-center gap-4 sm:gap-5 w-full max-w-lg mx-auto relative z-10"
      >
        <Link
          to="/today"
          class="group relative px-8 py-4 sm:px-10 sm:py-5 rounded-2xl bg-gradient-to-r from-primary via-blue-500 to-cyan-500 text-white font-bold text-lg shadow-xl shadow-blue-500/30 hover:shadow-blue-500/50 transition-all hover:-translate-y-1 hover:scale-105 overflow-hidden text-center"
        >
          <div
            class="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300"
          ></div>
          <span class="relative flex items-center justify-center gap-3">
            <svg
              class="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
              />
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            Today's Fixtures
            <svg
              class="w-5 h-5 transition-transform group-hover:translate-x-1"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              ><path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M13 7l5 5m0 0l-5 5m5-5H6"
              /></svg
            >
          </span>
        </Link>
        <Link
          to="/ai"
          class="px-8 py-4 sm:px-10 sm:py-5 rounded-2xl bg-white/5 text-white font-bold text-lg border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all hover:-translate-y-1 backdrop-blur-sm text-center"
        >
          View AI Models
        </Link>
      </div>

      <!-- Quick Actions Bar -->
      <div
        class="mt-8 flex justify-center gap-3 flex-wrap max-w-2xl mx-auto relative z-10"
      >
        <Link
          to="/live"
          class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/15 transition-all text-sm font-medium text-slate-300 hover:text-white"
        >
          <span class="relative flex h-2 w-2">
            <span
              class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"
            ></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-red-500"
            ></span>
          </span>
          Live Scores
        </Link>
        <Link
          to="/smart-markets"
          class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/15 transition-all text-sm font-medium text-slate-300 hover:text-white"
        >
          💡 Smart Markets
        </Link>
        <Link
          to="/accumulators"
          class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/15 transition-all text-sm font-medium text-slate-300 hover:text-white"
        >
          🎲 Daily Accas
        </Link>
        <Link
          to="/standings"
          class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/15 transition-all text-sm font-medium text-slate-300 hover:text-white"
        >
          📊 Standings
        </Link>
      </div>

      <!-- Inline Match of the Day Preview in Hero -->
      {#if !loading && matchOfTheDay}
        <Link
          to={`/prediction/${matchOfTheDay.fixture.id}?league=${matchOfTheDay.league?.id || 39}&season=${getFixtureSeason(matchOfTheDay)}`}
          class="mt-10 inline-flex items-center gap-4 px-5 py-3 rounded-2xl bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/20 hover:border-amber-500/40 transition-all hover:scale-[1.02] group"
        >
          <div class="flex items-center gap-2">
            <svg
              class="w-5 h-5 text-amber-400"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
              />
            </svg>
            <span class="text-sm font-bold text-amber-400">MOTD</span>
          </div>
          <div class="flex items-center gap-3">
            <img
              src={matchOfTheDay.teams.home.logo}
              alt={matchOfTheDay.teams.home.name}
              class="w-7 h-7 object-contain"
            />
            <span class="text-white font-medium text-sm"
              >{matchOfTheDay.teams.home.name}</span
            >
            <span class="text-slate-500 text-xs font-bold">vs</span>
            <span class="text-white font-medium text-sm"
              >{matchOfTheDay.teams.away.name}</span
            >
            <img
              src={matchOfTheDay.teams.away.logo}
              alt={matchOfTheDay.teams.away.name}
              class="w-7 h-7 object-contain"
            />
          </div>
          <div class="flex items-center gap-2 text-slate-400 text-sm">
            <span class="font-mono"
              >{formatTime(matchOfTheDay.fixture.date)}</span
            >
            <svg
              class="w-4 h-4 transition-transform group-hover:translate-x-1"
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
          </div>
        </Link>
      {/if}
    </div>
  </div>

  <!-- Match of the Day Section -->
  {#if loading}
    <!-- Match of the Day Skeleton -->
    <div class="space-y-4">
      <div class="flex items-center justify-between px-2">
        <div class="h-8 w-48 bg-white/10 rounded-lg animate-pulse"></div>
        <div class="h-6 w-32 bg-white/10 rounded-full animate-pulse"></div>
      </div>

      <div class="glass-card p-6 md:p-8 lg:p-10 animate-pulse">
        <div
          class="flex flex-col md:flex-row items-center justify-between gap-8"
        >
          <!-- Home Team Skeleton -->
          <div class="flex-1 space-y-4">
            <div
              class="w-24 h-24 md:w-32 md:h-32 bg-white/10 rounded-full mx-auto"
            ></div>
            <div class="h-8 w-48 bg-white/10 rounded mx-auto"></div>
          </div>

          <!-- VS Skeleton -->
          <div class="space-y-2">
            <div class="h-6 w-16 bg-white/10 rounded mx-auto"></div>
            <div class="h-12 w-24 bg-white/10 rounded mx-auto"></div>
          </div>

          <!-- Away Team Skeleton -->
          <div class="flex-1 space-y-4">
            <div
              class="w-24 h-24 md:w-32 md:h-32 bg-white/10 rounded-full mx-auto"
            ></div>
            <div class="h-8 w-48 bg-white/10 rounded mx-auto"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Today's Matches Skeleton -->
    <div class="space-y-4">
      <div class="h-8 w-56 bg-white/10 rounded-lg animate-pulse"></div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {#each Array(6) as _}
          <MatchCardSkeleton />
        {/each}
      </div>
    </div>
  {:else if matchOfTheDay}
    <div class="relative">
      <div class="flex items-center justify-between mb-6 px-2">
        <div class="flex items-center gap-3">
          <div class="p-2 bg-amber-500/10 rounded-lg text-amber-400">
            <svg
              class="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              ><path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
              /></svg
            >
          </div>
          <h2 class="text-2xl font-display font-bold text-white">
            Match of the Day
          </h2>
        </div>
        <div
          class="text-sm font-medium text-slate-400 bg-white/5 px-3 py-1 rounded-full border border-white/5"
        >
          {getLeagueDisplay(matchOfTheDay.league?.id).emoji}
          {matchOfTheDay.league?.name || "League"}
        </div>
      </div>

      <Link
        to={`/prediction/${matchOfTheDay.fixture.id}?league=${matchOfTheDay.league?.id || 39}&season=${getFixtureSeason(matchOfTheDay)}`}
        class="block group relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 to-slate-950 border border-white/10 hover:border-primary/50 transition-all duration-500 hover:shadow-2xl hover:shadow-primary/10"
      >
        <!-- Background Glow -->
        <div
          class="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full bg-gradient-to-b from-primary/5 to-transparent opacity-50"
        ></div>

        <div class="relative p-6 md:p-8 lg:p-10">
          <div
            class="flex flex-col md:flex-row items-center justify-between gap-8"
          >
            <!-- Home Team -->
            <div class="flex-1 text-center md:text-right group/team">
              <div class="relative inline-block">
                <div
                  class="absolute inset-0 bg-primary/20 blur-2xl rounded-full opacity-0 group-hover/team:opacity-100 transition-opacity"
                ></div>
                <img
                  src={matchOfTheDay.teams.home.logo}
                  alt={matchOfTheDay.teams.home.name}
                  class="relative w-24 h-24 md:w-32 md:h-32 mx-auto md:ml-auto object-contain drop-shadow-2xl transition-transform group-hover/team:scale-110 duration-300"
                />
              </div>
              <div
                class="mt-4 font-display font-bold text-xl md:text-3xl text-white"
              >
                {matchOfTheDay.teams.home.name}
              </div>
            </div>

            <!-- VS & Time -->
            <div class="px-4 text-center shrink-0 relative z-10">
              <div
                class="text-sm font-bold text-primary tracking-widest uppercase mb-2"
              >
                VS
              </div>

              <!-- Countdown Component -->
              <div class="mb-3">
                <MatchCountdown matchData={matchOfTheDay} />
              </div>

              <div
                class="text-3xl sm:text-4xl md:text-5xl font-display font-bold text-white mb-2 tracking-tight"
              >
                {formatTime(matchOfTheDay.fixture.date)}
              </div>
              <div
                class="text-sm font-medium text-slate-400 bg-white/5 px-4 py-1.5 rounded-full inline-block"
              >
                {new Date(matchOfTheDay.fixture.date).toLocaleDateString([], {
                  weekday: "long",
                  month: "long",
                  day: "numeric",
                })}
              </div>
            </div>

            <!-- Away Team -->
            <div class="flex-1 text-center md:text-left group/team">
              <div class="relative inline-block">
                <div
                  class="absolute inset-0 bg-secondary/20 blur-2xl rounded-full opacity-0 group-hover/team:opacity-100 transition-opacity"
                ></div>
                <img
                  src={matchOfTheDay.teams.away.logo}
                  alt={matchOfTheDay.teams.away.name}
                  class="relative w-24 h-24 md:w-32 md:h-32 mx-auto md:mr-auto object-contain drop-shadow-2xl transition-transform group-hover/team:scale-110 duration-300"
                />
              </div>
              <div
                class="mt-4 font-display font-bold text-xl md:text-3xl text-white"
              >
                {matchOfTheDay.teams.away.name}
              </div>
            </div>
          </div>

          <div class="mt-10 text-center">
            <span
              class="inline-flex items-center gap-2 px-6 py-3 bg-primary/10 hover:bg-primary/20 border border-primary/20 rounded-full text-primary font-bold transition-all group-hover:scale-105"
            >
              <svg
                class="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                ><path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                /></svg
              >
              {$_("todaysFixtures.viewAnalysis")}
            </span>
          </div>
        </div>
      </Link>
    </div>
  {:else if !error && !matchOfTheDay && todaysMatches.length === 0}
    {#if upcomingMatches.length > 0}
      <!-- Upcoming fixtures fallback: today has no games, show what's ahead -->
      <div class="content-enter">
        <div class="flex items-center justify-between mb-6 px-2">
          <div>
            <h2 class="text-2xl font-display font-bold">{$_("home.upcomingHeading")}</h2>
            <p class="text-slate-400 text-sm mt-1">
              {upcomingDaysAhead === 1
                ? $_("home.upcomingTomorrow")
                : $_("home.upcomingInDays", { values: { days: upcomingDaysAhead } })}
            </p>
          </div>
          <Link
            to="/fixtures"
            class="text-sm font-medium text-primary hover:text-primary/80 transition-colors"
          >
            {$_("home.viewUpcoming")} &rarr;
          </Link>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 stagger-enter">
          {#each upcomingMatches.slice(0, 6) as fixture}
            <Link
              to={`/prediction/${fixture.fixture.id}?league=${fixture.league?.id || 39}&season=${getFixtureSeason(fixture)}`}
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
      <!-- Genuine no-matches state with retry -->
      <div class="glass-card p-12 text-center content-enter">
        <div
          class="w-16 h-16 bg-white/5 rounded-2xl flex items-center justify-center mx-auto mb-4 text-slate-400"
        >
          <svg
            class="w-8 h-8"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            ><path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
            /></svg
          >
        </div>
        <h3 class="font-display font-bold text-xl mb-2">{$_("fixtures.noMatchesToday")}</h3>
        <p class="text-slate-400 mb-4">
          {$_("home.noMatchesDesc")}
        </p>
        <button
          on:click={() => loadTodaysData()}
          class="px-4 py-2 bg-accent/20 hover:bg-accent/30 text-accent rounded-lg font-medium text-sm"
        >
          🔄 {$_("common.retry")}
        </button>
      </div>
    {/if}
  {/if}

  <!-- Daily Accumulator -->
  <AccumulatorCard />

  <!-- Today's Other Matches -->
  {#if todaysMatches.length > 1}
    <div class="content-enter">
      <div class="flex items-center justify-between mb-6 px-2">
        <h2 class="text-2xl font-display font-bold">{$_("home.todayMatchesHeading")}</h2>
        <Link
          to="/today"
          class="text-sm font-medium text-primary hover:text-primary/80 transition-colors"
        >
          {$_("home.viewAllMatches", { values: { count: todaysMatches.length } })} &rarr;
        </Link>
      </div>

      <div
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 stagger-enter"
      >
        {#each todaysMatches.slice(1, 7) as fixture}
          <Link
            to={`/prediction/${fixture.fixture.id}?league=${fixture.league?.id || 39}&season=${getFixtureSeason(fixture)}`}
            class="group glass-card p-4 hover:border-primary/30 transition-all hover:-translate-y-1"
          >
            <div
              class="flex items-center justify-between mb-3 text-xs text-slate-400"
            >
              <span>{fixture.league?.name}</span>
              <span class="font-mono">{formatTime(fixture.fixture.date)}</span>
            </div>

            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <img
                    src={fixture.teams.home.logo}
                    alt={fixture.teams?.home?.name || "Home team"}
                    class="w-8 h-8 object-contain"
                  />
                  <span
                    class="font-medium group-hover:text-white transition-colors"
                    >{fixture.teams.home.name}</span
                  >
                </div>
              </div>
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <img
                    src={fixture.teams.away.logo}
                    alt={fixture.teams?.away?.name || "Away team"}
                    class="w-8 h-8 object-contain"
                  />
                  <span
                    class="font-medium group-hover:text-white transition-colors"
                    >{fixture.teams.away.name}</span
                  >
                </div>
              </div>
            </div>
          </Link>
        {/each}
      </div>
    </div>
  {/if}

  <!-- Quick Access Grid -->
  <div class="grid grid-cols-1 md:grid-cols-3 gap-6 stagger-enter">
    <Link to="/fixtures" class="glass-card p-6 group relative overflow-hidden">
      <div
        class="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity transform group-hover:scale-110 duration-500"
      >
        <svg
          class="w-24 h-24"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          ><path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
          /></svg
        >
      </div>
      <div
        class="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-400 mb-4 group-hover:bg-blue-500/20 transition-colors"
      >
        <svg
          class="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          ><path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
          /></svg
        >
      </div>
      <h3
        class="text-xl font-display font-bold mb-2 group-hover:text-primary transition-colors"
      >
        Fixtures
      </h3>
      <p class="text-sm text-slate-400 leading-relaxed">
        Browse matches playing today across all 51 leagues.
      </p>
    </Link>

    <Link to="/teams" class="glass-card p-6 group relative overflow-hidden">
      <div
        class="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity transform group-hover:scale-110 duration-500"
      >
        <svg
          class="w-24 h-24"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          ><path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
            d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
          /></svg
        >
      </div>
      <div
        class="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400 mb-4 group-hover:bg-emerald-500/20 transition-colors"
      >
        <svg
          class="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          ><path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
          /></svg
        >
      </div>
      <h3
        class="text-xl font-display font-bold mb-2 group-hover:text-emerald-400 transition-colors"
      >
        Team Stats
      </h3>
      <p class="text-sm text-slate-400 leading-relaxed">
        Analyze detailed team statistics and form guides.
      </p>
    </Link>

    <Link to="/ai" class="glass-card p-6 group relative overflow-hidden">
      <div
        class="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity transform group-hover:scale-110 duration-500"
      >
        <svg
          class="w-24 h-24"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          ><path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
            d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
          /></svg
        >
      </div>
      <div
        class="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center text-purple-400 mb-4 group-hover:bg-purple-500/20 transition-colors"
      >
        <svg
          class="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          ><path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
          /></svg
        >
      </div>
      <h3
        class="text-xl font-display font-bold mb-2 group-hover:text-purple-400 transition-colors"
      >
        AI Models
      </h3>
      <p class="text-sm text-slate-400 leading-relaxed">
        Access predictions from our advanced AI system.
      </p>
    </Link>
  </div>

  <!-- Bots Section -->
  <div class="space-y-6">
    <div class="flex items-center gap-3 px-2">
      <div class="p-2 bg-indigo-500/10 rounded-lg text-indigo-400">
        <svg
          class="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
          />
        </svg>
      </div>
      <h2 class="text-2xl font-display font-bold text-white">
        Get Predictions Everywhere
      </h2>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Discord Bot -->
      <a
        href="https://discord.com/oauth2/authorize?client_id=1444393438028339615&permissions=274877908992&integration_type=0&scope=bot+applications.commands"
        target="_blank"
        rel="noopener noreferrer"
        class="glass-card p-6 group relative overflow-hidden hover:border-indigo-500/30 transition-all"
      >
        <div
          class="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity transform group-hover:scale-110 duration-500"
        >
          <svg class="w-24 h-24" viewBox="0 0 24 24" fill="currentColor">
            <path
              d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"
            />
          </svg>
        </div>
        <div
          class="w-12 h-12 rounded-xl bg-indigo-500/10 flex items-center justify-center text-indigo-400 mb-4 group-hover:bg-indigo-500/20 transition-colors"
        >
          <svg class="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
            <path
              d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"
            />
          </svg>
        </div>
        <h3
          class="text-xl font-display font-bold mb-2 group-hover:text-indigo-400 transition-colors"
        >
          Discord Bot
        </h3>
        <p class="text-sm text-slate-400 leading-relaxed mb-4">
          Get AI predictions directly in your Discord server with slash
          commands.
        </p>
        <div class="flex flex-wrap gap-2 text-xs">
          <span class="px-2 py-1 bg-white/5 rounded-full text-slate-300"
            >/predict</span
          >
          <span class="px-2 py-1 bg-white/5 rounded-full text-slate-300"
            >/today</span
          >
          <span class="px-2 py-1 bg-white/5 rounded-full text-slate-300"
            >/motd</span
          >
        </div>
        <div
          class="mt-4 flex items-center gap-2 text-indigo-400 text-sm font-medium"
        >
          <span>Add to Server</span>
          <svg
            class="w-4 h-4 transition-transform group-hover:translate-x-1"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
            />
          </svg>
        </div>
      </a>

      <!-- Telegram Bot -->
      <a
        href="https://t.me/FixtureCastBot"
        target="_blank"
        rel="noopener noreferrer"
        class="glass-card p-6 group relative overflow-hidden hover:border-sky-500/30 transition-all"
      >
        <div
          class="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity transform group-hover:scale-110 duration-500"
        >
          <svg class="w-24 h-24" viewBox="0 0 24 24" fill="currentColor">
            <path
              d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"
            />
          </svg>
        </div>
        <div
          class="w-12 h-12 rounded-xl bg-sky-500/10 flex items-center justify-center text-sky-400 mb-4 group-hover:bg-sky-500/20 transition-colors"
        >
          <svg class="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
            <path
              d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"
            />
          </svg>
        </div>
        <h3
          class="text-xl font-display font-bold mb-2 group-hover:text-sky-400 transition-colors"
        >
          Telegram Bot
        </h3>
        <p class="text-sm text-slate-400 leading-relaxed mb-4">
          Chat with our bot on Telegram for instant match predictions anytime.
        </p>
        <div class="flex flex-wrap gap-2 text-xs">
          <span class="px-2 py-1 bg-white/5 rounded-full text-slate-300"
            >/predict</span
          >
          <span class="px-2 py-1 bg-white/5 rounded-full text-slate-300"
            >/today</span
          >
          <span class="px-2 py-1 bg-white/5 rounded-full text-slate-300"
            >/motd</span
          >
        </div>
        <div
          class="mt-4 flex items-center gap-2 text-sky-400 text-sm font-medium"
        >
          <span>Open in Telegram</span>
          <svg
            class="w-4 h-4 transition-transform group-hover:translate-x-1"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
            />
          </svg>
        </div>
      </a>
    </div>
  </div>

  <!-- Email Signup & Notifications -->
  <div class="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
    <EmailSignup />
    <NotificationSettings />
  </div>
</div>

<style>
  /* Page-specific animations handled by global CSS */
</style>
