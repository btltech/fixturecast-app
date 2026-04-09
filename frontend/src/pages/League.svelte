<script>
  import SEOHead from "../components/SEOHead.svelte";
  import { generateLeagueSEO } from "../services/seoService.js";
  import { onMount } from "svelte";
  import { _, locale } from "svelte-i18n";
  import { Link } from "svelte-routing";
  import { API_URL } from "../config.js";
  import { getCurrentSeason } from "../services/season.js";
  import { getLeague } from "../services/leagues.js";
  import { formatDate } from "../lib/i18n/format.js";

  export let id;

  const leagueId = parseInt(id, 10);
  const league   = getLeague(leagueId);
  const season   = getCurrentSeason();

  $: seoData = league ? generateLeagueSEO(league) : null;

  let fixtures  = [];
  let loading   = true;
  let error     = null;

  onMount(async () => {
    if (!league) { loading = false; return; }
    try {
      const res = await fetch(
        `${API_URL}/api/fixtures?league=${leagueId}&season=${season}&next=8`
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      fixtures = (data.response || []).slice(0, 8);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  function formatFixtureDate(dateStr) {
    if (!dateStr) return "";
    return formatDate(dateStr, $locale, { weekday: "short", month: "short", day: "numeric" });
  }
  function formatTime(dateStr) {
    if (!dateStr) return "TBD";
    return formatDate(dateStr, $locale, { hour: "2-digit", minute: "2-digit" });
  }

  const TIER_BADGE = {
    0: { label: "FIFA / Continental", cls: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" },
    1: { label: "Top Division",        cls: "bg-accent/20 text-accent border-accent/30" },
    2: { label: "Second Division",     cls: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
    3: { label: "Cup Competition",     cls: "bg-orange-500/20 text-orange-400 border-orange-500/30" },
    4: { label: "Friendly",            cls: "bg-slate-500/20 text-slate-400 border-slate-500/30" },
  };
</script>

{#if seoData}
  <SEOHead data={seoData} />
{/if}

{#if !league}
  <!-- Unknown league -->
  <div class="text-center py-20 text-slate-400">
    <p class="text-5xl mb-4">⚽</p>
    <p class="text-xl font-semibold text-white mb-2">{$_("leaguePage.notFound")}</p>
    <p class="mb-6">{$_("leaguePage.notFoundDesc", { values: { id } })}</p>
    <Link to="/predictions" class="text-accent hover:underline">{$_("leaguePage.browseAll")} →</Link>
  </div>
{:else}
  {@const badge = TIER_BADGE[league.tier] ?? TIER_BADGE[1]}

  <!-- Hero -->
  <div class="mb-8">
    <div class="flex items-center gap-3 mb-2">
      <span class="text-5xl">{league.emoji}</span>
      <div>
        <h1 class="text-2xl md:text-3xl font-bold text-white">{league.name}</h1>
        <p class="text-slate-400 text-sm">{league.country}</p>
      </div>
    </div>
    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border {badge.cls}">
      {badge.label}
    </span>
  </div>

  <!-- Quick nav links -->
  <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
    <Link
      to="/predictions?league={leagueId}"
      class="flex flex-col items-center gap-1.5 p-4 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-accent/50 transition-all text-center"
    >
      <span class="text-2xl">🤖</span>
      <span class="text-sm font-medium text-white">{$_("nav.predictions")}</span>
    </Link>
    <Link
      to="/fixtures?league={leagueId}"
      class="flex flex-col items-center gap-1.5 p-4 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-accent/50 transition-all text-center"
    >
      <span class="text-2xl">📅</span>
      <span class="text-sm font-medium text-white">{$_("nav.fixtures")}</span>
    </Link>
    <Link
      to="/standings?league={leagueId}"
      class="flex flex-col items-center gap-1.5 p-4 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-accent/50 transition-all text-center"
    >
      <span class="text-2xl">📊</span>
      <span class="text-sm font-medium text-white">{$_("nav.standings")}</span>
    </Link>
    <Link
      to="/results?league={leagueId}"
      class="flex flex-col items-center gap-1.5 p-4 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-accent/50 transition-all text-center"
    >
      <span class="text-2xl">🏁</span>
      <span class="text-sm font-medium text-white">{$_("nav.results")}</span>
    </Link>
  </div>

  <!-- Upcoming fixtures -->
  <section>
    <h2 class="text-lg font-semibold text-white mb-4">{$_("leaguePage.upcomingFixtures")}</h2>

    {#if loading}
      <div class="space-y-3">
        {#each Array(4) as _}
          <div class="h-16 rounded-xl bg-slate-800 animate-pulse"></div>
        {/each}
      </div>
    {:else if error}
      <p class="text-slate-400 text-sm">{$_("leaguePage.loadFailed")}</p>
    {:else if fixtures.length === 0}
      <p class="text-slate-400 text-sm">{$_("leaguePage.noFixtures")}</p>
    {:else}
      <div class="space-y-2">
        {#each fixtures as f}
          {@const fixtureId = f.fixture?.id}
          {@const date      = f.fixture?.date}
          {@const home      = f.teams?.home}
          {@const away      = f.teams?.away}
          <Link
            to="/prediction/{fixtureId}?league={leagueId}"
            class="flex items-center justify-between px-4 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-accent/40 transition-all"
          >
            <!-- Teams -->
            <div class="flex items-center gap-2 min-w-0 flex-1">
              {#if home?.logo}
                <img src={home.logo} alt={home.name} class="w-6 h-6 object-contain flex-shrink-0" />
              {/if}
              <span class="text-sm text-white truncate">{home?.name}</span>
              <span class="text-xs text-slate-500 flex-shrink-0">{$_("common.vs")}</span>
              <span class="text-sm text-white truncate">{away?.name}</span>
              {#if away?.logo}
                <img src={away.logo} alt={away.name} class="w-6 h-6 object-contain flex-shrink-0" />
              {/if}
            </div>
            <!-- Date / time -->
            <div class="text-right flex-shrink-0 ml-3">
              <p class="text-xs text-slate-400">{formatFixtureDate(date)}</p>
              <p class="text-xs font-medium text-accent">{formatTime(date)}</p>
            </div>
          </Link>
        {/each}
      </div>
      <div class="mt-4">
        <Link
          to="/predictions?league={leagueId}"
          class="text-sm text-accent hover:underline"
        >
          {$_("leaguePage.viewAllPredictions", { values: { league: league.name } })} →
        </Link>
      </div>
    {/if}
  </section>
{/if}
