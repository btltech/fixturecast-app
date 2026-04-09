<script>
  import { _, locale } from 'svelte-i18n';
  import { availableLocales, setLocale } from '../lib/i18n';

  let isOpen = false;

  $: currentLocale = availableLocales.find(l => l.code === $locale) || availableLocales[0];

  function selectLocale(code) {
    setLocale(code);
    isOpen = false;
  }

  function toggleDropdown() {
    isOpen = !isOpen;
  }

  // Close dropdown when clicking outside
  function handleClickOutside(event) {
    if (!event.target.closest('.language-switcher')) {
      isOpen = false;
    }
  }
</script>

<svelte:window on:click={handleClickOutside} />

<div class="language-switcher relative">
  <button
    on:click|stopPropagation={toggleDropdown}
    class="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors text-sm"
    aria-label={$_('common.selectLanguage')}
  >
    <span class="text-lg">{currentLocale.flag}</span>
    <span class="hidden sm:inline">{currentLocale.code.toUpperCase()}</span>
    <svg
      class="w-4 h-4 transition-transform {isOpen ? 'rotate-180' : ''}"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
    </svg>
  </button>

  {#if isOpen}
    <div
      class="absolute right-0 mt-2 w-40 bg-slate-800 rounded-lg shadow-xl border border-white/10 overflow-hidden z-50"
    >
      {#each availableLocales as loc}
        <button
          on:click={() => selectLocale(loc.code)}
          class="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/10 transition-colors text-left
            {loc.code === $locale ? 'bg-accent/20 text-accent' : 'text-white'}"
        >
          <span class="text-lg">{loc.flag}</span>
          <span class="text-sm">{loc.name}</span>
          {#if loc.code === $locale}
            <svg class="w-4 h-4 ml-auto" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>
          {/if}
        </button>
      {/each}
    </div>
  {/if}
</div>
