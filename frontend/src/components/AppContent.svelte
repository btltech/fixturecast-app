<script>
  import { Route, useLocation } from "svelte-routing";
  import Navbar from "./Navbar.svelte";
  import BottomNav from "./BottomNav.svelte";
  import BackToTop from "./BackToTop.svelte";
  import ErrorBoundary from "./ErrorBoundary.svelte";
  import ComparePanel from "./ComparePanel.svelte";
  import CookieConsent from "./CookieConsent.svelte";
  import ResponsibleGamblingFooter from "./ResponsibleGamblingFooter.svelte";
  import Home from "../pages/Home.svelte";
  import Fixtures from "../pages/Fixtures.svelte";
  import Prediction from "../pages/Prediction.svelte";
  import Teams from "../pages/Teams.svelte";
  import TeamDetail from "../pages/TeamDetail.svelte";
  import MLPredictions from "../pages/MLPredictions.svelte";
  import Standings from "../pages/Standings.svelte";
  import Results from "../pages/Results.svelte";
  import ModelStats from "../pages/ModelStats.svelte";
  import AdminMetrics from "../pages/AdminMetrics.svelte";
  import History from "../pages/History.svelte";
  import LiveScores from "../pages/LiveScores.svelte";
  import TodaysFixtures from "../pages/TodaysFixtures.svelte";
  import Privacy from "../pages/Privacy.svelte";
  import Terms from "../pages/Terms.svelte";
  import Cookies from "../pages/Cookies.svelte";
  import LandingPicks from "../pages/LandingPicks.svelte";
  import DailyAccas from "../pages/DailyAccas.svelte";
  import SmartMarkets from "../pages/SmartMarkets.svelte";
  import League from "../pages/League.svelte";
  import NotFound from "../pages/NotFound.svelte";

  // Now useLocation works because we're inside Router context
  const location = useLocation();
  $: isLandingPage = $location.pathname === "/picks";
</script>

{#if isLandingPage}
  <!-- Landing Page (standalone, no nav/footer) -->
  <Route path="/picks" component={LandingPicks} />
{:else}
  <!-- All other routes with full navigation -->
  <div class="min-h-screen flex flex-col pb-16 md:pb-0">
    <Navbar />
    <ErrorBoundary>
      <main class="flex-grow container mx-auto p-4">
        <Route path="/" component={Home} />
        <Route path="/today" component={TodaysFixtures} />
        <Route path="/fixtures" component={Fixtures} />
        <Route path="/prediction/:id" component={Prediction} />
        <Route path="/ai" component={MLPredictions} />
        <Route path="/predictions" component={MLPredictions} />
        <Route path="/smart-markets" component={SmartMarkets} />
        <Route path="/accumulators" component={DailyAccas} />
        <Route path="/accas" component={DailyAccas} />
        <Route path="/teams" component={Teams} />
        <Route path="/team/:id" component={TeamDetail} />
        <Route path="/league/:id" component={League} />
        <Route path="/standings" component={Standings} />
        <Route path="/results" component={Results} />
        <Route path="/models" component={ModelStats} />
        <Route path="/admin/metrics" component={AdminMetrics} />
        <Route path="/history" component={History} />
        <Route path="/live" component={LiveScores} />
        <Route path="/privacy" component={Privacy} />
        <Route path="/terms" component={Terms} />
        <Route path="/cookies" component={Cookies} />
        <Route component={NotFound} />
      </main>
    </ErrorBoundary>

    <!-- Responsible Gambling Footer -->
    <ResponsibleGamblingFooter />

    <!-- Mobile Bottom Navigation -->
    <BottomNav />

    <!-- Back to Top Button -->
    <BackToTop />

    <!-- Compare Panel (floating) -->
    <ComparePanel />

    <!-- Cookie Consent Banner -->
    <CookieConsent />
  </div>
{/if}
