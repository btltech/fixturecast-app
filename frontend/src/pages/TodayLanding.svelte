<script>
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import SEOHead from "../components/SEOHead.svelte";
  import AIRationaleCard from "../components/AIRationaleCard.svelte";
  import { API_URL } from "../config.js";

  let loading = true;
  let error = null;
  let data = null;

  // Session & Attribution tracking
  function getSessionId() {
    try {
      let sId = sessionStorage.getItem("fc_session_id");
      if (!sId) {
        sId = "s_" + Math.random().toString(36).substring(2, 11) + "_" + Date.now();
        sessionStorage.setItem("fc_session_id", sId);
      }
      return sId;
    } catch {
      return "s_anon_" + Date.now();
    }
  }

  async function trackEvent(eventType, extraData = {}) {
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const payload = {
        session_id: getSessionId(),
        event_type: eventType,
        path: window.location.pathname,
        utm_source: urlParams.get("utm_source") || "direct",
        utm_medium: urlParams.get("utm_medium") || "",
        utm_campaign: urlParams.get("utm_campaign") || "",
        utm_content: urlParams.get("utm_content") || "",
        referrer: document.referrer || "",
        ...extraData,
      };

      fetch(`${API_URL}/api/analytics/track-event`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        keepalive: true,
      }).catch(() => {});
    } catch (e) {
      console.warn("Analytics error:", e);
    }
  }

  onMount(async () => {
    // Log landing event
    trackEvent("landing");

    try {
      const res = await fetch(`${API_URL}/api/recommendations/today`);
      if (res.ok) {
        data = await res.json();
      } else {
        error = "Failed to load today's official selections.";
      }
    } catch (e) {
      console.error("Error loading today's recommendations:", e);
      error = "Failed to load today's official selections.";
    } finally {
      loading = false;
    }
  });

  function handleTrackRecordClick() {
    trackEvent("track_record_view");
  }
</script>

<SEOHead
  title="Today's Qualified Picks | FixtureCast"
  description="Today's official pre-kickoff qualified Single and Accumulator picks, verified by empirical conservative calibration and zero backfill."
  canonicalUrl="https://fixturecast.com/today"
/>

