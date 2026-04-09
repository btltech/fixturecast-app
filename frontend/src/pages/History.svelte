<script>
  import SEOHead from "../components/SEOHead.svelte";
  import { generateHistorySEO } from "../services/seoService.js";
  import { onMount } from "svelte";
  import { _, locale } from "svelte-i18n";
  import { Link } from "svelte-routing";
  import { predictionHistory, clearHistory } from "../services/historyStore.js";
  import { formatDate } from "../lib/i18n/format.js";

  let seoData;
  $: seoData = generateHistorySEO($locale);

  // Use reactive auto-subscription ($ prefix) - automatically unsubscribes
  $: history = $predictionHistory || [];
</script>

<SEOHead data={seoData} />

<div class="space-y-6">
  <div class="glass-card p-6">
    <div class="flex justify-between items-center">
      <div>
        <h1 class="text-3xl font-bold mb-2">{$_("history.title")}</h1>
        <p class="text-slate-400">
          {$_("history.subtitle", { values: { count: history.length, max: 50 } })}
        </p>
      </div>
      {#if history.length > 0}
        <button
          on:click={clearHistory}
          class="px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-all"
        >
          {$_("history.clearAll")}
        </button>
      {/if}
    </div>
  </div>

  {#if history.length === 0}
    <div class="glass-card p-12 text-center">
      <div class="text-6xl mb-4">📊</div>
      <p class="text-slate-400">
        {$_("history.empty")}
      </p>
      <Link
        to="/ai"
        class="inline-block mt-4 px-6 py-3 bg-accent text-white rounded-lg hover:bg-accent/80 transition-all"
      >
        {$_("history.viewPredictions")}
      </Link>
    </div>
  {:else}
    <div class="space-y-4">
      {#each history as item}
        <div class="glass-card p-6 hover:bg-white/5 transition-all">
          <div class="flex items-center justify-between mb-4">
            <div class="text-sm text-slate-400">
              {$_("history.viewed")}: {formatDate(item.viewed_at, $locale, {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </div>
            <Link
              to={`/prediction/${item.fixture_id}?league=${item.league_id || 39}${item.season ? `&season=${item.season}` : ""}`}
              class="text-sm text-accent hover:underline"
            >
              {$_("history.viewAgain")} →
            </Link>
          </div>

          <div class="grid grid-cols-[1fr_auto_1fr] gap-4 items-center">
            <div class="text-right flex items-center justify-end gap-2">
              <div>
                <div class="font-bold text-lg">{item.home_team}</div>
                {#if item.home_win_prob}
                  <div class="text-sm text-slate-400">
                    {$_("history.winProb", { values: { count: (item.home_win_prob * 100).toFixed(0) } })}
                  </div>
                {/if}
              </div>
              {#if item.home_logo}
                <img
                  src={item.home_logo}
                  alt={item.home_team}
                  class="w-10 h-10"
                />
              {/if}
            </div>

            <div class="flex items-center gap-2">
              <div class="px-4 py-2 bg-white/10 rounded-lg text-sm font-mono">
                {item.predicted_score || $_("common.vs")}
              </div>
            </div>

            <div class="text-left flex items-center gap-2">
              {#if item.away_logo}
                <img
                  src={item.away_logo}
                  alt={item.away_team}
                  class="w-10 h-10"
                />
              {/if}
              <div>
                <div class="font-bold text-lg">{item.away_team}</div>
                {#if item.away_win_prob}
                  <div class="text-sm text-slate-400">
                    {$_("history.winProb", { values: { count: (item.away_win_prob * 100).toFixed(0) } })}
                  </div>
                {/if}
              </div>
            </div>
          </div>

          {#if item.confidence}
            <div class="mt-4 flex items-center gap-2">
              <span class="text-xs text-slate-400">{$_("prediction.confidence")}:</span>
              <div class="flex-1 bg-white/10 h-2 rounded-full overflow-hidden">
                <div
                  class="bg-accent h-full rounded-full"
                  style="width: {item.confidence * 100}%"
                ></div>
              </div>
              <span class="text-xs font-bold"
                >{(item.confidence * 100).toFixed(0)}%</span
              >
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>
