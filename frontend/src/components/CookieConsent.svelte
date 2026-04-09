<script>
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';

  let showBanner = false;
  let showPreferences = false;

  const COOKIE_KEY = 'fixturecast_cookie_consent';

  onMount(() => {
    const consent = localStorage.getItem(COOKIE_KEY);
    if (!consent) {
      showBanner = true;
    }
  });

  function acceptAll() {
    localStorage.setItem(COOKIE_KEY, JSON.stringify({
      essential: true,
      analytics: true,
      timestamp: new Date().toISOString()
    }));
    showBanner = false;
  }

  function acceptEssential() {
    localStorage.setItem(COOKIE_KEY, JSON.stringify({
      essential: true,
      analytics: false,
      timestamp: new Date().toISOString()
    }));
    showBanner = false;
  }

  function openPreferences() {
    showPreferences = true;
  }

  function closePreferences() {
    showPreferences = false;
  }
</script>

{#if showBanner}
  <div class="fixed bottom-16 md:bottom-0 left-0 right-0 z-50 p-4 bg-slate-900/95 backdrop-blur-md border-t border-slate-700">
    <div class="container mx-auto max-w-4xl">
      <div class="flex flex-col md:flex-row items-start md:items-center gap-4">
        <div class="flex-1">
          <h3 class="font-semibold text-white mb-1">{$_('cookieConsent.bannerTitle')}</h3>
          <p class="text-sm text-slate-300">
            {$_('cookieConsent.bannerText')}
            <button on:click={openPreferences} class="text-cyan-400 hover:underline ml-1">{$_('cookieConsent.learnMore')}</button>
          </p>
        </div>
        <div class="flex gap-2 shrink-0">
          <button
            on:click={acceptEssential}
            class="px-4 py-2 text-sm border border-slate-600 text-slate-300 rounded-lg hover:bg-slate-800 transition-colors"
          >
            {$_('cookieConsent.essentialOnly')}
          </button>
          <button
            on:click={acceptAll}
            class="px-4 py-2 text-sm bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors"
          >
            {$_('cookieConsent.acceptAll')}
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

{#if showPreferences}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
    <div class="bg-slate-800 rounded-xl max-w-lg w-full p-6 border border-slate-700">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-xl font-bold text-white">{$_('cookieConsent.preferencesTitle')}</h2>
        <button on:click={closePreferences} class="text-slate-400 hover:text-white text-2xl">&times;</button>
      </div>

      <div class="space-y-4 mb-6">
        <div class="p-4 bg-slate-700/50 rounded-lg">
          <div class="flex justify-between items-center">
            <div>
              <h4 class="font-medium text-white">{$_('cookieConsent.essentialTitle')}</h4>
              <p class="text-sm text-slate-400">{$_('cookieConsent.essentialDesc')}</p>
            </div>
            <span class="text-sm text-cyan-400">{$_('cookieConsent.alwaysOn')}</span>
          </div>
        </div>

        <div class="p-4 bg-slate-700/50 rounded-lg">
          <div class="flex justify-between items-center">
            <div>
              <h4 class="font-medium text-white">{$_('cookieConsent.analyticsTitle')}</h4>
              <p class="text-sm text-slate-400">{$_('cookieConsent.analyticsDesc')}</p>
            </div>
            <span class="text-sm text-slate-400">{$_('cookieConsent.optional')}</span>
          </div>
        </div>
      </div>

      <div class="flex gap-2 justify-end">
        <button
          on:click={() => { acceptEssential(); closePreferences(); }}
          class="px-4 py-2 text-sm border border-slate-600 text-slate-300 rounded-lg hover:bg-slate-700"
        >
          {$_('cookieConsent.essentialOnly')}
        </button>
        <button
          on:click={() => { acceptAll(); closePreferences(); }}
          class="px-4 py-2 text-sm bg-cyan-600 text-white rounded-lg hover:bg-cyan-700"
        >
          {$_('cookieConsent.acceptAll')}
        </button>
      </div>
    </div>
  </div>
{/if}
