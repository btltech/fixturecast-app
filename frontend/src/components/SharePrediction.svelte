<script>
  import { get } from "svelte/store";
  import { _ } from "svelte-i18n";

  export let match;
  export let prediction;
  export let analysis = null;

  let showMenu = false;
  let copied = false;
  let toastMessage = "";

  function showToast(message) {
    toastMessage = message;
    setTimeout(() => {
      toastMessage = "";
    }, 2200);
  }

  function t(key, values) {
    return get(_)(key, values ? { values } : undefined);
  }

  // Get the prediction URL for this specific fixture
  function getPredictionUrl() {
    const fixtureId = match.fixture?.id || prediction?.fixture_id;
    const leagueId = match.league?.id || prediction?.league_id || 39;
    if (fixtureId) {
      return `https://fixturecast.com/prediction/${fixtureId}?league=${leagueId}`;
    }
    return "https://fixturecast.com";
  }

  // Strip markdown/HTML for plain text
  function stripFormatting(text) {
    if (!text) return '';
    return text
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/\*(.*?)\*/g, '$1')
      .replace(/<[^>]*>/g, '')
      .replace(/•\s*/g, '- ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  // Summarize analysis to ~100 chars for Twitter
  function summarizeAnalysis(maxLen = 100) {
    if (!analysis) return '';

    const clean = stripFormatting(analysis);
    if (!clean) return '';

    // Try to get the first sentence
    const firstSentenceMatch = clean.match(/^[^.!?]+[.!?]/);
    if (firstSentenceMatch && firstSentenceMatch[0].length <= maxLen) {
      return firstSentenceMatch[0].trim();
    }

    // Otherwise truncate at word boundary
    if (clean.length <= maxLen) return clean;

    const truncated = clean.slice(0, maxLen);
    const lastSpace = truncated.lastIndexOf(' ');
    return (lastSpace > 50 ? truncated.slice(0, lastSpace) : truncated) + '...';
  }

  // Generate Twitter/X text with full prediction + analysis (X Premium allows 25,000 chars)
  function generateTwitterText() {
    if (!prediction) return "";

    const home = match.teams.home.name;
    const away = match.teams.away.name;
    const league = match.league?.name || t("share.defaultLeague");
    const score = prediction.predicted_scoreline || "?-?";

    const homeProb = (prediction.home_win_prob * 100).toFixed(0);
    const drawProb = (prediction.draw_prob * 100).toFixed(0);
    const awayProb = (prediction.away_win_prob * 100).toFixed(0);
    const btts = prediction.btts_prob ? (prediction.btts_prob * 100).toFixed(0) : null;
    const over25 = prediction.over25_prob ? (prediction.over25_prob * 100).toFixed(0) : null;

    // Determine predicted winner
    let winner, winProb;
    if (prediction.home_win_prob > prediction.away_win_prob && prediction.home_win_prob > prediction.draw_prob) {
      winner = home;
      winProb = homeProb;
    } else if (prediction.away_win_prob > prediction.home_win_prob && prediction.away_win_prob > prediction.draw_prob) {
      winner = away;
      winProb = awayProb;
    } else {
      winner = t("prediction.draw");
      winProb = drawProb;
    }

    // Full tweet with all details (X Premium: 25,000 char limit)
    let text = `🔮 ${t("share.header")}\n\n`;
    text += `⚽ ${home} ${t("common.vs")} ${away}\n`;
    text += `🏆 ${league}\n\n`;
    text += `📊 ${t("share.matchProbabilities")}:\n`;
    text += `   ${home}: ${homeProb}%\n`;
    text += `   ${t("prediction.draw")}: ${drawProb}%\n`;
    text += `   ${away}: ${awayProb}%\n\n`;
    text += `🎯 ${t("share.predictionLabel")}: ${winner} (${winProb}%)\n`;
    text += `📈 ${t("share.scoreLabel")}: ${score}\n`;

    if (btts) {
      text += `⚽ ${t("prediction.btts")}: ${parseInt(btts, 10) >= 50 ? t("share.yes") : t("share.no")} (${btts}%)\n`;
    }
    if (over25) {
      text += `📊 ${t("prediction.over25")}: ${parseInt(over25, 10) >= 50 ? t("share.yes") : t("share.no")} (${over25}%)\n`;
    }

    // Include full analysis
    if (analysis) {
      const cleanAnalysis = stripFormatting(analysis);
      if (cleanAnalysis) {
        text += `\n📝 ${t("share.analysisLabel")}:\n${cleanAnalysis}\n`;
      }
    }

    text += `\n🤖 ${t("share.generatedBy")}`;

    return text;
  }

  // Generate FULL share text for other platforms (WhatsApp, Telegram, Copy)
  function generateShareText() {
    if (!prediction) return "";

    const home = match.teams.home.name;
    const away = match.teams.away.name;
    const league = match.league?.name || t("share.defaultLeague");

    const homeProb = (prediction.home_win_prob * 100).toFixed(0);
    const drawProb = (prediction.draw_prob * 100).toFixed(0);
    const awayProb = (prediction.away_win_prob * 100).toFixed(0);
    const score = prediction.predicted_scoreline || "?-?";
    const btts = prediction.btts_prob ? (prediction.btts_prob * 100).toFixed(0) : null;
    const over25 = prediction.over25_prob ? (prediction.over25_prob * 100).toFixed(0) : null;

    let winner, winProb;
    if (prediction.home_win_prob > prediction.away_win_prob && prediction.home_win_prob > prediction.draw_prob) {
      winner = home;
      winProb = homeProb;
    } else if (prediction.away_win_prob > prediction.home_win_prob && prediction.away_win_prob > prediction.draw_prob) {
      winner = away;
      winProb = awayProb;
    } else {
      winner = t("prediction.draw");
      winProb = drawProb;
    }

    let text = `🔮 ${t("share.header")}\n\n`;
    text += `⚽ ${home} ${t("common.vs")} ${away}\n`;
    text += `🏆 ${league}\n\n`;
    text += `📊 ${t("share.matchProbabilities")}:\n`;
    text += `   ${home}: ${homeProb}%\n`;
    text += `   ${t("prediction.draw")}: ${drawProb}%\n`;
    text += `   ${away}: ${awayProb}%\n\n`;
    text += `🎯 ${t("share.predictionLabel")}: ${winner} (${winProb}%)\n`;
    text += `📈 ${t("share.scoreLabel")}: ${score}\n`;

    if (btts) {
      text += `⚽ ${t("prediction.btts")}: ${parseInt(btts, 10) >= 50 ? t("share.yes") : t("share.no")} (${btts}%)\n`;
    }
    if (over25) {
      text += `📊 ${t("prediction.over25")}: ${parseInt(over25, 10) >= 50 ? t("share.yes") : t("share.no")} (${over25}%)\n`;
    }

    // Include full analysis for platforms without char limits
    if (analysis) {
      const cleanAnalysis = stripFormatting(analysis);
      if (cleanAnalysis) {
        text += `\n📝 ${t("share.analysisLabel")}:\n${cleanAnalysis}\n`;
      }
    }

    text += `\n🤖 ${t("share.generatedBy")}`;
    text += `\n${getPredictionUrl()}`;

    return text;
  }

  // Share URLs
  function getTwitterUrl() {
    const text = encodeURIComponent(generateTwitterText());
    const url = encodeURIComponent(getPredictionUrl());
    return `https://x.com/intent/tweet?text=${text}&url=${url}`;
  }

  function getWhatsAppUrl() {
    const text = encodeURIComponent(generateShareText());
    return `https://wa.me/?text=${text}`;
  }

  function getTelegramUrl() {
    const url = encodeURIComponent(getPredictionUrl());
    const text = encodeURIComponent(generateShareText());
    return `https://t.me/share/url?url=${url}&text=${text}`;
  }

  function getFacebookUrl() {
    const url = encodeURIComponent(getPredictionUrl());
    return `https://www.facebook.com/sharer/sharer.php?u=${url}&quote=${encodeURIComponent(generateShareText())}`;
  }

  async function copyToClipboard() {
    try {
      await navigator.clipboard.writeText(getPredictionUrl());
      copied = true;
      showToast($_("share.linkCopied"));
      setTimeout(() => copied = false, 2000);
    } catch (e) {
      console.error('Failed to copy:', e);
      showToast($_("share.copyFailed"));
    }
  }

  function share(platform) {
    let url;
    switch (platform) {
      case 'twitter':
        url = getTwitterUrl();
        break;
      case 'whatsapp':
        url = getWhatsAppUrl();
        break;
      case 'telegram':
        url = getTelegramUrl();
        break;
      case 'facebook':
        url = getFacebookUrl();
        break;
      case 'copy':
        copyToClipboard();
        return;
    }
    window.open(url, '_blank', 'width=600,height=400');
    showMenu = false;
  }

  // Native share API (mobile)
  async function nativeShare() {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `${match.teams.home.name} ${t("common.vs")} ${match.teams.away.name} - FixtureCast`,
          text: generateShareText(),
          url: getPredictionUrl()
        });
      } catch (e) {
        // AbortError = user cancelled intentionally — don't open dropdown
        // Any other error (NotAllowedError, etc.) = fall back to dropdown
        if (e.name !== 'AbortError') {
          showMenu = !showMenu;
        }
      }
    } else {
      showMenu = !showMenu;
    }
  }

  function handleClickOutside(event) {
    if (showMenu && !event.target.closest('.share-container')) {
      showMenu = false;
    }
  }

  $: hasAnalysis = analysis && stripFormatting(analysis).length > 0;
