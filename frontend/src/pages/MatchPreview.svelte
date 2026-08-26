<script>
  import { onMount } from "svelte";
  import SEOHead from "../components/SEOHead.svelte";
  import { ML_API_URL, BACKEND_API_URL, mlApiFetch } from "../config.js";

  export let id = null;
  export let slug = null;

  let loading = true;
  let error = null;
  let prediction = null;
  let fixtureDetails = null;

  $: fixtureId = id || (slug ? slug.split("-").pop() : null);

  onMount(async () => {
    if (!fixtureId) {
      error = "Match ID not specified.";
      loading = false;
      return;
    }

    try {
      loading = true;
      const res = await mlApiFetch(`${ML_API_URL}/api/prediction/${fixtureId}`);
      if (!res.ok) throw new Error(`Match not found (${res.status})`);
      const data = await res.json();
      prediction = data.prediction || data;
      fixtureDetails = data.fixture_details || {};
    } catch (err) {
      console.error("Match fetch error:", err);
      error = "Unable to load match preview and predictions.";
    } finally {
      loading = false;
    }
  });

  $: homeTeam = fixtureDetails?.teams?.home?.name || prediction?.home_team || "Home Team";
  $: awayTeam = fixtureDetails?.teams?.away?.name || prediction?.away_team || "Away Team";
  $: league = fixtureDetails?.league?.name || prediction?.league || "Football League";
  $: kickoff = fixtureDetails?.fixture?.date || prediction?.match_date || "";
  $: matchTitle = `${homeTeam} vs ${awayTeam}`;

  $: seoData = {
    title: `${matchTitle} Prediction, Odds & AI Analysis | FixtureCast`,
    description: `AI-powered prediction for ${matchTitle} (${league}). Calibrated win probabilities, xG breakdown, head-to-head stats, and +EV betting edges.`,
    canonicalUrl: `https://fixturecast.com/match/${fixtureId}`,
  };

  $: jsonLd = {
    "@context": "https://schema.org",
    "@type": "SportsEvent",
    "name": matchTitle,
    "startDate": kickoff,
    "competitor": [
      { "@type": "SportsTeam", "name": homeTeam },
      { "@type": "SportsTeam", "name": awayTeam }
    ],
    "description": `AI prediction and value betting analysis for ${matchTitle} in ${league}.`
  };
</script>

<SEOHead
  title={seoData.title}
  description={seoData.description}
  canonicalUrl={seoData.canonicalUrl}
/>

<svelte:head>
  {@html `<script type="application/ld+json">${JSON.stringify(jsonLd)}</script>`}
</svelte:head>

<div class="max-w-4xl mx-auto px-4 py-8">
  {#if loading}
    <div class="flex flex-col items-center justify-center py-20 animate-pulse">
      <div class="w-12 h-12 rounded-full border-4 border-emerald-500 border-t-transparent animate-spin mb-4"></div>
      <p class="text-slate-400 text-sm font-medium">Analyzing team data and model ensemble...</p>
    </div>
  {:else if error}
    <div class="p-8 rounded-2xl bg-slate-900 border border-red-500/20 text-center text-red-400">
      <p class="font-bold text-lg mb-2">{error}</p>
      <a href="/" class="text-xs text-emerald-400 underline">Return to Live Fixtures</a>
    </div>
  {:else}
    <!-- Match Hero Header -->
    <div class="glass-card p-6 sm:p-8 rounded-3xl border border-white/10 bg-slate-900/80 shadow-2xl relative overflow-hidden mb-8">
      <div class="flex items-center justify-between gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">
        <span>{league}</span>
        <span>{kickoff ? new Date(kickoff).toLocaleString() : "Upcoming"}</span>
      </div>

      <div class="grid grid-cols-3 items-center text-center gap-4 py-4">
        <div>
          <h2 class="text-xl sm:text-3xl font-black text-white">{homeTeam}</h2>
          <div class="text-xs text-slate-400 mt-1 font-mono">
            {prediction?.home_win ? `${(prediction.home_win * 100).toFixed(1)}% Win Prob` : "Home"}
          </div>
        </div>

        <div class="space-y-1">
          <span class="px-3 py-1 rounded-full text-xs font-black bg-white/10 text-emerald-400 border border-white/10">VS</span>
          <div class="text-[11px] text-slate-500 font-mono">Draw: {prediction?.draw ? `${(prediction.draw * 100).toFixed(1)}%` : "—"}</div>
        </div>

        <div>
          <h2 class="text-xl sm:text-3xl font-black text-white">{awayTeam}</h2>
          <div class="text-xs text-slate-400 mt-1 font-mono">
            {prediction?.away_win ? `${(prediction.away_win * 100).toFixed(1)}% Win Prob` : "Away"}
          </div>
        </div>
      </div>
    </div>

    <!-- 7-Model Ensemble Consensus Grid -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
      <div class="p-5 rounded-2xl bg-slate-900/60 border border-white/10">
        <span class="text-xs uppercase font-bold text-slate-400 block mb-1">Match Winner (1X2)</span>
        <div class="text-lg font-black text-white">
          {(prediction?.home_win || 0) > (prediction?.away_win || 0) ? `${homeTeam} Favored` : `${awayTeam} Favored`}
        </div>
        <div class="text-xs text-emerald-400 mt-1 font-mono">
          Highest Confidence Model: GBDT + Elo
        </div>
      </div>

      <div class="p-5 rounded-2xl bg-slate-900/60 border border-white/10">
        <span class="text-xs uppercase font-bold text-slate-400 block mb-1">Both Teams To Score</span>
        <div class="text-lg font-black text-white">
          {(prediction?.btts_prob || 0) >= 0.52 ? "Yes (BTTS)" : "No"}
        </div>
        <div class="text-xs text-slate-400 mt-1 font-mono">
          Probability: {prediction?.btts_prob ? `${(prediction.btts_prob * 100).toFixed(1)}%` : "—"}
        </div>
      </div>

      <div class="p-5 rounded-2xl bg-slate-900/60 border border-white/10">
        <span class="text-xs uppercase font-bold text-slate-400 block mb-1">Over / Under 2.5 Goals</span>
        <div class="text-lg font-black text-white">
          {(prediction?.over25_prob || 0) >= 0.52 ? "Over 2.5 Goals" : "Under 2.5 Goals"}
        </div>
        <div class="text-xs text-slate-400 mt-1 font-mono">
          Probability: {prediction?.over25_prob ? `${(prediction.over25_prob * 100).toFixed(1)}%` : "—"}
        </div>
      </div>
    </div>
  {/if}
</div>
