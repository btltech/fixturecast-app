<script>
    import { Link } from "svelte-routing";
    import { _ } from "svelte-i18n";

    export let prediction;
    export let homeTeam;
    export let awayTeam;
    export let homeTeamId = null;
    export let awayTeamId = null;
    export let leagueId = 39;

    $: homeWinPct = (prediction.home_win_prob * 100).toFixed(1);
    $: drawPct = (prediction.draw_prob * 100).toFixed(1);
    $: awayWinPct = (prediction.away_win_prob * 100).toFixed(1);
    $: bttsPct = (prediction.btts_prob * 100).toFixed(1);
    $: over25Pct = (prediction.over25_prob * 100).toFixed(1);
    $: under25Pct = (prediction.under25_prob * 100).toFixed(1);
    $: over15Pct = (prediction.over15_prob * 100).toFixed(1);
    $: under15Pct = (prediction.under15_prob * 100).toFixed(1);
    $: over35Pct = (prediction.over35_prob * 100).toFixed(1);
    $: under35Pct = (prediction.under35_prob * 100).toFixed(1);
    $: btts1stHalfPct = (prediction.btts_1st_half_prob * 100).toFixed(1);
    $: btts2ndHalfPct = (prediction.btts_2nd_half_prob * 100).toFixed(1);

    // Asian Handicap
    $: ahMinus05Pct = (prediction.home_ah_minus_05 * 100).toFixed(1);
    $: ahMinus10Pct = (prediction.home_ah_minus_10 * 100).toFixed(1);
    $: ahPlus05Pct = (prediction.home_ah_plus_05 * 100).toFixed(1);
    $: ahPlus10Pct = (prediction.home_ah_plus_10 * 100).toFixed(1);

    // Confidence / intervals (if backend provides them)
    $: confidence = prediction.confidence_intervals
        ? prediction.confidence_intervals
        : null;

    $: confidenceLevel = confidence ? confidence.confidence_level : null;

    function getConfidenceLabelKey() {
        if (!confidenceLevel) return "mlPrediction.confidencePending";
        if (confidenceLevel === "very_high") return "mlPrediction.confidenceVeryHigh";
        if (confidenceLevel === "high") return "mlPrediction.confidenceHigh";
        if (confidenceLevel === "medium") return "mlPrediction.confidenceMedium";
        if (confidenceLevel === "low") return "mlPrediction.confidenceLow";
        return "mlPrediction.confidenceAnalysing";
    }

    function getConfidenceClass() {
        if (!confidenceLevel) return "pending";
        return confidenceLevel;
    }

    function getOutcomeClass(prob) {
        if (prob > 0.5) return "high";
        if (prob > 0.3) return "medium";
        return "low";
    }

    // Simple human-readable reasons using available features if present
    $: reasons = [];

    $: if (prediction && prediction.elo_ratings) {
        const diff = Math.abs(prediction.elo_ratings.diff || 0);
        if (diff >= 80) {
            const favored =
                prediction.elo_ratings.diff > 0 ? homeTeam : awayTeam;
            reasons = [
                ...reasons,
                `${favored} has a clear strength advantage based on our analysis`,
            ];
        }
    }

    $: if (prediction) {
        const homeForm =
            prediction.home_form_last5 ?? prediction.home_points_last10;
        const awayForm =
            prediction.away_form_last5 ?? prediction.away_points_last10;
        if (typeof homeForm === "number" && typeof awayForm === "number") {
            const diff = homeForm - awayForm;
            if (diff >= 3) {
                reasons = [
                    ...reasons,
                    `${homeTeam} is in better recent form over the last matches`,
                ];
            } else if (diff <= -3) {
                reasons = [
                    ...reasons,
                    `${awayTeam} is in better recent form over the last matches`,
                ];
            }
        }
    }

    $: if (prediction && typeof prediction.rank_difference === "number") {
        const diff = prediction.rank_difference;
        if (diff < -5) {
            reasons = [
                ...reasons,
                `${homeTeam} sits significantly higher in the table`,
            ];
        } else if (diff > 5) {
            reasons = [
                ...reasons,
                `${awayTeam} sits significantly higher in the table`,
            ];
        }
    }