</script>

<svelte:window on:click={handleClickOutside} />

<div class="share-container relative">
  <button
    on:click={nativeShare}
    class="p-2 rounded-lg bg-accent/20 hover:bg-accent/30 text-accent transition-colors flex items-center gap-1.5 text-sm"
    title={$_("share.titleTooltip")}
  >
    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
    </svg>
    <span class="hidden sm:inline">{$_("prediction.share")}</span>
  </button>

  {#if toastMessage}
    <div class="absolute right-0 -top-12 bg-slate-900/95 border border-accent/30 text-white text-xs px-3 py-2 rounded-lg shadow-lg whitespace-nowrap z-50">
      {toastMessage}
    </div>
  {/if}

  {#if showMenu}
    <div class="absolute right-0 top-full mt-2 bg-slate-800 border border-white/10 rounded-lg shadow-xl z-50 min-w-[200px] overflow-hidden">

      <!-- Twitter/X -->
      <button
        on:click={() => share('twitter')}
        class="w-full px-4 py-3 flex items-center gap-3 hover:bg-white/10 transition-colors text-left"
      >
        <span class="text-lg">𝕏</span>
        <div class="flex flex-col">
          <span>{$_("share.platforms.twitter")}</span>
          <span class="text-xs text-slate-400">{hasAnalysis ? $_("share.withSummary") : $_("share.predictionOnly")}</span>
        </div>
      </button>

      <!-- WhatsApp -->
      <button
        on:click={() => share('whatsapp')}
        class="w-full px-4 py-3 flex items-center gap-3 hover:bg-white/10 transition-colors text-left"
      >
        <span class="text-lg">💬</span>
        <div class="flex flex-col">
          <span>{$_("share.platforms.whatsapp")}</span>
          <span class="text-xs text-slate-400">{hasAnalysis ? $_("share.fullAnalysis") : $_("share.fullPrediction")}</span>
        </div>
      </button>

      <!-- Telegram -->
      <button
        on:click={() => share('telegram')}
        class="w-full px-4 py-3 flex items-center gap-3 hover:bg-white/10 transition-colors text-left"
      >
        <span class="text-lg">✈️</span>
        <div class="flex flex-col">
          <span>{$_("share.platforms.telegram")}</span>
          <span class="text-xs text-slate-400">{hasAnalysis ? $_("share.fullAnalysis") : $_("share.fullPrediction")}</span>
        </div>
      </button>

      <!-- Facebook -->
      <button
        on:click={() => share('facebook')}
        class="w-full px-4 py-3 flex items-center gap-3 hover:bg-white/10 transition-colors text-left"
      >
        <span class="text-lg">📘</span>
        <span>{$_("share.platforms.facebook")}</span>
      </button>

      <div class="border-t border-white/10"></div>

      <!-- Copy -->
      <button
        on:click={() => share('copy')}
        class="w-full px-4 py-3 flex items-center gap-3 hover:bg-white/10 transition-colors text-left"
      >
        <span class="text-lg">{copied ? '✅' : '📋'}</span>
        <div class="flex flex-col">
          <span>{copied ? $_("share.copied") : $_("share.copyLink")}</span>
          <span class="text-xs text-slate-400">{$_("share.predictionLink")}</span>
        </div>
      </button>
    </div>
  {/if}
</div>
