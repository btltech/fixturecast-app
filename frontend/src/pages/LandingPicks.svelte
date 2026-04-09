<script>
  import SEOHead from "../components/SEOHead.svelte";
  import { get } from "svelte/store";
  import { _, locale } from "svelte-i18n";
  import { generatePageSEO } from "../services/seoService.js";
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { API_URL, ML_API_URL } from "../config.js";
  import Logo from "../components/Logo.svelte";
  import { formatDate } from "../lib/i18n/format.js";

  let seoData;
  $: seoData = generatePageSEO(
    $_("landingPicks.seoTitle"),
    $_("landingPicks.seoDescription"),
    "/picks",
  );

  let email = "";
  let status = "idle"; // idle, loading, success, error
  let message = "";
  let showPicks = false;

  let todaysPicks = [];
  let loading = true;
  let accuracyStats = null;

  // Kit (ConvertKit) Form ID
  const KIT_FORM_ID = "8837042";

  function t(key, values) {
    return get(_)(key, values ? { values } : undefined);
  }

  onMount(async () => {
    // Fetch today's matches with predictions
    try {
      const res = await fetch(`${API_URL}/api/fixtures/today`);
      if (res.ok) {
        const data = await res.json();
        const matches = data.response || [];

        // Get predictions for first 4 matches
        const picks = [];
        for (const match of matches.slice(0, 4)) {
          try {
            const predRes = await fetch(
              `${ML_API_URL}/api/predict?fixture_id=${match.fixture.id}&league_id=${match.league?.id || 39}`,
            );
            if (predRes.ok) {
              const pred = await predRes.json();
              picks.push({
                match,
                prediction: pred,
              });
            }
          } catch (e) {
            // Skip this match
          }
        }
        todaysPicks = picks;
      }

      // Fetch accuracy stats
      const accRes = await fetch(`${ML_API_URL}/api/feedback/performance`);
      if (accRes.ok) {
        accuracyStats = await accRes.json();
      }
    } catch (e) {
      console.error("Error loading picks:", e);
    } finally {
      loading = false;
    }
  });

  async function handleSubmit(e) {
    e.preventDefault();
    if (!email || !email.includes("@")) {
      status = "error";
      message = $_("emailSignup.errors.invalidEmail");
      return;
    }

    status = "loading";

    try {
      const response = await fetch(
        `https://app.kit.com/forms/${KIT_FORM_ID}/subscriptions`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({ email_address: email }),
        },
      );

      if (!response.ok) {
        const altResponse = await fetch(
          `https://api.convertkit.com/v3/forms/${KIT_FORM_ID}/subscribe`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              api_key: import.meta.env.VITE_CONVERTKIT_API_KEY || "",
              email: email,
            }),
          },
        );
        if (!altResponse.ok) throw new Error("Subscription failed");
      }

      status = "success";
      message = $_("landingPicks.welcome");
      showPicks = true;
    } catch (err) {
      // Show picks anyway on API failure (good UX)
      status = "success";
      message = $_("landingPicks.welcome");
      showPicks = true;
    }
  }

  function getPredictionSummary(pred) {
    if (!pred) return null;
    const homeProb = pred.home_win_prob * 100;
    const drawProb = pred.draw_prob * 100;
    const awayProb = pred.away_win_prob * 100;

    if (homeProb > awayProb && homeProb > drawProb) {
      return { winner: "home", prob: homeProb, label: $_("landingPicks.home") };
    } else if (awayProb > homeProb && awayProb > drawProb) {
      return { winner: "away", prob: awayProb, label: $_("landingPicks.away") };
    }
    return { winner: "draw", prob: drawProb, label: $_("prediction.draw") };
  }

  function formatTime(dateStr) {
    return formatDate(dateStr, $locale, { hour: "2-digit", minute: "2-digit" });
  }
</script>

<SEOHead data={seoData} />

<div
  class="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950"
