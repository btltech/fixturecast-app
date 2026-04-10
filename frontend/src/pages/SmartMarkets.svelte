<script>
    import SEOHead from "../components/SEOHead.svelte";
    import { generateSmartMarketsSEO } from "../services/seoService.js";
    const seoData = generateSmartMarketsSEO();
    import { onMount } from "svelte";
    import { ML_API_URL, BACKEND_API_URL } from "../services/apiConfig.js";
    import { getLeagueSeason } from "../services/season.js";
    import { LEAGUES } from "../services/leagues.js";
    import { _ } from "svelte-i18n";

    const ML_API = ML_API_URL;
    const BACKEND_API = BACKEND_API_URL;
    const leagues = LEAGUES.filter((l) => l.tier !== 3);

    const EDGE_MARGIN = Number(
        /** @type {any} */ (import.meta).env?.VITE_EDGE_MARGIN ?? 0.02,
    );

    function twoWayImplied(oddsA, oddsB) {
        const a = Number(oddsA);
        const b = Number(oddsB);
        if (!Number.isFinite(a) || !Number.isFinite(b) || a <= 1 || b <= 1)
            return null;
        const impliedA = 1 / a;
        const impliedB = 1 / b;
        const total = impliedA + impliedB;
        if (total <= 0) return null;
        return {
            a: impliedA / total,
            b: impliedB / total,
        };
    }

    let matches = [];
    let predictions = [];
    let loading = true;
    let error = null;
    let selectedFilter = "all"; // all, high-confidence, ou-only, btts-only
    let accuracy = null;

    function getFixtureSeason(leagueId, fixtureDate = new Date()) {
        return getLeagueSeason(leagueId, fixtureDate);
    }

    onMount(async () => {
        // Load backend-derived accuracy first so UI never falls back to hardcoded numbers.
        await loadAccuracy();
        await loadSmartMarketPredictions();
    });

    async function loadSmartMarketPredictions() {
        loading = true;
        error = null;
        predictions = [];

        try {
            // Fetch TODAY'S fixtures from backend API for ALL featured leagues IN PARALLEL
            const leaguePromises = leagues.map(async (league) => {
                try {
                    const season = getFixtureSeason(league.id);
                    const response = await fetch(
                        `${BACKEND_API}/api/fixtures?league=${league.id}&season=${season}&today_only=true`,
                    );
                    if (response.ok) {
                        const data = await response.json();
                        if (data.response && Array.isArray(data.response)) {
                            return data.response.filter(
                                (f) =>
                                    f.fixture.status?.short === "NS" ||
                                    f.fixture.status?.short === "TBD",
                            );
                        }
                    }
                } catch (e) {
                    console.warn(
                        `Failed to load fixtures for league ${league.id}:`,
                        e,
                    );
                }
                return [];
            });

            const leagueResults = await Promise.all(leaguePromises);
            matches = leagueResults.flat(); // ALL today's matches, no arbitrary limit
            console.log(`Loaded ${matches.length} matches from today`);

            // Get smart market predictions for each match IN PARALLEL
            const predictionPromises = matches.map(async (match) => {
                try {
                    const fixtureId = match.fixture?.id;
                    if (!fixtureId) return null;

                    const predResponse = await fetch(
                        `${ML_API}/api/prediction/${fixtureId}?league=${match.league?.id}&season=${getFixtureSeason(match.league?.id, match.fixture?.date)}`,
                    );

                    if (predResponse.ok) {
                        const pred = await predResponse.json();
                        const predData = pred.prediction || pred;

                        // Extract smart markets from prediction response
                        const overProb = predData.over25_prob || 0.5;
                        const bttsProb = predData.btts_prob || 0.5;

                        // Certainty: probability of the predicted side (e.g. Over vs Under)
                        // 60%+ certainty means p >= 0.60 or p <= 0.40.
                        const ouCertainty = Math.max(overProb, 1 - overProb);
                        const bttsCertainty = Math.max(bttsProb, 1 - bttsProb);

                        // Value/edge gating: require our prob to exceed bookmaker-implied prob by EDGE_MARGIN.
                        // If market pricing is missing, we do NOT treat it as a value pick.
                        const ouMarket = predData.odds?.over_under_25;
                        const bttsMarket = predData.odds?.btts;

                        const ouImplied = ouMarket?.available
                            ? twoWayImplied(ouMarket.over, ouMarket.under)
                            : null;
                        const bttsImplied = bttsMarket?.available
                            ? twoWayImplied(bttsMarket.yes, bttsMarket.no)
                            : null;

                        const ouImpliedSelected = ouImplied
                            ? overProb > 0.5
                                ? ouImplied.a
                                : ouImplied.b
                            : null;
                        const bttsImpliedSelected = bttsImplied
                            ? bttsProb > 0.5
                                ? bttsImplied.a
                                : bttsImplied.b
                            : null;

                        const ouValueOk =
                            ouImpliedSelected != null
                                ? ouCertainty >= ouImpliedSelected + EDGE_MARGIN
                                : false;
                        const bttsValueOk =
                            bttsImpliedSelected != null
                                ? bttsCertainty >=
                                  bttsImpliedSelected + EDGE_MARGIN
                                : false;

                        const smartMarkets = {
                            predictions: {
                                over_under_25: {
                                    prediction:
                                        overProb > 0.5 ? "Over" : "Under",
                                    probability: ouCertainty,
                                    confidence: ouCertainty,
                                    value_ok: ouValueOk,
                                    historical_accuracy:
                                        accuracy?.ou_25_accuracy ?? null,
                                },
                                btts: {
                                    prediction: bttsProb > 0.5 ? "Yes" : "No",
                                    probability: bttsCertainty,
                                    confidence: bttsCertainty,
                                    value_ok: bttsValueOk,
                                    historical_accuracy:
                                        accuracy?.btts_accuracy ?? null,
                                },
                            },
                        };

                        return {
                            ...match,
                            smart_markets: smartMarkets,
                        };
                    } else {
                        console.warn(
                            `Failed to get prediction for fixture ${fixtureId}: ${predResponse.status}`,
                        );
                        return null;
                    }
                } catch (e) {
                    console.warn(
                        `Error predicting match ${match.fixture?.id}:`,
                        e.message,
                    );
                    return null;
                }
            });

            const predictionResults = await Promise.all(predictionPromises);
            predictions = predictionResults.filter((p) => p !== null);

            console.log(`Generated ${predictions.length} predictions`);
        } catch (e) {
            error = e.message;
            console.error("Error loading smart markets:", e);
        } finally {
            loading = false;
        }
    }

    async function loadAccuracy() {
        try {
            const response = await fetch(
                `${ML_API}/api/smart-markets/accuracy`,
            );
            if (response.ok) {
                accuracy = await response.json();
            }
        } catch (e) {
            console.warn("Failed to load accuracy:", e);
        }
    }

    $: filteredPredictions = predictions
        .filter((p) => {
            const hasOU = p.smart_markets?.predictions?.over_under_25;
            const hasBTTS = p.smart_markets?.predictions?.btts;

            // Smart Markets shows ONLY:
            // - high confidence (>= 60% certainty)
            // - and value (our probability beats bookmaker implied by EDGE_MARGIN)
            const ouQualifies =
                hasOU && hasOU.confidence >= 0.6 && hasOU.value_ok === true;
            const bttsQualifies =
                hasBTTS &&
                hasBTTS.confidence >= 0.6 &&
                hasBTTS.value_ok === true;

            if (selectedFilter === "high-confidence") {
                return ouQualifies || bttsQualifies;
            }
            if (selectedFilter === "ou-only") return ouQualifies;
            if (selectedFilter === "btts-only") return bttsQualifies;

            // Default "All Predictions" still requires 60% confidence threshold
            return ouQualifies || bttsQualifies;
        })
        .sort((a, b) => {
            // Sort by highest confidence first
            const getMaxConfidence = (p) => {
                const ou =
                    p.smart_markets?.predictions?.over_under_25?.confidence ||
                    0;
                const btts =
                    p.smart_markets?.predictions?.btts?.confidence || 0;
                return Math.max(ou, btts);
            };
            return getMaxConfidence(b) - getMaxConfidence(a);
        });

    function getConfidenceColor(confidence) {
        if (confidence > 0.7) return "#10b981"; // green - very high confidence
        if (confidence > 0.6) return "#3b82f6"; // blue - high confidence
        return "#f59e0b"; // amber - shouldn't show in Smart Markets
    }
