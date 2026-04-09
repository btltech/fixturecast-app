<script>
  import SEOHead from "../components/SEOHead.svelte";
  import { generateStandingsSEO } from "../services/seoService.js";
  const seoData = generateStandingsSEO();
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { API_URL } from "../config.js";
  import { _ } from "svelte-i18n";
  import {
    getSavedLeague,
    saveLeague,
  } from "../services/preferences.js";
  import { LEAGUES } from "../services/leagues.js";

  let selectedLeague = getSavedLeague(39); // Premier League default (persisted)
  let standings = [];
  let leagueInfo = null;
  let loading = true;
  let error = null;
  const leagues = LEAGUES.map((l) => ({ ...l, flag: l.emoji }));

  // Leagues that display as a single calendar year (not "2025/26" cross-year format)
  const SINGLE_YEAR_LEAGUE_IDS = new Set([
    71, 116, 183, 244, 164,         // calendar-year / summer leagues
    13, 11, 73, 130,                // South American cups
    98, 292, 253, 262,              // J1, K League, MLS, Liga MX
    128, 239, 265,                  // South American leagues
    296, 278, 340, 169, 255,        // Asian / USL
  ]);

  function formatSeason(leagueId, seasonYear) {
    const currentYear = new Date().getFullYear();
    if (!SINGLE_YEAR_LEAGUE_IDS.has(leagueId) && seasonYear < currentYear) {
      return `${seasonYear}/${String(seasonYear + 1).slice(2)}`;
    }
    return String(seasonYear);
  }

  // Active leagues — populated from /api/active-leagues on mount
  // Default: show all leagues while loading (prevents empty selector on first paint)
  let activeLeagueIds = new Set(LEAGUES.map((l) => l.id));

  // Group leagues by tier — filtered to only those currently active
  $: europeanLeagues = leagues.filter((l) => l.tier === 0 && activeLeagueIds.has(l.id));
  $: topLeagues = leagues.filter((l) => l.tier === 1 && activeLeagueIds.has(l.id));
  $: secondDivisions = leagues.filter((l) => l.tier === 2 && activeLeagueIds.has(l.id));
  $: cups = leagues.filter((l) => l.tier === 3 && activeLeagueIds.has(l.id));

  async function fetchStandings() {
    loading = true;
    error = null;
    try {
      const response = await fetch(
        `${API_URL}/api/standings?league=${selectedLeague}`,
      );
      if (!response.ok) throw new Error("Failed to fetch standings");
      const data = await response.json();

      if (data.response && data.response[0]) {
        leagueInfo = data.response[0].league;
        standings = data.response[0].league.standings[0] || [];
      }
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    fetchStandings();
    // Fetch active leagues in the background — filters selector to only show live competitions
    fetch(`${API_URL}/api/active-leagues`)
      .then((r) => r.json())
      .then((data) => {
        if (data.active_leagues?.length) {
          activeLeagueIds = new Set(data.active_leagues);
        }
      })
      .catch(() => { /* silently keep showing all leagues on error */ });
  });

  function getFormColor(result) {
    if (result === "W") return "bg-green-500";
    if (result === "D") return "bg-yellow-500";
    if (result === "L") return "bg-red-500";
    return "bg-gray-500";
  }

  function getPositionColor(rank) {
    if (rank <= 4) return "text-green-400"; // Champions League
    if (rank <= 6) return "text-blue-400"; // Europa League
    if (rank >= standings.length - 2) return "text-red-400"; // Relegation
    return "text-slate-300";
  }

  function getPositionBadge(rank) {
    if (rank <= 4) return "bg-green-500/20 border-green-500/30";
    if (rank <= 6) return "bg-blue-500/20 border-blue-500/30";
    if (rank >= standings.length - 2) return "bg-red-500/20 border-red-500/30";
    return "bg-white/5 border-white/10";
  }

  function calculatePPG(points, played) {
    if (played === 0) return "0.00";
    return (points / played).toFixed(2);
  }

  function getFormStreakInfo(form) {
    if (!form) return { streak: 0, type: null };
    const recent = form.split("").reverse();
    let streak = 0;
    const firstResult = recent[0];
    for (const result of recent) {
      if (result === firstResult) streak++;
      else break;
    }
    return { streak, type: firstResult };
  }