>
  <!-- Minimal Header -->
  <header
    class="px-6 py-4 flex items-center justify-between border-b border-white/5"
  >
    <Link to="/" class="flex-shrink-0">
      <Logo size={40} />
    </Link>
    <Link
      to="/"
      class="text-sm text-slate-400 hover:text-white transition-colors"
    >
      ← {$_("landingPicks.backToSite")}
    </Link>
  </header>

  <!-- Hero Section -->
  <section class="px-6 py-16 md:py-24 text-center max-w-3xl mx-auto">
    <!-- Badge -->
    <div
      class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-green-500/10 border border-green-500/30 text-sm font-medium text-green-400 mb-6"
    >
      <span class="relative flex h-2 w-2">
        <span
          class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
        ></span>
        <span class="relative inline-flex rounded-full h-2 w-2 bg-green-500"
        ></span>
      </span>
      {#if loading}
        {$_("landingPicks.loadingPicks")}
      {:else}
        {todaysPicks.length > 0
          ? t("landingPicks.matchesAnalyzed", { count: todaysPicks.length })
          : $_("landingPicks.updatedDaily")}
      {/if}
    </div>

    <!-- Main Headline -->
    <h1
      class="text-4xl sm:text-5xl md:text-6xl font-display font-bold text-white leading-tight mb-6"
    >
      {$_("landingPicks.heroTitle")}
      <span
        class="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500"
        >{$_("landingPicks.heroHighlight")}</span
      >
    </h1>

    <!-- Sub-headline -->
    <p class="text-xl text-slate-400 mb-10 max-w-xl mx-auto">
      {$_("landingPicks.heroSubtitle")}
    </p>

    <!-- CTA Form -->
    {#if status === "success"}
      <div class="glass-card p-6 max-w-md mx-auto border-green-500/30">
        <div class="flex items-center justify-center gap-2 text-green-400 mb-2">
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
              d="M5 13l4 4L19 7"
            />
          </svg>
          <span class="font-bold">{$_("landingPicks.youAreIn")}</span>
        </div>
        <p class="text-slate-300">{message}</p>
      </div>
    {:else}
      <form on:submit={handleSubmit} class="max-w-md mx-auto">
        <div class="flex flex-col sm:flex-row gap-3">
          <input
            type="email"
            bind:value={email}
            placeholder={$_("landingPicks.emailPlaceholder")}
            disabled={status === "loading"}
            class="flex-1 px-5 py-4 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 focus:ring-2 focus:ring-cyan-500/20 text-lg disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={status === "loading"}
            class="px-8 py-4 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-bold rounded-xl shadow-lg shadow-cyan-500/30 hover:shadow-cyan-500/50 transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {#if status === "loading"}
              <span class="inline-block animate-spin mr-2">⏳</span>
            {/if}
            {$_("landingPicks.getFreePicks")} →
          </button>
        </div>
        {#if status === "error"}
          <p class="text-red-400 text-sm mt-2">{message}</p>
        {/if}
        <p class="text-xs text-slate-500 mt-3">
          🔒 {$_("landingPicks.noSpam")}
        </p>
      </form>
    {/if}
  </section>

  <!-- Today's Picks Preview (shown after signup or as teaser) -->
  {#if showPicks || todaysPicks.length > 0}
    <section class="px-6 py-12 max-w-4xl mx-auto">
      <h2 class="text-2xl font-bold text-center mb-8 text-white">
        {showPicks ? `🎯 ${$_("landingPicks.todaysPicks")}` : `📊 ${$_("landingPicks.samplePredictions")}`}
      </h2>

      {#if loading}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          {#each Array(4) as _}
            <div class="glass-card p-4 animate-pulse">
              <div class="h-6 bg-white/10 rounded w-3/4 mb-3"></div>
              <div class="h-4 bg-white/10 rounded w-1/2"></div>
            </div>
          {/each}
        </div>
      {:else if todaysPicks.length > 0}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          {#each todaysPicks as { match, prediction }}
            {@const summary = getPredictionSummary(prediction)}
            <div
              class="glass-card p-4 hover:border-cyan-500/30 transition-all {!showPicks
                ? 'blur-sm hover:blur-none'
                : ''}"
            >
              <div class="flex items-center justify-between mb-3">
                <div class="flex items-center gap-2">
                  <img
                    src={match.teams.home.logo}
                    alt=""
                    class="w-6 h-6 object-contain"
                  />
                  <span class="text-white font-medium text-sm"
                    >{match.teams.home.name}</span
                  >
                </div>
                <span class="text-xs text-slate-500"
                  >{formatTime(match.fixture.date)}</span
                >
              </div>
              <div class="flex items-center gap-2 mb-3">
                <img
                  src={match.teams.away.logo}
                  alt=""
                  class="w-6 h-6 object-contain"
                />
                <span class="text-white font-medium text-sm"
                  >{match.teams.away.name}</span
                >
              </div>

              {#if showPicks && prediction}
                <div class="flex gap-2 mt-3 pt-3 border-t border-white/10">
                  <span
                    class="px-2 py-1 text-xs rounded bg-blue-500/20 text-blue-400"
                  >
                    {summary?.label}
                    {summary?.prob.toFixed(0)}%
                  </span>
                  <span
                    class="px-2 py-1 text-xs rounded {prediction.btts_yes_prob >
                    0.5
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-red-500/20 text-red-400'}"
                  >
                    {$_("prediction.btts")} {prediction.btts_yes_prob > 0.5 ? $_("share.yes") : $_("share.no")}
                  </span>
                  <span
                    class="px-2 py-1 text-xs rounded {prediction.over_25_prob >
                    0.5
                      ? 'bg-amber-500/20 text-amber-400'
                      : 'bg-slate-500/20 text-slate-400'}"
                  >
                    {prediction.over_25_prob > 0.5 ? "O2.5" : "U2.5"}
                  </span>
                </div>
              {:else}
                <div class="text-center py-2">
                  <span class="text-xs text-slate-500"
                    >{$_("landingPicks.subscribeToReveal")}</span
                  >
                </div>
              {/if}
            </div>
          {/each}
        </div>

        {#if showPicks}
          <div class="text-center mt-8">
            <Link
              to="/fixtures"
              class="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 rounded-xl text-white font-medium hover:bg-white/10 transition-all"
            >
              {$_("landingPicks.viewAllPredictions", { values: { count: todaysPicks.length > 4 ? "20+" : todaysPicks.length } })} →
            </Link>
          </div>
        {/if}
      {:else}
        <div class="text-center py-8 text-slate-400">
          <p>{$_("landingPicks.noMatchesToday")}</p>
        </div>
      {/if}
    </section>
  {/if}

  <!-- How It Works -->
  <section class="px-6 py-16 border-t border-white/5">
    <div class="max-w-4xl mx-auto">
      <h2 class="text-2xl font-bold text-center mb-12 text-white">
        {$_("landingPicks.howItWorks.title")}
      </h2>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div class="text-center">
          <div
            class="w-16 h-16 bg-cyan-500/10 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4"
          >
            📊
          </div>
          <h3 class="font-bold text-white mb-2">{$_("landingPicks.howItWorks.step1Title")}</h3>
          <p class="text-sm text-slate-400">
            {$_("landingPicks.howItWorks.step1Desc")}
          </p>
        </div>

        <div class="text-center">
          <div
            class="w-16 h-16 bg-blue-500/10 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4"
          >
            🎯
          </div>
          <h3 class="font-bold text-white mb-2">{$_("landingPicks.howItWorks.step2Title")}</h3>
          <p class="text-sm text-slate-400">
            {$_("landingPicks.howItWorks.step2Desc")}
          </p>
        </div>

        <div class="text-center">
          <div
            class="w-16 h-16 bg-purple-500/10 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4"
          >
            ⚡
          </div>
          <h3 class="font-bold text-white mb-2">{$_("landingPicks.howItWorks.step3Title")}</h3>
          <p class="text-sm text-slate-400">
            {$_("landingPicks.howItWorks.step3Desc")}
          </p>
        </div>
      </div>
    </div>
  </section>

  <!-- Social Proof -->
  <section class="px-6 py-16 border-t border-white/5 bg-white/[0.02]">
    <div class="max-w-4xl mx-auto">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
        <div>
          <div class="text-3xl font-bold text-cyan-400">
            {#if accuracyStats?.overall?.accuracy}
              {(accuracyStats.overall.accuracy * 100).toFixed(0)}%
            {:else}
              65%+
            {/if}
          </div>
          <div class="text-sm text-slate-400 mt-1">{$_("landingPicks.socialProof.matchAccuracy")}</div>
        </div>
        <div>
          <div class="text-3xl font-bold text-blue-400">11</div>
          <div class="text-sm text-slate-400 mt-1">{$_("landingPicks.socialProof.aiModels")}</div>
        </div>
        <div>
          <div class="text-3xl font-bold text-purple-400">14+</div>
          <div class="text-sm text-slate-400 mt-1">{$_("landingPicks.socialProof.leaguesCovered")}</div>
        </div>
        <div>
          <div class="text-3xl font-bold text-green-400">{$_("landingPicks.socialProof.free")}</div>
          <div class="text-sm text-slate-400 mt-1">{$_("landingPicks.socialProof.forever")}</div>
        </div>
      </div>

      <!-- Responsible Gambling -->
      <div
        class="mt-12 p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl text-center"
      >
        <p class="text-sm text-amber-400/90">
          ⚠️ <strong>18+</strong> • {$_("landingPicks.disclaimer")}
          <a
            href="https://www.begambleaware.org"
            target="_blank"
            rel="noopener"
            class="underline">BeGambleAware.org</a
          >
        </p>
      </div>
    </div>
  </section>

  <!-- Final CTA -->
  <section class="px-6 py-16 border-t border-white/5">
    <div class="max-w-md mx-auto text-center">
      <h2 class="text-2xl font-bold text-white mb-4">
        {$_("landingPicks.finalCta.title")}
      </h2>
      <p class="text-slate-400 mb-6">
        {$_("landingPicks.finalCta.subtitle")}
      </p>

      {#if status !== "success"}
        <form on:submit={handleSubmit} class="flex flex-col gap-3">
          <input
            type="email"
            bind:value={email}
            placeholder={$_("landingPicks.emailPlaceholder")}
            disabled={status === "loading"}
            class="px-5 py-4 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 text-center disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={status === "loading"}
            class="px-8 py-4 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-bold rounded-xl shadow-lg shadow-cyan-500/30 hover:shadow-cyan-500/50 transition-all disabled:opacity-50"
          >
            {$_("landingPicks.finalCta.subscribe")}
          </button>
        </form>
      {:else}
        <Link
          to="/fixtures"
          class="inline-block px-8 py-4 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-bold rounded-xl shadow-lg"
        >
          {$_("landingPicks.finalCta.explore")} →
        </Link>
      {/if}
    </div>
  </section>

  <!-- Minimal Footer -->
  <footer class="px-6 py-8 border-t border-white/5 text-center">
    <p class="text-xs text-slate-500">
      © {new Date().getFullYear()} FixtureCast •
      <Link to="/privacy" class="hover:text-white transition-colors"
        >{$_("nav.privacy")}</Link
      > •
      <Link to="/terms" class="hover:text-white transition-colors">{$_("nav.terms")}</Link>
    </p>
  </footer>
</div>

<style>
  .glass-card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 1rem;
    backdrop-filter: blur(10px);
  }
</style>
