<script>
  import { _ , locale } from "svelte-i18n";
  import { formatDate } from "../lib/i18n/format.js";
  import { reminders, toggleReminder } from "../services/remindersStore.js";

  export let fixture = null;
  export let fixtureId;
  export let homeTeam;
  export let awayTeam;
  export let kickoffTime;
  export let leagueName = "";
  export let compact = false;

  let isSet = false;
  let showTooltip = false;
  let animating = false;

  // Build fixture object from props if not provided
  $: fixtureData = fixture || {
    fixtureId,
    homeTeam,
    awayTeam,
    kickoffTime,
    leagueName
  };

  // Check if kickoff is in the future
  $: isFuture = new Date(fixtureData.kickoffTime) > new Date();

  // Subscribe to reminders store
  $: isSet = $reminders.some(r => r.fixtureId === fixtureData.fixtureId);

  function handleClick(e) {
    e.preventDefault();
    e.stopPropagation();

    if (!isFuture) return;

    // Check notification permission
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
          doToggle();
        }
      });
    } else {
      doToggle();
    }
  }

  function doToggle() {
    animating = true;
    toggleReminder(fixtureData);

    setTimeout(() => {
      animating = false;
    }, 300);
  }

  function formatReminderTime() {
    return formatDate(fixtureData.kickoffTime, $locale, {
      hour: "2-digit",
      minute: "2-digit"
    });
  }
</script>

{#if isFuture}
  <button
    on:click={handleClick}
    on:mouseenter={() => showTooltip = true}
    on:mouseleave={() => showTooltip = false}
    class="relative group transition-all duration-200
      {compact ? 'p-1.5' : 'p-2'}
      {isSet
        ? 'text-amber-400 hover:text-amber-300'
        : 'text-slate-400 hover:text-amber-400'
      }
      {animating ? 'scale-125' : ''}"
    title={isSet ? $_("reminder.remove") : $_("reminder.beforeKickoff")}
  >
    {#if isSet}
      <!-- Bell with ring -->
      <svg
        class="transition-transform {compact ? 'w-4 h-4' : 'w-5 h-5'} {animating ? 'animate-wiggle' : ''}"
        fill="currentColor"
        viewBox="0 0 24 24"
      >
        <path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
      </svg>
      <!-- Active indicator -->
      <span class="absolute -top-0.5 -right-0.5 w-2 h-2 bg-amber-400 rounded-full animate-pulse"></span>
    {:else}
      <!-- Bell outline -->
      <svg
        class="transition-transform {compact ? 'w-4 h-4' : 'w-5 h-5'}"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
      </svg>
    {/if}

    <!-- Tooltip -->
    {#if showTooltip}
      <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-slate-800 text-xs text-white rounded whitespace-nowrap z-50 pointer-events-none">
        {#if isSet}
          {$_("reminder.setForTime", { values: { time: formatReminderTime() } })}
        {:else}
          {$_("reminder.beforeShort")}
        {/if}
        <div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800"></div>
      </div>
    {/if}
  </button>
{/if}

<style>
  @keyframes wiggle {
    0%, 100% { transform: rotate(0deg); }
    25% { transform: rotate(-15deg); }
    75% { transform: rotate(15deg); }
  }

  :global(.animate-wiggle) {
    animation: wiggle 0.3s ease-in-out;
  }
</style>
