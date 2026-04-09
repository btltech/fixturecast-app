<script>
  import SEOHead from "../components/SEOHead.svelte";
  import { generateTeamsSEO } from "../services/seoService.js";
  const seoData = generateTeamsSEO();
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { _ } from "svelte-i18n";
  import { API_URL } from "../config.js";
  import SearchBar from "../components/SearchBar.svelte";
  import { getCurrentSeason } from "../services/season.js";
  import { LEAGUES } from "../services/leagues.js";
  import { getSavedLeague, saveLeague } from "../services/preferences.js";

  const leagues = LEAGUES;

  let teams = [];
  let loading = true;
  let selectedLeague = getSavedLeague(39);
  let searchQuery = "";
  let season = getCurrentSeason();
  let showLeagueSelector = false;

  async function loadTeams(leagueId) {
    loading = true;
    selectedLeague = leagueId;
    saveLeague(leagueId);
    try {
      const res = await fetch(
        `${API_URL}/api/teams?league=${leagueId}&season=${season}`,
      );
      const data = await res.json();
      // Force Svelte reactivity by creating a new array reference
      teams = [...(data.response || [])];
    } catch (e) {
      console.error("Error loading teams:", e);
      teams = [];
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    // Load teams for the saved league preference (defaults to 39 if none saved)
    loadTeams(selectedLeague);
  });

  $: filteredTeams = teams.filter((item) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const name = item.team.name.toLowerCase();
    const code = item.team.code ? item.team.code.toLowerCase() : "";
    return name.includes(q) || code.includes(q);
  });

  $: currentLeague =
    leagues.find((l) => l.id === selectedLeague) ||
    leagues.find((l) => l.id === 39);

  function handleClickOutside(event) {
    if (showLeagueSelector && !event.target.closest(".league-selector")) {
      showLeagueSelector = false;
    }
  }
</script>

<SEOHead data={seoData} />

<svelte:window on:click={handleClickOutside} />

