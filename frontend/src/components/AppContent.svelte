<script>
  import { Route, useLocation } from "svelte-routing";
  import Navbar from "./Navbar.svelte";
  import BottomNav from "./BottomNav.svelte";
  import BackToTop from "./BackToTop.svelte";
  import ErrorBoundary from "./ErrorBoundary.svelte";
  import ComparePanel from "./ComparePanel.svelte";
  import LazyRoute from "./LazyRoute.svelte";
  import CookieConsent from "./CookieConsent.svelte";
  import ResponsibleGamblingFooter from "./ResponsibleGamblingFooter.svelte";
  import Home from "../pages/Home.svelte";
  import LandingPicks from "../pages/LandingPicks.svelte";

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
        <!--
          Home stays eagerly imported: it is the most common entry point, and
          lazy-loading it would add a needless round trip to the page most
          visitors see first. Every other page is fetched on demand.
        -->
        <Route path="/" component={Home} />
        <Route path="/today"><LazyRoute load={() => import("../pages/TodayLanding.svelte")} /></Route>
        <Route path="/today-fixtures"><LazyRoute load={() => import("../pages/TodaysFixtures.svelte")} /></Route>
        <Route path="/fixtures"><LazyRoute load={() => import("../pages/Fixtures.svelte")} /></Route>
        <Route path="/prediction/:id" let:params>
          <LazyRoute load={() => import("../pages/Prediction.svelte")} props={{ id: params.id }} />
        </Route>
        <Route path="/match/:id" let:params>
          <LazyRoute load={() => import("../pages/MatchPreview.svelte")} props={{ id: params.id }} />
        </Route>
        <Route path="/ai"><LazyRoute load={() => import("../pages/MLPredictions.svelte")} /></Route>
        <Route path="/predictions"><LazyRoute load={() => import("../pages/MLPredictions.svelte")} /></Route>
        <Route path="/smart-markets"><LazyRoute load={() => import("../pages/SmartMarkets.svelte")} /></Route>
        <Route path="/accumulators"><LazyRoute load={() => import("../pages/DailyAccas.svelte")} /></Route>
        <Route path="/accas"><LazyRoute load={() => import("../pages/DailyAccas.svelte")} /></Route>
        <Route path="/teams"><LazyRoute load={() => import("../pages/Teams.svelte")} /></Route>
        <Route path="/team/:id" let:params>
          <LazyRoute load={() => import("../pages/TeamDetail.svelte")} props={{ id: params.id }} />
        </Route>
        <Route path="/league/:id" let:params>
          <LazyRoute load={() => import("../pages/League.svelte")} props={{ id: params.id }} />
        </Route>
        <Route path="/standings"><LazyRoute load={() => import("../pages/Standings.svelte")} /></Route>
        <Route path="/results"><LazyRoute load={() => import("../pages/Results.svelte")} /></Route>
        <Route path="/models"><LazyRoute load={() => import("../pages/ModelStats.svelte")} /></Route>
        <Route path="/track-record"><LazyRoute load={() => import("../pages/TrackRecord.svelte")} /></Route>
        <Route path="/admin/metrics"><LazyRoute load={() => import("../pages/AdminMetrics.svelte")} /></Route>
        <Route path="/history"><LazyRoute load={() => import("../pages/History.svelte")} /></Route>
        <Route path="/live"><LazyRoute load={() => import("../pages/LiveScores.svelte")} /></Route>
        <Route path="/privacy"><LazyRoute load={() => import("../pages/Privacy.svelte")} /></Route>
        <Route path="/terms"><LazyRoute load={() => import("../pages/Terms.svelte")} /></Route>
        <Route path="/cookies"><LazyRoute load={() => import("../pages/Cookies.svelte")} /></Route>
        <Route path="/how-it-works"><LazyRoute load={() => import("../pages/HowItWorks.svelte")} /></Route>
        <Route path="/acca-builder"><LazyRoute load={() => import("../pages/AccaBuilder.svelte")} /></Route>
        <Route><LazyRoute load={() => import("../pages/NotFound.svelte")} /></Route>
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
