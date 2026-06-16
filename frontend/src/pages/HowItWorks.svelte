<script>
  import { Link } from "svelte-routing";

  const title = "How FixtureCast Works — Our AI Football Prediction Method | FixtureCast";
  const description =
    "How FixtureCast generates AI football predictions: the data we use, our ensemble model, how we calibrate probabilities, and why we tell you when we don't have an edge.";
  const canonical = "https://fixturecast.com/how-it-works";
</script>

<svelte:head>
  <title>{title}</title>
  <meta name="description" content={description} />
  <link rel="canonical" href={canonical} />
  <meta property="og:title" content={title} />
  <meta property="og:description" content={description} />
  <meta property="og:type" content="website" />
  <meta property="og:url" content={canonical} />
</svelte:head>

<div class="max-w-4xl mx-auto px-4 py-8 text-slate-300 leading-relaxed">
  <Link to="/" class="text-cyan-400 hover:underline text-sm">← Back to Home</Link>

  <h1 class="text-3xl md:text-4xl font-bold text-white mt-4 mb-3">How FixtureCast Works</h1>
  <p class="text-slate-400 mb-8">
    No black box. Here's exactly how our football predictions are made — and how we keep
    ourselves honest about them.
  </p>

  <!-- TL;DR -->
  <div class="glass-card p-5 border border-cyan-500/30 mb-8">
    <h2 class="text-lg font-semibold text-cyan-300 mb-2">The short version</h2>
    <p>
      For each match we combine several statistical and machine-learning models into a
      single set of probabilities, calibrate them against real outcomes, and publish our
      track record so you can check us. When we don't have enough data to add real value —
      for example a national team we've never modelled — we say so instead of guessing.
    </p>
  </div>

  <!-- Step 1: Data -->
  <section class="mb-8">
    <h2 class="text-xl font-semibold text-white mb-3">1. The data</h2>
    <p>
      Across 90+ competitions we pull recent results, team form, head-to-head history,
      league standings, goals-for/against trends and live bookmaker odds. Odds matter:
      the betting market aggregates a huge amount of information, so we use it as one
      input rather than pretending it doesn't exist.
    </p>
  </section>

  <!-- Step 2: The model -->
  <section class="mb-8">
    <h2 class="text-xl font-semibold text-white mb-3">2. The model</h2>
    <p>
      Rather than relying on a single method, we run an <strong>ensemble</strong> — several
      independent models that each look at the game differently (long-run team strength,
      recent form, goal-scoring patterns, and more). Their outputs are combined into one
      probability for each outcome.
    </p>
    <p class="mt-3">
      Scorelines and goal markets (Both Teams to Score, Over/Under, Asian handicaps) are
      derived from a single coherent goal-distribution model based on the Dixon-Coles
      approach, so the markets never contradict each other — if we say Over 2.5 is 55%,
      Over 3.5 will always be lower, by construction.
    </p>
  </section>

  <!-- Step 3: Calibration & honesty -->
  <section class="mb-8">
    <h2 class="text-xl font-semibold text-white mb-3">3. Calibration &amp; honesty</h2>
    <p>
      A prediction that says "60%" should be right about 60% of the time. We
      <strong>calibrate</strong> our probabilities against real results and track how well
      "60%" calls actually land. You can see the numbers — accuracy, scoring metrics and a
      calibration curve — on our
      <Link to="/models" class="text-cyan-400 hover:underline">accuracy page</Link>.
    </p>
    <p class="mt-3">
      We also flag <strong>low-confidence</strong> and <strong>market-based</strong> picks.
      When we lack real team data (common for national teams in tournaments), we either
      abstain or clearly label the prediction as leaning on the market rather than a model
      edge — so you always know how much weight to give it.
    </p>
  </section>

  <!-- What we predict -->
  <section class="mb-8">
    <h2 class="text-xl font-semibold text-white mb-3">What we predict</h2>
    <p>
      Match result (1X2), predicted scoreline, Both Teams to Score, Over/Under goal lines,
      half-time markets and Asian handicaps — each with a probability and a confidence
      level.
    </p>
  </section>

  <!-- Disclaimer -->
  <div class="glass-card p-5 border border-amber-500/30 text-amber-200/90 mb-8">
    <h2 class="text-lg font-semibold text-amber-300 mb-2">Important</h2>
    <p>
      FixtureCast is for information and entertainment, not betting advice. Past accuracy
      doesn't guarantee future results. 18+ — please gamble responsibly. Support:
      BeGambleAware.org.
    </p>
  </div>

  <div class="flex flex-col sm:flex-row gap-3">
    <Link
      to="/ai"
      class="px-6 py-3 rounded-xl bg-gradient-to-r from-primary to-cyan-500 text-white font-bold text-center"
    >
      See today's predictions →
    </Link>
    <Link
      to="/models"
      class="px-6 py-3 rounded-xl bg-white/5 border border-white/10 text-white font-bold text-center hover:bg-white/10"
    >
      View our accuracy
    </Link>
  </div>
</div>
