<script>
  import SEOHead from "../components/SEOHead.svelte";
  import { generateResultsSEO } from "../services/seoService.js";
  import { _, locale } from "svelte-i18n";
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { API_URL } from "../config.js";
  import { getCurrentSeason } from "../services/season.js";
  import { getSavedLeague, saveLeague } from "../services/preferences.js";
  import { LEAGUES } from "../services/leagues.js";
  import { formatDate } from "../lib/i18n/format.js";

  let seoData;
  $: seoData = generateResultsSEO($locale);

  let selectedLeague = getSavedLeague(39);
  let results = [];
  let loading = true;
  let error = null;
  const season = getCurrentSeason();

  const leagueOptions = LEAGUES.map((l) => ({ ...l, flag: l.emoji }));

  $: europeanLeagues = leagueOptions.filter((l) => l.tier === 0);
  $: topLeagues = leagueOptions.filter((l) => l.tier === 1);
  $: secondDivisions = leagueOptions.filter((l) => l.tier === 2);
  $: cups = leagueOptions.filter((l) => l.tier === 3);

  async function fetchResults() {
    loading = true;
    error = null;
    try {
      const response = await fetch(
        `${API_URL}/api/results?league=${selectedLeague}&last=20&season=${season}`,
      );
      if (!response.ok) throw new Error($_("results.fetchFailed"));
      const data = await response.json();
      results = data.response || [];
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    fetchResults();
  });

  function changeLeague(leagueId) {
    selectedLeague = leagueId;
    saveLeague(leagueId);
    fetchResults();
  }
</script>

<SEOHead data={seoData} />