</script>

<SEOHead data={seoData} />

<svelte:window on:click />

<div class="smart-markets-page">
    <!-- Header -->
    <div class="header">
        <div class="header-content">
            <h1>💡 {$_('smartMarkets.title')}</h1>
            <p class="subtitle">
                {$_('smartMarkets.subtitle')}
            </p>
        </div>

        {#if accuracy && (accuracy.ou_25_accuracy != null || accuracy.btts_accuracy != null || accuracy.data_points)}
            <div class="accuracy-stats">
                <div class="stat">
                    <div class="stat-label">{$_('smartMarkets.ouLabel')}</div>
                    <div class="stat-value">
                        {#if accuracy.ou_25_accuracy != null}
                            {(accuracy.ou_25_accuracy * 100).toFixed(1)}%
                        {:else}
                            —
                        {/if}
                    </div>
                    <div class="stat-desc">{$_('smartMarkets.accuracySince')}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">{$_('smartMarkets.bttsLabel')}</div>
                    <div class="stat-value">
                        {#if accuracy.btts_accuracy != null}
                            {(accuracy.btts_accuracy * 100).toFixed(1)}%
                        {:else}
                            —
                        {/if}
                    </div>
                    <div class="stat-desc">{$_('smartMarkets.accuracySince')}</div>
                </div>
                <div class="stat">
                    <div class="stat-label">{$_('smartMarkets.dataPoints')}</div>
                    <div class="stat-value">
                        {accuracy.data_points?.over_under_25 ??
                            accuracy.data_points?.btts ??
                            "—"}
                    </div>
                    <div class="stat-desc">{$_('smartMarkets.trackedSince')}</div>
                </div>
            </div>
        {/if}
    </div>

    <!-- Info Banner -->
    <div class="info-banner">
        <div class="banner-icon">ℹ️</div>
        <div class="banner-text">
            <strong>Why Smart Markets?</strong> We focus on Over/Under 2.5 and
            BTTS where our AI model shows predictive edge.
            <strong>Only picks with meaningful edge are shown.</strong> We require
            at least 60% certainty and that our probability beats the bookmaker-implied
            probability by a small margin. Most matches won't qualify — that's intentional.
        </div>
    </div>

    <!-- Filter Bar -->
    <div class="filter-bar">
        <button
            class:active={selectedFilter === "all"}
            on:click={() => (selectedFilter = "all")}
        >
            {$_('smartMarkets.allPredictions')}
        </button>
        <button
            class:active={selectedFilter === "high-confidence"}
            on:click={() => (selectedFilter = "high-confidence")}
        >
            🔥 {$_('smartMarkets.highConfidence')}
        </button>
        <button
            class:active={selectedFilter === "ou-only"}
            on:click={() => (selectedFilter = "ou-only")}
        >
            {$_('smartMarkets.ouOnly')}
        </button>
        <button
            class:active={selectedFilter === "btts-only"}
            on:click={() => (selectedFilter = "btts-only")}
        >
            {$_('smartMarkets.bttsOnly')}
        </button>
    </div>

    <!-- Loading / Error -->
    {#if loading}
        <div class="loading">{$_('smartMarkets.loading')}</div>
    {/if}

    {#if error}
        <div class="error">Error: {error}</div>
    {/if}

    <!-- Predictions Grid -->
    {#if !loading && filteredPredictions.length > 0}
        <div class="predictions-grid">
            {#each filteredPredictions as pred (pred.fixture?.id)}
                <div class="prediction-card">
                    <!-- Match Header -->
                    <div class="match-header">
                        <div class="teams">
                            <div class="team">
                                <span class="team-name"
                                    >{pred.teams?.home?.name || "Home"}</span
                                >
                            </div>
                            <div class="vs">vs</div>
                            <div class="team">
                                <span class="team-name"
                                    >{pred.teams?.away?.name || "Away"}</span
                                >
                            </div>
                        </div>
                        <div class="match-time">
                            {#if pred.fixture?.date}
                                {new Date(pred.fixture.date).toLocaleString()}
                            {/if}
                        </div>
                    </div>

                    <!-- Markets -->
                    <div class="markets">
                        {#if pred.smart_markets?.predictions?.over_under_25}
                            <div class="market">
                                <div class="market-name">📈 {$_('smartMarkets.ouMarket')}</div>
                                <div class="prediction-box">
                                    <div class="pred-value">
                                        {pred.smart_markets.predictions
                                            .over_under_25.prediction}
                                    </div>
                                    <div class="pred-confidence">
                                        <span
                                            class="confidence-dot"
                                            style="background: {getConfidenceColor(
                                                pred.smart_markets.predictions
                                                    .over_under_25.confidence,
                                            )}"
                                        ></span>
                                        <span
                                            >{(
                                                pred.smart_markets.predictions
                                                    .over_under_25.confidence *
                                                100
                                            ).toFixed(0)}%</span
                                        >
                                    </div>
                                    <div class="accuracy-badge">
                                        {#if pred.smart_markets.predictions.over_under_25.historical_accuracy != null}
                                            {(
                                                pred.smart_markets.predictions
                                                    .over_under_25
                                                    .historical_accuracy * 100
                                            ).toFixed(1)}{$_('smartMarkets.sinceLaunch')}
                                        {/if}
                                    </div>
                                </div>
                            </div>
                        {/if}

                        {#if pred.smart_markets?.predictions?.btts}
                            <div class="market">
                                <div class="market-name">
                                    ⚽ {$_('smartMarkets.bttsMarket')}
                                </div>
                                <div class="prediction-box">
                                    <div class="pred-value">
                                        {pred.smart_markets.predictions.btts
                                            .prediction}
                                    </div>
                                    <div class="pred-confidence">
                                        <span
                                            class="confidence-dot"
                                            style="background: {getConfidenceColor(
                                                pred.smart_markets.predictions
                                                    .btts.confidence,
                                            )}"
                                        ></span>
                                        <span
                                            >{(
                                                pred.smart_markets.predictions
                                                    .btts.confidence * 100
                                            ).toFixed(0)}%</span
                                        >
                                    </div>
                                    <div class="accuracy-badge">
                                        {#if pred.smart_markets.predictions.btts.historical_accuracy != null}
                                            {(
                                                pred.smart_markets.predictions
                                                    .btts.historical_accuracy *
                                                100
                                            ).toFixed(1)}{$_('smartMarkets.sinceLaunch')}
                                        {/if}
                                    </div>
                                </div>
                            </div>
                        {/if}

                        {#if pred.smart_markets?.combo}
                            <div class="market combo-market">
                                <div class="market-name">
                                    🎲 {$_('smartMarkets.comboMarket')}
                                </div>
                                <div class="prediction-box combo-box">
                                    <div class="combo-desc">
                                        {pred.smart_markets.combo.description}
                                    </div>
                                    <div class="pred-confidence">
                                        <span
                                            class="confidence-dot"
                                            style="background: {getConfidenceColor(
                                                pred.smart_markets.combo
                                                    .combined_confidence,
                                            )}"
                                        ></span>
                                        <span
                                            >{(
                                                pred.smart_markets.combo
                                                    .combined_confidence * 100
                                            ).toFixed(0)}%</span
                                        >
                                    </div>
                                </div>
                            </div>
                        {/if}
                    </div>
                </div>
            {/each}
        </div>
    {/if}

    {#if !loading && filteredPredictions.length === 0}
        <div class="no-predictions">
            <p>{$_('smartMarkets.noPredictions')}</p>
            <p>{$_('smartMarkets.noPredictionsDesc')}</p>
        </div>
    {/if}
</div>

<style>
    .smart-markets-page {
        max-width: 1400px;
        margin: 0 auto;
        padding: 20px;
        background: #0f172a;
        color: #e2e8f0;
        min-height: 100vh;
    }

    .header {
        margin-bottom: 30px;
    }

    .header-content h1 {
        font-size: 2.5em;
        font-weight: 700;
        margin: 0 0 10px 0;
        color: #fff;
    }

    .subtitle {
        color: #94a3b8;
        font-size: 1.1em;
        margin: 0 0 20px 0;
    }

    .accuracy-stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 15px;
        margin-top: 20px;
    }

    .stat {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #334155;
        text-align: center;
    }

    .stat-label {
        font-size: 0.9em;
        color: #94a3b8;
        margin-bottom: 8px;
    }

    .stat-value {
        font-size: 2.2em;
        font-weight: 700;
        color: #10b981;
        margin-bottom: 5px;
    }

    .stat-desc {
        font-size: 0.85em;
        color: #64748b;
    }

    .info-banner {
        background: linear-gradient(135deg, #164e63 0%, #0f172a 100%);
        border: 1px solid #06b6d4;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        display: flex;
        gap: 15px;
        align-items: flex-start;
    }

    .banner-icon {
        font-size: 1.5em;
        flex-shrink: 0;
    }

    .banner-text {
        color: #e0f2fe;
        line-height: 1.6;
    }

    .filter-bar {
        display: flex;
        gap: 10px;
        margin-bottom: 30px;
        flex-wrap: wrap;
    }

    .filter-bar button {
        padding: 10px 20px;
        border: 2px solid #334155;
        background: #1e293b;
        color: #94a3b8;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.3s;
        font-weight: 500;
    }

    .filter-bar button:hover {
        border-color: #64748b;
    }

    .filter-bar button.active {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        border-color: #10b981;
    }

    .loading,
    .error,
    .no-predictions {
        text-align: center;
        padding: 40px;
        color: #94a3b8;
        font-size: 1.1em;
    }

    .error {
        color: #ef4444;
    }

    .predictions-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
        gap: 20px;
    }

    .prediction-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        transition: all 0.3s;
    }

    .prediction-card:hover {
        border-color: #64748b;
        box-shadow: 0 0 20px rgba(16, 185, 129, 0.1);
    }

    .match-header {
        margin-bottom: 20px;
        padding-bottom: 15px;
        border-bottom: 1px solid #334155;
    }

    .teams {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
        gap: 10px;
    }

    .team {
        flex: 1;
        text-align: center;
    }

    .team-name {
        font-weight: 600;
        color: #fff;
        font-size: 1.05em;
    }

    .vs {
        color: #64748b;
        font-size: 0.9em;
        margin: 0 10px;
    }

    .match-time {
        font-size: 0.85em;
        color: #94a3b8;
        text-align: center;
    }

    .markets {
        display: flex;
        flex-direction: column;
        gap: 15px;
    }

    .market {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 15px;
    }

    .combo-market {
        background: linear-gradient(135deg, #7c2d12 0%, #0f172a 100%);
        border-color: #ea580c;
    }

    .market-name {
        font-weight: 600;
        color: #e2e8f0;
        margin-bottom: 12px;
        font-size: 0.95em;
    }

    .prediction-box {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }

    .pred-value {
        font-size: 1.3em;
        font-weight: 700;
        color: #10b981;
    }

    .pred-confidence {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.9em;
        color: #94a3b8;
    }

    .confidence-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }

    .accuracy-badge {
        font-size: 0.8em;
        color: #64748b;
        text-align: center;
        padding: 5px;
        background: rgba(100, 116, 139, 0.1);
        border-radius: 4px;
    }

    .combo-desc {
        color: #f97316;
        font-weight: 600;
        font-size: 0.95em;
    }

    @media (max-width: 768px) {
        .predictions-grid {
            grid-template-columns: 1fr;
        }

        .header-content h1 {
            font-size: 1.8em;
        }

        .accuracy-stats {
            grid-template-columns: 1fr;
        }
    }
</style>
