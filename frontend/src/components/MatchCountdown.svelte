<script>
  import { get } from "svelte/store";
  import { _ } from "svelte-i18n";
  import { onMount, onDestroy } from "svelte";
  import { BACKEND_API_URL } from "../services/apiConfig.js";

  export let matchData = null; // Pass in match data or fetch automatically

  let countdown = "";
  let isLive = false;
  let matchStartTime = null;
  let interval;

  function t(key, values) {
    return get(_)(key, values ? { values } : undefined);
  }

  function formatCountdown(ms) {
    if (ms <= 0) {
      isLive = true;
      return t("matchCountdown.liveNow");
    }

    const hours = Math.floor(ms / (1000 * 60 * 60));
    const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((ms % (1000 * 60)) / 1000);

    if (hours > 24) {
      const days = Math.floor(hours / 24);
      return `${days}${t("matchCountdown.daysShort")} ${hours % 24}${t("matchCountdown.hoursShort")}`;
    } else if (hours > 0) {
      return `${hours}${t("matchCountdown.hoursShort")} ${minutes}${t("matchCountdown.minutesShort")}`;
    } else if (minutes > 15) {
      return `${minutes}${t("matchCountdown.minutesShort")}`;
    } else if (minutes > 0) {
      return `${minutes}${t("matchCountdown.minutesShort")} ${seconds}${t("matchCountdown.secondsShort")}`;
    } else {
      return `${seconds}${t("matchCountdown.secondsShort")}`;
    }
  }

  function updateCountdown() {
    if (!matchStartTime) return;

    const now = Date.now();
    const diff = matchStartTime - now;

    countdown = formatCountdown(diff);

    // Check if match is starting soon (< 15 mins)
    if (diff > 0 && diff < 15 * 60 * 1000) {
      isLive = false; // Show countdown in urgent mode
    }
  }

  async function fetchMatchOfTheDay() {
    try {
      const response = await fetch(`${BACKEND_API_URL}/api/match-of-the-day`);
      if (response.ok) {
        const data = await response.json();
        if (data.match_of_the_day) {
          matchData = data.match_of_the_day;
          matchStartTime = data.match_of_the_day.fixture.timestamp * 1000;
        }
      }
    } catch (err) {
      console.error("Failed to fetch match of the day:", err);
    }
  }

  onMount(async () => {
    if (!matchData) {
      await fetchMatchOfTheDay();
    } else if (matchData.fixture?.timestamp) {
      matchStartTime = matchData.fixture.timestamp * 1000;
    }

    updateCountdown();
    interval = setInterval(updateCountdown, 1000);
  });

  onDestroy(() => {
    if (interval) clearInterval(interval);
  });
</script>

{#if matchData && countdown}
  <div class="countdown-container">
    {#if isLive}
      <div
        class="live-badge animate-pulse bg-red-600 text-white px-3 py-1 rounded-full font-bold text-sm"
      >
        🔴 {countdown}
      </div>
    {:else}
      <div class="countdown-badge">
        <span class="countdown-label text-slate-400 text-xs">{$_("matchCountdown.kicksOffIn")}</span>
        <span
          class="countdown-time font-bold text-lg {matchStartTime - Date.now() <
          15 * 60 * 1000
            ? 'text-red-400 animate-pulse'
            : 'text-cyan-400'}"
        >
          {countdown}
        </span>
      </div>
    {/if}

    <div class="match-info mt-2">
      <div class="text-sm text-slate-300">
        <span class="font-semibold">{matchData.teams?.home?.name || $_("matchCountdown.tbd")}</span>
        <span class="text-slate-500 mx-2">{$_("common.vs")}</span>
        <span class="font-semibold">{matchData.teams?.away?.name || $_("matchCountdown.tbd")}</span>
      </div>
      <div class="text-xs text-slate-500 mt-1">
        {matchData.league?.name || ""}
      </div>
    </div>
  </div>
{/if}

<style>
  .countdown-container {
    text-align: center;
  }

  .countdown-badge {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
  }

  .live-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
  }
</style>