<div class="space-y-6 page-enter">
  <div class="flex flex-col gap-3 mb-2 element-enter relative z-50">
    <div class="flex justify-between items-center gap-3">
      <h2 class="text-2xl font-bold">{$_('nav.teams')}</h2>

      <!-- League Selector Dropdown -->
      <div class="league-selector relative z-[100]">
        <button
          class="league-selector-btn flex items-center gap-2 px-4 py-2.5 bg-white/10 rounded-lg hover:bg-white/15 transition-all touch-target"
          on:click|stopPropagation={() =>
            (showLeagueSelector = !showLeagueSelector)}
        >
          <span class="text-lg">{currentLeague?.emoji}</span>
          <span class="font-medium">{currentLeague?.name}</span>
          <svg
            class="w-4 h-4 transition-transform {showLeagueSelector
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

        {#if showLeagueSelector}
          <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
          <div
            class="league-dropdown absolute right-0 top-full mt-2 w-64 max-h-80 overflow-y-auto bg-slate-900 border border-white/20 rounded-xl shadow-2xl z-[200]" style="pointer-events: auto;"
            on:click|stopPropagation
          >
            <!-- European -->
            <div class="p-2 border-b border-white/10">
              <div class="text-xs text-slate-400 px-2 py-1 font-bold">
                🏆 {$_('fixtures.europeanComps')}
              </div>
              {#each leagues.filter((l) => l.tier === 0) as league}
                <button
                  type="button"
                  class="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/10 transition-all {selectedLeague ===
                  league.id
                    ? 'bg-accent/20 text-accent'
                    : ''}"
                  on:click={() => {
                    loadTeams(league.id);
                    showLeagueSelector = false;
                  }}
                >
                  <span>{league.emoji}</span>
                  <span>{league.name}</span>
                </button>
              {/each}
            </div>
            <!-- Top Leagues -->
            <div class="p-2 border-b border-white/10">
              <div class="text-xs text-slate-400 px-2 py-1 font-bold">
                ⭐ {$_('fixtures.topLeagues')}
              </div>
              {#each leagues.filter((l) => l.tier === 1) as league}
                <button
                  type="button"
                  class="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/10 transition-all {selectedLeague ===
                  league.id
                    ? 'bg-accent/20 text-accent'
                    : ''}"
                  on:click={() => {
                    loadTeams(league.id);
                    showLeagueSelector = false;
                  }}
                >
                  <span>{league.emoji}</span>
                  <span>{league.name}</span>
                </button>
              {/each}
            </div>
            <!-- More Leagues -->
            <div class="p-2 border-b border-white/10">
              <div class="text-xs text-slate-400 px-2 py-1 font-bold">
                🌐 MORE LEAGUES
              </div>
              {#each leagues.filter((l) => l.tier === 2) as league}
                <button
                  type="button"
                  class="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/10 transition-all {selectedLeague ===
                  league.id
                    ? 'bg-accent/20 text-accent'
                    : ''}"
                  on:click={() => {
                    loadTeams(league.id);
                    showLeagueSelector = false;
                  }}
                >
                  <span>{league.emoji}</span>
                  <span>{league.name}</span>
                </button>
              {/each}
            </div>
            <!-- Domestic Cups -->
            <div class="p-2">
              <div class="text-xs text-slate-400 px-2 py-1 font-bold">
                🏆 DOMESTIC CUPS
              </div>
              {#each leagues.filter((l) => l.tier === 3) as league}
                <button
                  type="button"
                  class="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/10 transition-all {selectedLeague ===
                  league.id
                    ? 'bg-orange-500/20 text-orange-400'
                    : ''}"
                  on:click={() => {
                    loadTeams(league.id);
                    showLeagueSelector = false;
                  }}
                >
                  <span>{league.emoji}</span>
                  <span>{league.name}</span>
                </button>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </div>
    <SearchBar bind:searchQuery {selectedLeague} />
  </div>

  {#if loading}
    <div class="text-center py-20">
      <div class="inline-block w-12 h-12 border-4 border-accent border-t-transparent rounded-full animate-spin mb-4"></div>
      <p class="text-slate-400">{$_('teams.loading')}</p>
    </div>
  {:else if filteredTeams.length === 0}
    <div class="glass-card p-12 text-center">
      <div class="text-6xl mb-4">🔍</div>
      <p class="text-xl font-bold mb-2">{$_('teams.noTeams')}</p>
      <p class="text-slate-400">{$_('teams.adjustSearch')}</p>
    </div>
  {:else}
    <!-- Team count and view info -->
    <div class="flex items-center justify-between mb-4">
      <p class="text-sm text-slate-400">
        Showing {filteredTeams.length} of {teams.length} teams
        {#if searchQuery.trim()}
          for "{searchQuery}"
        {/if}
      </p>
    </div>

    <div
      class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4 element-enter stagger-1 relative z-0"
    >
      {#each filteredTeams as item}
        <Link
          to={`/team/${item.team.id}?league=${selectedLeague}`}
          class="glass-card p-4 flex flex-col items-center justify-center gap-3 hover:bg-white/10 hover:border-accent/30 hover:scale-[1.02] transition-all duration-200 team-card group relative overflow-hidden"
        >
          <!-- Hover glow effect -->
          <div class="absolute inset-0 bg-gradient-to-t from-accent/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>

          <div class="relative">
            <img
              src={item.team.logo}
              alt={item.team.name}
              class="w-16 h-16 md:w-20 md:h-20 object-contain drop-shadow-lg group-hover:scale-110 transition-transform duration-200"
            />
          </div>

          <div class="text-center w-full relative z-10">
            <span class="font-bold text-sm md:text-base line-clamp-2 group-hover:text-accent transition-colors">{item.team.name}</span>

            {#if item.team.code}
              <span class="block text-xs text-slate-500 mt-0.5">{item.team.code}</span>
            {/if}
          </div>

          {#if item.venue?.name}
            <div class="flex items-center gap-1 text-[10px] md:text-xs text-slate-500 w-full justify-center relative z-10">
              <svg class="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
              <span class="truncate">{item.venue.name}</span>
            </div>
          {/if}

          <!-- Capacity badge on hover -->
          {#if item.venue?.capacity}
            <div class="absolute top-2 right-2 px-2 py-0.5 rounded-full bg-white/10 text-[10px] text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity">
              {item.venue.capacity.toLocaleString()} seats
            </div>
          {/if}
        </Link>
      {/each}
    </div>
  {/if}
</div>