</script>

<div class="ml-prediction-card">
    <div class="prediction-header">
        <div class="header-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path
                    d="M12 2L2 7L12 12L22 7L12 2Z"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linejoin="round"
                />
                <path
                    d="M2 17L12 22L22 17"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linejoin="round"
                />
                <path
                    d="M2 12L12 17L22 12"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linejoin="round"
                />
            </svg>
        </div>
        <div class="header-title-block">
            <h3>{$_('mlPrediction.title')}</h3>
            <div class="confidence-chip {getConfidenceClass()}">
                <span class="dot"></span>
                <span>{$_(getConfidenceLabelKey())}</span>
            </div>
        </div>
    </div>

    <!-- Main Prediction -->
    <div class="prediction-main">
        <div class="outcome-bars">
            <div
                class="outcome-bar home {getOutcomeClass(
                    prediction.home_win_prob,
                )}"
            >
                <div class="bar-label">
                    {#if homeTeamId}
                        <Link
                            to="/team/{homeTeamId}?league={leagueId}"
                            class="team-name team-link">{homeTeam}</Link
                        >
                    {:else}
                        <span class="team-name">{homeTeam}</span>
                    {/if}
                    <span class="probability">{homeWinPct}%</span>
                </div>
                <div class="bar-fill" style="width: {homeWinPct}%"></div>
            </div>

            <div
                class="outcome-bar draw {getOutcomeClass(prediction.draw_prob)}"
            >
                <div class="bar-label">
                    <span class="team-name">{$_('prediction.draw')}</span>
                    <span class="probability">{drawPct}%</span>
                </div>
                <div class="bar-fill" style="width: {drawPct}%"></div>
            </div>

            <div
                class="outcome-bar away {getOutcomeClass(
                    prediction.away_win_prob,
                )}"
            >
                <div class="bar-label">
                    {#if awayTeamId}
                        <Link
                            to="/team/{awayTeamId}?league={leagueId}"
                            class="team-name team-link">{awayTeam}</Link
                        >
                    {:else}
                        <span class="team-name">{awayTeam}</span>
                    {/if}
                    <span class="probability">{awayWinPct}%</span>
                </div>
                <div class="bar-fill" style="width: {awayWinPct}%"></div>
            </div>
        </div>

        <!-- Additional Predictions -->
        <div class="additional-predictions">
            <div class="prediction-pill">
                <span class="pill-label">{$_('prediction.btts')}</span>
                <span class="pill-value">{bttsPct}%</span>
            </div>
            <div class="prediction-pill">
                <span class="pill-label">{$_('prediction.over25')}</span>
                <span class="pill-value">{over25Pct}%</span>
            </div>
            <div class="prediction-pill">
                <span class="pill-label">{$_('prediction.under25')}</span>
                <span class="pill-value">{under25Pct}%</span>
            </div>
            <div class="prediction-pill">
                <span class="pill-label">{$_('mlPrediction.over15')}</span>
                <span class="pill-value">{over15Pct}%</span>
            </div>
            <div class="prediction-pill">
                <span class="pill-label">{$_('mlPrediction.under15')}</span>
                <span class="pill-value">{under15Pct}%</span>
            </div>
            <div class="prediction-pill">
                <span class="pill-label">{$_('mlPrediction.over35')}</span>
                <span class="pill-value">{over35Pct}%</span>
            </div>
            <div class="prediction-pill">
                <span class="pill-label">{$_('mlPrediction.under35')}</span>
                <span class="pill-value">{under35Pct}%</span>
            </div>
            <div class="prediction-pill">
                <span class="pill-label">{$_('mlPrediction.btts1stHalf')}</span>
                <span class="pill-value">{btts1stHalfPct}%</span>
            </div>
            <div class="prediction-pill">
                <span class="pill-label">{$_('mlPrediction.btts2ndHalf')}</span>
                <span class="pill-value">{btts2ndHalfPct}%</span>
            </div>
            <!-- Asian Handicap Section -->
            <div class="prediction-pill ah-header">
                <span class="pill-label">🎯 {$_('mlPrediction.asianHandicap')}</span>
            </div>
            <div class="prediction-pill">
                <span class="pill-label">AH -0.5</span>
                <span class="pill-value">{ahMinus05Pct}%</span>
            </div>
            <div class="prediction-pill">
                <span class="pill-label">AH -1.0</span>
                <span class="pill-value">{ahMinus10Pct}%</span>
            </div>
            <div class="prediction-pill">
                <span class="pill-label">AH +0.5</span>
                <span class="pill-value">{ahPlus05Pct}%</span>
            </div>
            <div class="prediction-pill">
                <span class="pill-label">AH +1.0</span>
                <span class="pill-value">{ahPlus10Pct}%</span>
            </div>
        </div>

        {#if reasons.length > 0}
            <div class="reasons-block">
                <div class="reasons-title">{$_('mlPrediction.whyModel')}</div>
                <ul>
                    {#each reasons.slice(0, 3) as r}
                        <li>{r}</li>
                    {/each}
                </ul>
            </div>
        {/if}
    </div>
</div>

<style>
    .ml-prediction-card {
        background: linear-gradient(
            135deg,
            rgba(88, 28, 135, 0.1),
            rgba(139, 92, 246, 0.05)
        );
        border: 1px solid rgba(139, 92, 246, 0.2);
        border-radius: 16px;
        padding: 20px;
        backdrop-filter: blur(20px);
        box-shadow: 0 8px 32px rgba(139, 92, 246, 0.1);
        transition:
            transform var(--duration-fast, 100ms)
                var(--ease-out-soft, cubic-bezier(0.25, 0.46, 0.45, 0.94)),
            box-shadow var(--duration-fast, 100ms)
                var(--ease-out-soft, cubic-bezier(0.25, 0.46, 0.45, 0.94));
    }

    @media (min-width: 640px) {
        .ml-prediction-card {
            padding: 24px;
        }
    }

    .ml-prediction-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 48px rgba(139, 92, 246, 0.15);
    }

    .prediction-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 24px;
        padding-bottom: 16px;
        border-bottom: 1px solid rgba(139, 92, 246, 0.2);
    }

    .header-icon {
        color: var(--primary-400, #a78bfa);
    }

    .header-title-block {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 4px;
    }

    .prediction-header h3 {
        margin: 0;
        font-size: 1.25rem;
        font-weight: 700;
        background: linear-gradient(135deg, #a78bfa, #ec4899);
        background-clip: text;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .confidence-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.7rem;
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(148, 163, 184, 0.4);
        color: #e5e7eb;
        align-self: flex-start;
    }

    .confidence-chip .dot {
        width: 6px;
        height: 6px;
        border-radius: 999px;
        background: #9ca3af;
    }

    .confidence-chip.very_high {
        border-color: #22c55e;
        background: rgba(34, 197, 94, 0.08);
    }

    .confidence-chip.very_high .dot {
        background: #22c55e;
    }

    .confidence-chip.high {
        border-color: #a3e635;
        background: rgba(163, 230, 53, 0.08);
    }

    .confidence-chip.high .dot {
        background: #a3e635;
    }

    .confidence-chip.medium {
        border-color: #fbbf24;
        background: rgba(251, 191, 36, 0.08);
    }

    .confidence-chip.medium .dot {
        background: #fbbf24;
    }

    .confidence-chip.low {
        border-color: #f97316;
        background: rgba(249, 115, 22, 0.08);
    }

    .confidence-chip.low .dot {
        background: #f97316;
    }

    .prediction-main {
        display: flex;
        flex-direction: column;
        gap: 20px;
    }

    @media (min-width: 640px) {
        .prediction-main {
            gap: 24px;
        }
    }

    .outcome-bars {
        display: flex;
        flex-direction: column;
        gap: 12px;
        min-height: 180px; /* Reserve space to prevent layout shift */
    }

    .outcome-bar {
        position: relative;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 12px;
        overflow: hidden;
        min-height: 52px; /* Fixed height for each bar */
    }

    .bar-label {
        display: flex;
        justify-content: space-between;
        align-items: center;
        position: relative;
        z-index: 2;
        margin-bottom: 8px;
    }

    .team-name {
        font-weight: 600;
        font-size: 0.95rem;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 180px; /* Limit width to prevent bar overflow */
    }

    .team-link {
        color: inherit;
        text-decoration: none;
        transition: color var(--duration-fast, 100ms)
            var(--ease-out-soft, cubic-bezier(0.25, 0.46, 0.45, 0.94));
    }

    .team-link:hover {
        color: var(--primary-400, #a78bfa);
        text-decoration: underline;
    }

    .probability {
        font-weight: 700;
        font-size: 1.1rem;
    }

    .bar-fill {
        position: absolute;
        top: 0;
        left: 0;
        height: 100%;
        border-radius: 12px;
        transition: width var(--duration-slow, 300ms)
            var(--ease-out-smooth, cubic-bezier(0.22, 1, 0.36, 1)) 50ms; /* Slight delay to ensure layout is ready */
        opacity: 0.3;
        width: 0; /* Start at 0, animate to target */
    }

    .outcome-bar.home .bar-fill {
        background: linear-gradient(90deg, #10b981, #059669);
    }

    .outcome-bar.draw .bar-fill {
        background: linear-gradient(90deg, #f59e0b, #d97706);
    }

    .outcome-bar.away .bar-fill {
        background: linear-gradient(90deg, #ef4444, #dc2626);
    }

    .outcome-bar.high .bar-fill {
        opacity: 0.6;
        box-shadow: 0 0 20px currentColor;
    }

    .outcome-bar.medium .bar-fill {
        opacity: 0.4;
    }

    .scoreline-prediction {
        text-align: center;
        padding: 20px;
        background: rgba(139, 92, 246, 0.1);
        border-radius: 12px;
        border: 1px dashed rgba(139, 92, 246, 0.3);
    }

    .additional-predictions {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 12px;
    }

    .prediction-pill {
        background: rgba(59, 130, 246, 0.1);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 10px;
        padding: 12px 16px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
        transition:
            transform var(--duration-fast, 100ms)
                var(--ease-out-soft, cubic-bezier(0.25, 0.46, 0.45, 0.94)),
            background-color var(--duration-fast, 100ms)
                var(--ease-out-soft, cubic-bezier(0.25, 0.46, 0.45, 0.94));
    }

    .prediction-pill.ah-header {
        background: rgba(139, 92, 246, 0.15);
        border-color: rgba(139, 92, 246, 0.5);
        grid-column: 1 / -1;
        font-weight: 600;
        padding: 10px;
    }

    .prediction-pill:hover {
        transform: scale(1.02);
        background: rgba(59, 130, 246, 0.15);
    }

    .pill-label {
        font-size: 0.8rem;
        opacity: 0.8;
        text-align: center;
    }

    .pill-value {
        font-size: 1.3rem;
        font-weight: 700;
        color: var(--blue-400, #60a5fa);
    }

    .reasons-block {
        margin-top: 18px;
        padding: 12px 14px;
        border-radius: 10px;
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.3);
        font-size: 0.8rem;
    }

    .reasons-title {
        font-weight: 600;
        margin-bottom: 6px;
        color: #e5e7eb;
    }

    .reasons-block ul {
        margin: 0;
        padding-left: 18px;
        color: #cbd5f5;
    }

    .reasons-block li {
        margin-bottom: 2px;
    }

    @media (max-width: 640px) {
        .additional-predictions {
            grid-template-columns: 1fr;
        }
    }
</style>