<div class="max-w-4xl mx-auto py-6 sm:py-10 px-4 sm:px-6">
  <!-- Top Header Banner -->
  <div class="text-center mb-8 sm:mb-12">
    <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-bold {data?.freeze_status === 'pending' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'} mb-3 shadow-lg">
      <span class="w-2 h-2 rounded-full {data?.freeze_status === 'pending' ? 'bg-amber-400' : 'bg-emerald-400'} animate-pulse"></span>
      {data?.freeze_status === 'pending' ? 'Pre-Kickoff Qualification Pending' : 'Canonical Pre-Kickoff Pipeline'}
    </div>
    <h1 class="text-3xl sm:text-4xl lg:text-5xl font-black text-white tracking-tight mb-3">
      Today’s Official Selections
    </h1>
    <p class="text-sm sm:text-base text-slate-400 max-w-xl mx-auto leading-relaxed">
      Every selection is evaluated against conservative calibration, frozen before kickoff, and tracked publicly on our verified ledger.
    </p>
  </div>

  {#if loading}
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 animate-pulse">
      <div class="h-80 rounded-2xl bg-slate-900/60 border border-white/10 p-6 space-y-4">
        <div class="h-6 w-32 bg-white/10 rounded"></div>
        <div class="h-8 w-48 bg-white/10 rounded"></div>
        <div class="h-24 bg-white/5 rounded-xl"></div>
      </div>
      <div class="h-80 rounded-2xl bg-slate-900/60 border border-white/10 p-6 space-y-4">
        <div class="h-6 w-32 bg-white/10 rounded"></div>
        <div class="h-8 w-48 bg-white/10 rounded"></div>
        <div class="h-24 bg-white/5 rounded-xl"></div>
      </div>
    </div>
  {:else if error}
    <div class="p-6 rounded-2xl bg-red-500/10 border border-red-500/20 text-center text-red-400">
      {error}
    </div>
  {:else if data}
    <!-- Main Cards Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8 mb-10">
      
      <!-- 1. Daily Single Card -->
      <div class="glass-card p-6 sm:p-7 rounded-2xl border border-white/10 bg-slate-900/70 flex flex-col justify-between relative overflow-hidden shadow-xl shadow-black/40">
        <div class="absolute -right-10 -bottom-10 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>

        <div>
          <div class="flex items-center justify-between gap-2 mb-4">
            <div class="flex items-center gap-2">
              <span class="px-3 py-1 rounded-lg text-xs font-black uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Daily Single
              </span>
              {#if data.single?.has_pick && data.single?.match_phase}
                <span class="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider {data.single.match_phase === 'LIVE' ? 'bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse' : data.single.match_phase === 'SETTLED' ? 'bg-slate-700 text-slate-300' : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'}">
                  {data.single.match_phase}
                </span>
              {/if}
            </div>
            <span class="text-xs text-slate-400 font-mono">{data.date}</span>
          </div>

          {#if data.single?.has_pick}
            <div class="mb-4">
              <h2 class="text-xl sm:text-2xl font-black text-white mb-1">
                {data.single.match}
              </h2>
              <div class="text-xs text-slate-400 font-medium">
                {data.single.league} {data.single.kickoff ? `• ${data.single.kickoff.substring(11, 16)} UTC` : ''}
              </div>
            </div>

            <div class="p-4 rounded-xl bg-white/5 border border-white/10 mb-4 space-y-3">
              <div class="flex justify-between items-center">
                <span class="text-sm font-bold text-slate-200">{data.single.selection}</span>
                <span class="font-mono font-black text-xl text-emerald-400">@ {data.single.odds}</span>
              </div>

              <div class="grid grid-cols-3 gap-2 pt-2 border-t border-white/10 text-center">
                <div>
                  <div class="text-[10px] text-slate-400 uppercase font-semibold">Conservative Prob</div>
                  <div class="font-mono font-bold text-xs text-white">{(data.single.conservative_probability * 100).toFixed(1)}%</div>
                </div>
                <div>
                  <div class="text-[10px] text-slate-400 uppercase font-semibold">Implied</div>
                  <div class="font-mono font-bold text-xs text-slate-300">{(data.single.implied_probability * 100).toFixed(1)}%</div>
                </div>
                <div>
                  <div class="text-[10px] text-slate-400 uppercase font-semibold">Conservative Edge</div>
                  <div class="font-mono font-black text-xs text-emerald-400">+{data.single.edge_pct}%</div>
                </div>
              </div>
            </div>

            <p class="text-xs text-slate-400 leading-relaxed mb-4">
              {data.single.rationale}
            </p>

            <!-- Interactive AI Match Rationale Breakdown -->
            <AIRationaleCard single={data.single} />
          {:else}
            <!-- Explicit Abstain / Pending State -->
            <div class="py-8 text-center space-y-3">
              <div class="w-12 h-12 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center mx-auto text-slate-400 text-lg font-bold">
                {data?.freeze_status === 'pending' ? '⏳' : '🛡️'}
              </div>
              <h3 class="text-base font-bold text-white">
                {data?.freeze_status === 'pending' ? 'Qualification Pending' : 'No Single Pick Today'}
              </h3>
              <p class="text-xs text-slate-400 max-w-xs mx-auto leading-relaxed">
                {data.single?.reason || "No single selection cleared our conservative probability and edge qualification criteria."}
              </p>
            </div>
          {/if}
        </div>

        <div class="pt-4 border-t border-white/10 flex items-center justify-between text-xs font-semibold">
          {#if data.single?.has_pick}
            <Link
              to={`/prediction/${data.single.fixture_id}`}
              class="text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
            >
              <span>Full Match Analysis</span>
              <span>→</span>
            </Link>
          {:else}
            <span class="text-slate-500 font-medium">{data?.freeze_status === 'pending' ? 'Awaiting Pre-Kickoff Freeze' : 'Disciplined Model Abstention'}</span>
          {/if}
          <span class="text-[11px] text-slate-500 font-mono">Frozen Pre-Kickoff</span>
        </div>
      </div>

      <!-- 2. Daily Acca Card -->
      <div class="glass-card p-6 sm:p-7 rounded-2xl border border-white/10 bg-slate-900/70 flex flex-col justify-between relative overflow-hidden shadow-xl shadow-black/40">
        <div class="absolute -right-10 -bottom-10 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>

        <div>
          <div class="flex items-center justify-between gap-2 mb-4">
            <span class="px-3 py-1 rounded-lg text-xs font-black uppercase tracking-wider bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              Daily Qualified Acca
            </span>
            <span class="text-xs text-slate-400 font-mono">{data.date}</span>
          </div>

          {#if data.acca?.has_pick}
            <div class="mb-4 flex justify-between items-baseline">
              <h2 class="text-lg sm:text-xl font-black text-white">
                {data.acca.acca_type} ({data.acca.legs_count} Legs)
              </h2>
              <div class="font-mono font-black text-lg text-indigo-400">
                Total Odds: @ {data.acca.total_odds}
              </div>
            </div>

            <div class="space-y-2 mb-4">
              {#each data.acca.legs as leg}
                <div class="p-2.5 rounded-xl bg-white/5 border border-white/10 text-xs flex items-center justify-between">
                  <div class="truncate mr-2">
                    <div class="font-bold text-white truncate">{leg.match}</div>
                    <div class="text-[11px] text-slate-400">{leg.selection}</div>
                  </div>
                  <div class="text-right shrink-0">
                    <div class="font-mono font-bold text-emerald-400">@ {leg.odds}</div>
                    {#if leg.conservative_edge !== null && leg.conservative_edge !== undefined}
                      <div class="text-[10px] font-mono text-slate-400">+{(leg.conservative_edge * 100).toFixed(1)}% edge</div>
                    {/if}
                  </div>
                </div>
              {/each}
            </div>
          {:else}
            <!-- Explicit No-Acca State -->
            <div class="py-8 text-center space-y-3">
              <div class="w-12 h-12 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center mx-auto text-slate-400 text-lg font-bold">
                🎲
              </div>
              <h3 class="text-base font-bold text-white">No Qualified Acca Today</h3>
              <p class="text-xs text-slate-400 max-w-xs mx-auto leading-relaxed">
                {data.acca?.reason || "No accumulator today met all canonical single-leg edge checks and strict 4-leg qualification limits."}
              </p>
            </div>
          {/if}
        </div>

        <div class="pt-4 border-t border-white/10 flex items-center justify-between text-xs font-semibold">
          <Link
            to="/accumulators"
            class="text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
          >
            <span>Explore All Accas</span>
            <span>→</span>
          </Link>
          <span class="text-[11px] text-slate-500 font-mono">Max 4 Legs</span>
        </div>
      </div>

    </div>

    <!-- Verified Track Record Call-To-Action Banner -->
    <div class="p-6 sm:p-8 rounded-3xl bg-gradient-to-r from-emerald-950/40 via-slate-900 to-indigo-950/40 border border-emerald-500/20 flex flex-col sm:flex-row items-center justify-between gap-6 shadow-2xl">
      <div>
        <div class="flex items-center gap-2 mb-1">
          <span class="text-xs font-bold uppercase tracking-wider text-emerald-400">Auditable Forward Record</span>
          <span class="text-xs text-slate-500">•</span>
          <span class="text-xs text-slate-400">Tracking Since 20 Aug 2026</span>
        </div>
        <h3 class="text-xl sm:text-2xl font-black text-white mb-2">
          Every Pre-Kickoff Recommendation Is Public
        </h3>
        <p class="text-xs sm:text-sm text-slate-300 max-w-lg leading-relaxed">
          We do not delete losses or backfill wins. Audit every past single and accumulator result on our immutable forward ledger.
        </p>
      </div>

      <div class="flex flex-col sm:flex-row items-center gap-3 shrink-0 w-full sm:w-auto">
        <Link
          to="/track-record"
          on:click={handleTrackRecordClick}
          class="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-sm text-center transition-all shadow-lg shadow-emerald-500/20 hover:scale-105 active:scale-95"
        >
          View Verified Record →
        </Link>
      </div>
    </div>
  {/if}
</div>
