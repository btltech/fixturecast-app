<script>
  import { Link } from "svelte-routing";
  import { accaSlip, removeSelection, clearSlip } from "../services/accaStore.js";
  import { accaSummary, selectionOdds, potentialReturn } from "../services/accaBuilder.js";

  let stake = 10;

  $: summary = accaSummary($accaSlip);
  $: returns = potentialReturn(stake, summary.combinedOdds);

  const title = "Accumulator Builder | FixtureCast";
  const description =
    "Build your own football accumulator from FixtureCast AI predictions. See the combined probability, combined odds and potential returns for your bet slip.";
</script>

<svelte:head>
  <title>{title}</title>
  <meta name="description" content={description} />
  <link rel="canonical" href="https://fixturecast.com/acca-builder" />
</svelte:head>

<div class="max-w-3xl mx-auto px-4 py-8">
  <div class="flex items-center justify-between mb-2">
    <h1 class="text-3xl font-bold text-white">🎲 Accumulator Builder</h1>
    {#if $accaSlip.length > 0}
      <button class="text-sm text-rose-400 hover:underline" on:click={clearSlip}>Clear all</button>
    {/if}
  </div>
  <p class="text-slate-400 mb-6">
    Add picks from any prediction to build your own accumulator and see the combined odds.
  </p>

  {#if $accaSlip.length === 0}
    <div class="glass-card p-10 text-center">
      <div class="text-5xl mb-3">🧮</div>
      <h2 class="text-xl font-semibold text-white mb-2">Your slip is empty</h2>
      <p class="text-slate-400 mb-5">
        Open a match prediction and tap “Add to accumulator” to start building.
      </p>
      <Link to="/ai" class="inline-block px-6 py-3 rounded-xl bg-gradient-to-r from-primary to-cyan-500 text-white font-bold">
        Browse predictions →
      </Link>
    </div>
  {:else}
    <!-- Selections -->
    <div class="space-y-2 mb-6">
      {#each $accaSlip as sel (sel.id)}
        <div class="glass-card p-3 flex items-center justify-between gap-3">
          <div class="min-w-0">
            <div class="font-medium text-white truncate">{sel.label}</div>
            {#if sel.fixture}<div class="text-xs text-slate-400 truncate">{sel.fixture}</div>{/if}
          </div>
          <div class="flex items-center gap-3 flex-shrink-0">
            <div class="text-right">
              <div class="text-sm font-bold text-cyan-300">{selectionOdds(sel).toFixed(2)}</div>
              {#if typeof sel.prob === "number"}
                <div class="text-[11px] text-slate-500">{(sel.prob * 100).toFixed(0)}%</div>
              {/if}
            </div>
            <button
              class="text-slate-400 hover:text-rose-400 text-lg leading-none"
              aria-label="Remove selection"
              on:click={() => removeSelection(sel.id)}
            >✕</button>
          </div>
        </div>
      {/each}
    </div>

    <!-- Summary -->
    <div class="glass-card p-5">
      <div class="grid grid-cols-3 gap-4 text-center mb-5">
        <div>
          <div class="text-xs text-slate-400 uppercase tracking-wide">Legs</div>
          <div class="text-2xl font-bold text-white">{summary.count}</div>
        </div>
        <div>
          <div class="text-xs text-slate-400 uppercase tracking-wide">Combined odds</div>
          <div class="text-2xl font-bold text-cyan-300">{summary.combinedOdds.toFixed(2)}</div>
        </div>
        <div>
          <div class="text-xs text-slate-400 uppercase tracking-wide">Model chance</div>
          <div class="text-2xl font-bold text-white">{(summary.combinedProb * 100).toFixed(1)}%</div>
        </div>
      </div>

      <div class="flex items-center gap-3 mb-2">
        <label for="stake" class="text-sm text-slate-300">Stake</label>
        <input
          id="stake"
          type="number"
          min="0"
          step="1"
          bind:value={stake}
          class="w-28 px-3 py-2 bg-white/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent text-white"
        />
        <span class="text-slate-400">→ potential return</span>
        <span class="text-xl font-bold text-emerald-400 ml-auto">{returns.toFixed(2)}</span>
      </div>

      {#if summary.fairOdds > 0}
        <p class="text-xs text-slate-500 mt-3">
          Model-fair odds for this slip would be {summary.fairOdds.toFixed(2)}.
          {#if summary.hasEdge}
            <span class="text-emerald-400">The book odds beat the model — potential value.</span>
          {/if}
        </p>
      {/if}
    </div>
  {/if}

  <p class="text-xs text-slate-500 mt-6 text-center">
    18+ · For information and entertainment only, not betting advice. The longer the
    accumulator, the lower the chance all legs land. Please gamble responsibly.
  </p>
</div>