</script>

<SEOHead data={seoData} />

<div class="space-y-6 page-enter">
  <!-- Header -->
  <div class="glass-card p-6 element-enter">
    <h1 class="text-3xl font-bold mb-4">{$_('standings.leagueStandings')}</h1>

    <!-- League Selector - Grouped by tier -->
    <div class="space-y-4">
      <!-- European Competitions -->
      <div>
        <h3 class="text-xs uppercase tracking-wider text-slate-400 mb-2">
          🏆 {$_('standings.europeanComps')}
        </h3>
        <div class="flex flex-wrap gap-2">
          {#each europeanLeagues as league}
            <button
              on:click={() => {
                selectedLeague = league.id;
                saveLeague(selectedLeague);
                fetchStandings();
              }}
              class="px-3 py-2 rounded-lg text-sm btn-interact touch-target {selectedLeague ===
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
        <h3 class="text-xs uppercase tracking-wider text-slate-400 mb-2">
          ⭐ {$_('standings.topLeagues')}
        </h3>
        <div class="flex flex-wrap gap-2">
          {#each topLeagues as league}
            <button
              on:click={() => {
                selectedLeague = league.id;
                saveLeague(selectedLeague);
                fetchStandings();
              }}
              class="px-3 py-1.5 rounded-lg text-sm btn-interact {selectedLeague ===
              league.id
                ? 'bg-accent text-white font-medium'
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
        <h3 class="text-xs uppercase tracking-wider text-slate-400 mb-2">
          📊 {$_('standings.moreLeagues')}
        </h3>
        <div class="flex flex-wrap gap-2">
          {#each secondDivisions as league}
            <button
              on:click={() => {
                selectedLeague = league.id;
                saveLeague(selectedLeague);
                fetchStandings();
              }}
              class="px-3 py-1.5 rounded-lg text-sm btn-interact {selectedLeague ===
              league.id
                ? 'bg-accent text-white font-medium'
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
        <h3 class="text-xs uppercase tracking-wider text-slate-400 mb-2">
          🏆 {$_('standings.domesticCups')}
        </h3>
        <div class="flex flex-wrap gap-2">
          {#each cups as league}
            <button
              on:click={() => {
                selectedLeague = league.id;
                saveLeague(selectedLeague);
                fetchStandings();
              }}
              class="px-3 py-1.5 rounded-lg text-sm btn-interact touch-target {selectedLeague ===
              league.id
                ? 'bg-orange-500/80 text-white font-medium'
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
    <div class="glass-card p-12 text-center">
      <div
        class="inline-block w-12 h-12 border-4 border-accent border-t-transparent rounded-full animate-spin"
      ></div>
      <p class="mt-4 text-slate-400">{$_('standings.loading')}</p>
    </div>
  {:else if error}
    <div class="glass-card p-8 text-center border border-red-500/30">
      <p class="text-red-400">❌ {error}</p>
    </div>
  {:else if standings.length > 0}
    <!-- Standings Table -->
    <div class="glass-card overflow-hidden element-enter stagger-1">
      <!-- League Info -->
      {#if leagueInfo}
        <div class="p-4 border-b border-white/10 flex items-center gap-3">
          <img src={leagueInfo.logo} alt={leagueInfo.name} class="w-12 h-12" />
          <div>
            <h2 class="text-xl font-bold">{leagueInfo.name}</h2>
            <p class="text-sm text-slate-400">
              {leagueInfo.country} • {$_('standings.season')} {formatSeason(selectedLeague, leagueInfo.season)}
            </p>
          </div>
        </div>
      {/if}

      <!-- Table -->
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-white/5 border-b border-white/10">
            <tr class="text-left text-sm">
              <th class="p-3 w-16">#</th>
              <th class="p-3">Team</th>
              <th class="p-3 text-center w-12">P</th>
              <th class="p-3 text-center w-12">W</th>
              <th class="p-3 text-center w-12">D</th>
              <th class="p-3 text-center w-12">L</th>
              <th class="p-3 text-center w-16">GD</th>
              <th class="p-3 text-center w-16 font-bold">Pts</th>
              <th class="p-3 text-center w-16 hidden sm:table-cell" title={$_('standings.pointsPerGame')}>{$_('standings.ppg')}</th>
              <th class="p-3 text-center">Form</th>
            </tr>
          </thead>
          <tbody>
            {#each standings as team, i}
              {@const formStreak = getFormStreakInfo(team.form)}
              {@const ppg = calculatePPG(team.points, team.all.played)}
              <tr
                class="border-b border-white/5 hover:bg-white/5 transition-colors group"
              >
                <td class="p-3">
                  <div class="flex items-center gap-2">
                    <span class="inline-flex items-center justify-center w-7 h-7 rounded-lg border text-sm font-bold {getPositionBadge(team.rank)} {getPositionColor(team.rank)}">
                      {team.rank}
                    </span>
                  </div>
                </td>
                <td class="p-3">
                  <Link
                    to="/team/{team.team.id}?league={selectedLeague}"
                    class="flex items-center gap-3 hover:text-accent transition-colors"
                  >
                    <img
                      src={team.team.logo}
                      alt={team.team.name}
                      class="w-7 h-7 group-hover:scale-110 transition-transform"
                    />
                    <div>
                      <span class="font-medium block">{team.team.name}</span>
                      {#if formStreak.streak >= 3}
                        <span class="text-xs {formStreak.type === 'W' ? 'text-green-400' : formStreak.type === 'L' ? 'text-red-400' : 'text-yellow-400'}">
                          {formStreak.type === 'W' ? $_('standings.winsStreak', {values: {count: formStreak.streak}}) : formStreak.type === 'L' ? $_('standings.lossesStreak', {values: {count: formStreak.streak}}) : $_('standings.drawsStreak', {values: {count: formStreak.streak}})}
                        </span>
                      {/if}
                    </div>
                  </Link>
                </td>
                <td class="p-3 text-center text-slate-400">{team.all.played}</td>
                <td class="p-3 text-center text-green-400 font-medium">{team.all.win}</td>
                <td class="p-3 text-center text-yellow-400">{team.all.draw}</td>
                <td class="p-3 text-center text-red-400">{team.all.lose}</td>
                <td class="p-3 text-center font-medium {team.goalsDiff >= 0 ? 'text-green-400' : 'text-red-400'}">
                  {team.goalsDiff > 0 ? "+" : ""}{team.goalsDiff}
                </td>
                <td class="p-3 text-center">
                  <span class="text-xl font-bold text-white bg-accent/20 px-2 py-1 rounded-lg">
                    {team.points}
                  </span>
                </td>
                <td class="p-3 text-center hidden sm:table-cell">
                  <span class="text-sm font-mono {parseFloat(ppg) >= 2 ? 'text-green-400' : parseFloat(ppg) >= 1.5 ? 'text-blue-400' : parseFloat(ppg) >= 1 ? 'text-yellow-400' : 'text-red-400'}">
                    {ppg}
                  </span>
                </td>
                <td class="p-3">
                  <div class="flex items-center gap-1 justify-center">
                    {#if team.form}
                      {#each team.form.split("").slice(-5) as result, idx}
                        <div
                          class="{getFormColor(result)} w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-white shadow-sm transform hover:scale-110 transition-transform"
                          title="{result === 'W' ? 'Win' : result === 'D' ? 'Draw' : 'Loss'} (Match {idx + 1})"
                          style="animation-delay: {idx * 50}ms"
                        >
                          {result}
                        </div>
                      {/each}
                    {:else}
                      <span class="text-xs text-slate-500">—</span>
                    {/if}
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Legend -->
      <div class="p-4 bg-white/5 border-t border-white/10 text-xs space-y-2">
        <div class="flex flex-wrap gap-4">
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 bg-green-500 rounded"></div>
            <span class="text-slate-400">{$_('standings.championLeague')}</span>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 bg-blue-500 rounded"></div>
            <span class="text-slate-400">{$_('standings.europaLeague')}</span>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 bg-red-500 rounded"></div>
            <span class="text-slate-400">{$_('standings.relegation')}</span>
          </div>
        </div>
        <div class="text-slate-500">
          {$_('standings.legend')}
        </div>
      </div>
    </div>
  {:else}
    <div class="glass-card p-8 text-center">
      <p class="text-slate-400">{$_('standings.noStandings')}</p>
    </div>
  {/if}
</div>
