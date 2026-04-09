<script>
  import { Link } from "svelte-routing";
  import { onMount } from "svelte";
  import { _, locale } from "svelte-i18n";
  import { API_URL } from "../config.js";
  import { getCurrentSeason } from "../services/season.js";
  import { formatDate } from "../lib/i18n/format.js";

  export let searchQuery = "";
  export let selectedLeague = null; // null = global search mode (Navbar); set to a league ID for scoped search

  let teams = [];
  let filteredTeams = [];
  let fixtures = [];
  let filteredFixtures = [];
  let showResults = false;
  let loading = false;
  let currentLeague = selectedLeague;
  let searchDebounce = null;
  const season = getCurrentSeason();

  // Load league-scoped fixtures/teams (used when selectedLeague is set)
  async function loadData(leagueId) {
    try {
      const [teamsRes, fixturesRes] = await Promise.all([
        fetch(`${API_URL}/api/teams?league=${leagueId}&season=${season}`),
        fetch(`${API_URL}/api/fixtures?league=${leagueId}&next=50&season=${season}`),
      ]);
      const teamsData = await teamsRes.json();
      const fixturesData = await fixturesRes.json();

      teams = teamsData.response || [];
      fixtures = fixturesData.response || [];
    } catch (err) {
      console.error("Failed to load search data:", err);
    }
  }

  // Cross-league team search via backend (used in global/Navbar mode)
  async function searchTeamsGlobal(query) {
    if (query.length < 2) return [];
    try {
      const res = await fetch(`${API_URL}/api/teams/search?q=${encodeURIComponent(query)}`);
      if (!res.ok) return [];
      const data = await res.json();
      return data.response || [];
    } catch {
      return [];
    }
  }

  // Reload data when selectedLeague changes (scoped mode only)
  $: if (selectedLeague && selectedLeague !== currentLeague) {
    currentLeague = selectedLeague;
    loadData(selectedLeague);
  }

  onMount(() => {
    if (selectedLeague) {
      loadData(selectedLeague);
    }
  });

  function handleSearch() {
    if (!searchQuery.trim()) {
      showResults = false;
      return;
    }

    // Scoped search (league-specific pages)
    if (selectedLeague) {
      const query = searchQuery.toLowerCase();
      filteredTeams = teams.filter(
        (t) =>
          t.team.name.toLowerCase().includes(query) ||
          t.team.code?.toLowerCase().includes(query)
      ).slice(0, 5);
      filteredFixtures = fixtures.filter(
        (f) =>
          f.teams.home.name.toLowerCase().includes(query) ||
          f.teams.away.name.toLowerCase().includes(query)
      ).slice(0, 5);
      showResults = true;
      return;
    }

    // Global search (Navbar) — debounce then hit the search API
    showResults = true;
    filteredFixtures = [];
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(async () => {
      if (!searchQuery.trim()) return;
      loading = true;
      const results = await searchTeamsGlobal(searchQuery.trim());
      filteredTeams = results.slice(0, 8);
      loading = false;
    }, 350);
  }

  function clearSearch() {
    searchQuery = "";
    showResults = false;
    filteredTeams = [];
    filteredFixtures = [];
  }
</script>

<div class="relative">
  <div class="relative">
    <input
      type="text"
      bind:value={searchQuery}
      on:input={handleSearch}
      on:focus={handleSearch}
      placeholder={$_('searchBar.placeholder')}
      class="w-full px-4 py-3 pl-12 bg-white/10 rounded-lg focus:bg-white/15 focus:outline-none focus:ring-2 focus:ring-accent search-input"
    />
    <div class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
      🔍
    </div>
    {#if searchQuery}
      <button
        on:click={clearSearch}
        class="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white btn-press"
      >
        ✕
      </button>
    {/if}
  </div>

  {#if showResults}
    <div
      class="absolute top-full mt-2 w-full bg-slate-900 border border-white/20 rounded-lg shadow-2xl max-h-96 overflow-y-auto z-50 search-results"
    >
      {#if loading}
        <div class="p-4 text-center text-slate-400">{$_('teams.loading')}</div>
      {:else if filteredTeams.length === 0 && filteredFixtures.length === 0}
        <div class="p-4 text-center text-slate-400">{$_('teams.noTeams')}</div>
      {:else}
        <!-- Teams -->
        {#if filteredTeams.length > 0}
          <div class="p-2 {selectedLeague ? 'border-b border-white/10' : ''}">
            <div class="text-xs text-slate-400 px-2 py-1 font-bold">{$_('searchBar.teamsSection')}</div>
            {#each filteredTeams as team}
              <Link
                to="/team/{team.team.id}{selectedLeague ? `?league=${selectedLeague}` : ''}"
                on:click={clearSearch}
                class="flex items-center gap-3 px-3 py-2 hover:bg-white/10 rounded-lg search-item"
              >
                <img
                  src={team.team.logo}
                  alt={team.team.name}
                  class="w-8 h-8"
                />
                <div>
                  <div class="font-medium">{team.team.name}</div>
                  {#if team.team.country}
                    <div class="text-xs text-slate-400">{team.team.country}</div>
                  {/if}
                </div>
              </Link>
            {/each}
          </div>
        {/if}

        <!-- Fixtures (scoped mode only) -->
        {#if selectedLeague && filteredFixtures.length > 0}
          <div class="p-2">
            <div class="text-xs text-slate-400 px-2 py-1 font-bold">
              {$_('searchBar.fixturesSection')}
            </div>
            {#each filteredFixtures as fixture}
              <Link
              to="/prediction/{fixture.fixture.id}?league={fixture.league?.id || selectedLeague}&season={season}"
                on:click={clearSearch}
                class="block px-3 py-2 hover:bg-white/10 rounded-lg search-item"
              >
                <div class="flex items-center justify-between gap-4">
                  <div class="flex items-center gap-2 flex-1">
                    <img
                      src={fixture.teams.home.logo}
                      alt={fixture.teams.home.name}
                      class="w-6 h-6"
                    />
                    <span class="text-sm">{fixture.teams.home.name}</span>
                  </div>
                  <span class="text-xs text-slate-400">{$_('common.vs')}</span>
                  <div class="flex items-center gap-2 flex-1 justify-end">
                    <span class="text-sm">{fixture.teams.away.name}</span>
                    <img
                      src={fixture.teams.away.logo}
                      alt={fixture.teams.away.name}
                      class="w-6 h-6"
                    />
                  </div>
                </div>
                <div class="text-xs text-slate-400 mt-1">
                  {formatDate(fixture.fixture.date, $locale, {
                    month: "short",
                    day: "numeric",
                    year: "numeric"
                  })}
                </div>
              </Link>
            {/each}
          </div>
        {/if}
      {/if}
    </div>
  {/if}
</div>