<div class="space-y-6 page-enter">
  <!-- Header + League Selector -->
  <div class="glass-card p-6 element-enter">
    <h1 class="text-3xl font-bold mb-4">{$_("results.recentResults")}</h1>

    <div class="space-y-4">
      <!-- European Competitions -->
      <div>
        <div class="text-xs text-slate-400 mb-2 font-bold">🏆 {$_("fixtures.europeanComps")}</div>
        <div class="flex flex-wrap gap-2">
          {#each europeanLeagues as league}
            <button
              on:click={() => changeLeague(league.id)}
              class="px-3 py-1.5 rounded-lg text-sm btn-interact {selectedLeague ===
              league.id
                ? 'bg-yellow-500/80 text-black font-medium'
                : 'bg-white/5 hover:bg-white/10'}"
            >
              <span class="mr-1">{league.flag}</span>
              {league.name}
            </button>
          {/each}
        </div>
      </div>

      <!-- Top Leagues -->
      <div>
        <div class="text-xs text-slate-400 mb-2 font-bold">🌍 {$_("fixtures.topLeagues")}</div>
        <div class="flex flex-wrap gap-2">
          {#each topLeagues as league}
            <button
              on:click={() => changeLeague(league.id)}
              class="px-3 py-1.5 rounded-lg text-sm btn-interact {selectedLeague ===
              league.id
                ? 'bg-accent text-white'
                : 'bg-white/5 hover:bg-white/10'}"
            >
              <span class="mr-1">{league.flag}</span>
              {league.name}
            </button>
          {/each}
        </div>
      </div>

      <!-- More Leagues -->
      <div>
        <div class="text-xs text-slate-400 mb-2 font-bold">
          📋 {$_("results.moreLeagues")}
        </div>
        <div class="flex flex-wrap gap-2">
          {#each secondDivisions as league}
            <button
              on:click={() => changeLeague(league.id)}
              class="px-3 py-1.5 rounded-lg text-sm btn-interact {selectedLeague ===
              league.id
                ? 'bg-accent text-white'
                : 'bg-white/5 hover:bg-white/10'}"
            >
              <span class="mr-1">{league.flag}</span>
              {league.name}
            </button>
          {/each}
        </div>
      </div>

      <!-- Domestic Cups -->
      <div>
        <div class="text-xs text-slate-400 mb-2 font-bold">
          🏆 {$_("fixtures.domesticCups")}
        </div>
        <div class="flex flex-wrap gap-2">
          {#each cups as league}
            <button
              on:click={() => changeLeague(league.id)}
              class="px-3 py-1.5 rounded-lg text-sm btn-interact {selectedLeague ===
              league.id
                ? 'bg-orange-500/80 text-white'
                : 'bg-white/5 hover:bg-white/10'}"
            >
              <span class="mr-1">{league.flag}</span>
              {league.name}
            </button>
          {/each}
        </div>
      </div>
    </div>
  </div>

  {#if loading}
    <div class="space-y-4">
      {#each Array(6) as _}
        <div class="glass-card p-6 animate-pulse">
          <div class="flex items-center justify-between mb-4">
            <div class="h-4 bg-white/10 rounded w-32"></div>
            <div class="h-4 bg-white/10 rounded w-20"></div>
          </div>
          <div class="grid grid-cols-[1fr_auto_1fr] gap-4 items-center">
            <div class="flex items-center gap-3 justify-end">
              <div class="h-5 bg-white/10 rounded w-24"></div>
              <div class="w-12 h-12 bg-white/10 rounded-full"></div>
            </div>
            <div class="h-10 bg-white/10 rounded-lg w-20"></div>
            <div class="flex items-center gap-3">
              <div class="w-12 h-12 bg-white/10 rounded-full"></div>
              <div class="h-5 bg-white/10 rounded w-24"></div>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {:else if error}
    <div class="glass-card p-8 text-center border border-red-500/30">
      <p class="text-red-400 mb-4">❌ {error}</p>
      <button
        on:click={fetchResults}
        class="px-6 py-2 bg-primary/20 hover:bg-primary/30 text-primary rounded-lg font-medium transition-colors"
      >
        {$_("common.retry")}
      </button>
    </div>
  {:else if results.length > 0}
    <div class="space-y-4 element-enter stagger-1">
      {#each results as match}
        <div class="glass-card p-6 hover:bg-white/5 result-card">
          <div class="flex items-center justify-between mb-4">
            <div class="text-sm text-slate-400">
              {formatDate(match.fixture.date, $locale, {
                weekday: "short",
                month: "short",
                day: "numeric",
                year: "numeric",
              })}
            </div>
            <div class="flex items-center gap-2">
              <Link
                to="/prediction/{match.fixture.id}?league={match.league
                  .id}&season={season}"
                class="text-xs px-2 py-1 rounded bg-accent/20 text-accent hover:bg-accent/30 transition-colors"
              >
                🤖 {$_("prediction.aiPrediction")}
              </Link>
              <div class="text-xs px-2 py-1 rounded bg-slate-700">
                {match.league.round}
              </div>
            </div>
          </div>

          <div class="grid grid-cols-[1fr_auto_1fr] gap-4 items-center">
            <Link
              to="/team/{match.teams.home.id}?league={match.league.id}"
              class="flex items-center gap-3 justify-end hover:text-accent transition-colors"
            >
              <span class="text-lg font-bold text-right"
                >{match.teams.home.name}</span
              >
              <img
                src={match.teams.home.logo}
                alt={match.teams.home.name}
                class="w-12 h-12"
              />
            </Link>

            <div class="flex items-center gap-3">
              <div
                class="text-3xl font-bold px-4 py-2 bg-white/10 rounded-lg min-w-[80px] text-center"
              >
                {match.goals.home} - {match.goals.away}
              </div>
            </div>

            <Link
              to="/team/{match.teams.away.id}?league={match.league.id}"
              class="flex items-center gap-3 hover:text-accent transition-colors"
            >
              <img
                src={match.teams.away.logo}
                alt={match.teams.away.name}
                class="w-12 h-12"
              />
              <span class="text-lg font-bold">{match.teams.away.name}</span>
            </Link>
          </div>

          {#if match.fixture.venue?.name}
            <div class="mt-4 text-sm text-slate-400 text-center">
              📍 {match.fixture.venue.name}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {:else}
    <div class="glass-card p-8 text-center">
      <p class="text-slate-400">{$_("results.noResultsAvailable")}</p>
    </div>
  {/if}
</div>
