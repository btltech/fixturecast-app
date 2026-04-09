<script>
  import { onMount } from 'svelte';
  import { Link } from 'svelte-routing';
  import { _ } from 'svelte-i18n';
  import { BACKEND_API_URL } from '../config.js';

  let accumulator = null;
  let loading = true;
  let error = false;

  const accaInfo = {
    '8-fold': {
      icon: '🎯',
      color: 'from-blue-500 to-purple-600',
      titleKey: 'dailyAccas.accaTypes.8fold.title',
      descriptionKey: 'dailyAccas.accaTypes.8fold.description'
    },
    '4-fold': {
      icon: '💎',
      color: 'from-green-500 to-emerald-600',
      titleKey: 'dailyAccas.accaTypes.4fold.title',
      descriptionKey: 'dailyAccas.accaTypes.4fold.description'
    },
    'BTTS': {
      icon: '⚽',
      color: 'from-orange-500 to-red-600',
      titleKey: 'dailyAccas.accaTypes.btts.title',
      descriptionKey: 'dailyAccas.accaTypes.btts.description'
    }
  };

  onMount(async () => {
    try {
      const response = await fetch(`${BACKEND_API_URL}/api/accumulators/today`);
      if (!response.ok) {
        error = true;
        return;
      }

      const data = await response.json();
      if (data.success && data.accumulators && data.accumulators.length > 0) {
        // Feature the first available accumulator
        accumulator = data.accumulators[0];
      } else {
        error = true;
      }
    } catch (err) {
      console.error('Error fetching accumulator:', err);
      error = true;
    } finally {
      loading = false;
    }
  });

</script>

{#if !loading && accumulator}
  {@const info = accaInfo[accumulator.acca_type]}
  <div class="relative content-enter">
    <div class="flex items-center justify-between mb-6 px-2">
      <div class="flex items-center gap-3">
        <div class="p-2 bg-gradient-to-br {info.color} rounded-lg text-white shadow-lg">
          <span class="text-2xl">{info.icon}</span>
        </div>
        <div>
          <h2 class="text-2xl font-display font-bold text-white">
            {$_('accumulatorCard.title')}
          </h2>
          <p class="text-sm text-slate-400">{$_(info.descriptionKey)}</p>
        </div>
      </div>
      <Link
        to="/accumulators"
        class="text-sm font-medium text-primary hover:text-primary/80 transition-colors hidden sm:block"
      >
        {$_('accumulatorCard.viewAllAccas')} &rarr;
      </Link>
    </div>

    <Link
      to="/accumulators"
      class="block group relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 to-slate-950 border border-white/10 hover:border-primary/50 transition-all duration-500 hover:shadow-2xl hover:shadow-primary/10"
    >
      <!-- Background Glow -->
      <div class="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full bg-gradient-to-br {info.color} opacity-5 group-hover:opacity-10 transition-opacity"></div>

      <div class="relative p-6 md:p-8">
        <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <!-- Left: Type & Stats -->
          <div class="flex-1">
            <div class="flex items-center gap-3 mb-4">
              <span class="text-4xl">{info.icon}</span>
              <div>
                <h3 class="text-2xl font-bold text-white">{$_(info.titleKey)}</h3>
                <p class="text-sm text-slate-400">{$_('accumulatorCard.selectionCount', { values: { count: accumulator.selections?.length || 0 } })}</p>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div class="bg-white/5 rounded-xl p-4 border border-white/10">
                <div class="text-sm text-slate-400 mb-1">{$_('dailyAccas.selections')}</div>
                <div class="text-3xl font-bold text-white">{accumulator.selections?.length || 0}</div>
              </div>
              <div class="bg-gradient-to-br {info.color} bg-opacity-10 rounded-xl p-4 border border-white/10">
                <div class="text-sm text-slate-300 mb-1">{$_('accumulatorCard.aiPicks')}</div>
                <div class="text-3xl font-bold text-white">{$_('common.today')}</div>
              </div>
            </div>
          </div>

          <!-- Right: Quick Preview -->
          <div class="w-full md:w-80">
            <div class="bg-white/5 rounded-xl p-4 border border-white/10">
              <div class="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
                </svg>
                {$_('accumulatorCard.matchSelections')}
              </div>
              <div class="space-y-2 max-h-40 overflow-y-auto">
                {#each (accumulator.selections || []).slice(0, 4) as selection}
                  <div class="text-sm bg-white/5 rounded-lg p-2 flex items-center justify-between">
                    <span class="text-slate-300 truncate flex-1">
                      {selection.home_team} vs {selection.away_team}
                    </span>
                  </div>
                {/each}
                {#if (accumulator.selections?.length || 0) > 4}
                  <div class="text-xs text-slate-400 text-center pt-1">
                    {$_('accumulatorCard.moreMatches', { values: { count: accumulator.selections.length - 4 } })}
                  </div>
                {/if}
              </div>
            </div>
          </div>
        </div>

        <div class="mt-6 flex items-center justify-between">
          <div class="text-xs text-slate-500">
            <span class="inline-flex items-center gap-1">
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
              </svg>
              {$_('accumulatorCard.aiGenerated')}
            </span>
          </div>
          <span class="inline-flex items-center gap-2 px-4 py-2 bg-primary/10 hover:bg-primary/20 border border-primary/20 rounded-full text-primary font-bold text-sm transition-all group-hover:scale-105">
            {$_('accumulatorCard.viewFullDetails')}
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
            </svg>
          </span>
        </div>
      </div>
    </Link>

    <!-- Mobile View All Link -->
    <div class="sm:hidden mt-4 text-center">
      <Link
        to="/accumulators"
        class="text-sm font-medium text-primary hover:text-primary/80 transition-colors"
      >
        {$_('accumulatorCard.viewAll')} &rarr;
      </Link>
    </div>
  </div>
{/if}

<style>
  :global(body) {
    overflow-x: hidden;
  }
</style>
