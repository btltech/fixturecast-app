<script>
  import { Link, useLocation } from "svelte-routing";
  import { _ } from "svelte-i18n";
  import SearchBar from "./SearchBar.svelte";
  import LanguageSwitcher from "./LanguageSwitcher.svelte";
  import Logo from "./Logo.svelte";
  import PwaInstallButton from "./PwaInstallButton.svelte";

  const location = useLocation();
  $: currentPath = $location.pathname;

  let mobileMenuOpen = false;
  let matchesDropdownOpen = false;
  let moreDropdownOpen = false;

  function toggleMobileMenu() {
    mobileMenuOpen = !mobileMenuOpen;
    // Prevent body scroll when menu is open
    document.body.style.overflow = mobileMenuOpen ? "hidden" : "";
  }

  function closeMobileMenu() {
    mobileMenuOpen = false;
    document.body.style.overflow = "";
  }

  function isActive(path) {
    if (path === "/") return currentPath === "/";
    return currentPath.startsWith(path);
  }

  function isMatchesActive() {
    return (
      isActive("/fixtures") ||
      isActive("/live") ||
      isActive("/results") ||
      isActive("/today")
    );
  }

  function isMoreActive() {
    return (
      isActive("/standings") ||
      isActive("/models") ||
      isActive("/history") ||
      isActive("/ai")
    );
  }

  function closeDropdowns() {
    matchesDropdownOpen = false;
    moreDropdownOpen = false;
  }

  function goBack() {
    if (window.history.length > 1) {
      window.history.back();
    } else {
      window.location.href = "/";
    }
  }

  $: showBackButton = currentPath !== "/";
</script>

<svelte:window on:click={closeDropdowns} />

<nav
  class="glass sticky top-0 z-50 px-4 md:px-6 py-3 md:py-4 border-b border-white/5 safe-top"
>
  <div class="flex justify-between items-center gap-4">
    <!-- Mobile Back Button -->
    {#if showBackButton}
      <button
        on:click={goBack}
        class="md:hidden flex-shrink-0 p-2 -ml-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 active:bg-white/20 transition-all touch-target"
        aria-label="Go back"
      >
        <svg
          class="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M15 19l-7-7 7-7"
          />
        </svg>
      </button>
    {/if}

    <!-- Logo -->
    <Link to="/" class="flex-shrink-0" on:click={closeMobileMenu}>
      <Logo
        size={32}
        textClass="text-lg md:text-xl font-display font-bold text-white"
      />
    </Link>

    <!-- Desktop Search -->
    <div class="hidden lg:block flex-1 max-w-md mx-8">
      <SearchBar />
    </div>

    <!-- Desktop Navigation -->
    <div class="hidden md:flex gap-1 items-center">
      <Link
        to="/"
        class="px-4 py-2 rounded-lg text-sm font-medium transition-all {isActive(
          '/',
        )
          ? 'text-white bg-white/10'
          : 'text-slate-400 hover:text-white hover:bg-white/5'}"
      >
        {$_("nav.home")}
      </Link>

      <!-- Matches Dropdown -->
      <div class="relative">
        <button
          on:click|stopPropagation={() => {
            matchesDropdownOpen = !matchesDropdownOpen;
            moreDropdownOpen = false;
          }}
          class="px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-1.5 {isMatchesActive()
            ? 'text-white bg-white/10'
            : 'text-slate-400 hover:text-white hover:bg-white/5'}"
        >
          {$_("nav.matches")}
          <svg
            class="w-4 h-4 transition-transform {matchesDropdownOpen
              ? 'rotate-180'
              : ''}"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M19 9l-7 7-7-7"
            />
          </svg>
          {#if isActive("/live")}
            <span class="relative flex h-2 w-2 ml-1">
              <span
                class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"
              ></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-red-500"
              ></span>
            </span>
          {/if}
        </button>

        {#if matchesDropdownOpen}
          <div
            class="absolute top-full left-0 mt-1 w-48 bg-surface border border-white/10 rounded-xl shadow-2xl py-2 z-50"
          >
            <Link
              to="/fixtures"
              on:click={closeDropdowns}
              class="flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors {isActive(
                '/fixtures',
              )
                ? 'text-white bg-white/5'
                : 'text-slate-300'}"
            >
              <svg
                class="w-4 h-4 text-blue-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
              {$_("nav.fixtures")}
            </Link>
            <Link
              to="/live"
              on:click={closeDropdowns}
              class="flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors {isActive(
                '/live',
              )
                ? 'text-white bg-white/5'
                : 'text-slate-300'}"
            >
              <span class="relative flex h-4 w-4 items-center justify-center">
                <span
                  class="animate-ping absolute inline-flex h-2.5 w-2.5 rounded-full bg-red-400 opacity-75"
                ></span>
                <span
                  class="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"
                ></span>
              </span>
              {$_("nav.live")}
            </Link>
            <Link
              to="/results"
              on:click={closeDropdowns}
              class="flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors {isActive(
                '/results',
              )
                ? 'text-white bg-white/5'
                : 'text-slate-300'}"
            >
              <svg
                class="w-4 h-4 text-emerald-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              {$_("nav.results")}
            </Link>
          </div>
        {/if}
      </div>

      <!-- More Dropdown -->
      <div class="relative">
        <button
          on:click|stopPropagation={() => {
            moreDropdownOpen = !moreDropdownOpen;
            matchesDropdownOpen = false;
          }}
          class="px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-1.5 {isMoreActive()
            ? 'text-white bg-white/10'
            : 'text-slate-400 hover:text-white hover:bg-white/5'}"
        >
          {$_("nav.more")}
          <svg
            class="w-4 h-4 transition-transform {moreDropdownOpen
              ? 'rotate-180'
              : ''}"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>

        {#if moreDropdownOpen}
          <div
            class="absolute top-full left-0 mt-1 w-48 bg-surface border border-white/10 rounded-xl shadow-2xl py-2 z-50"
          >
            <Link
              to="/standings"
              on:click={closeDropdowns}
              class="flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors {isActive(
                '/standings',
              )
                ? 'text-white bg-white/5'
                : 'text-slate-300'}"
            >
              <svg
                class="w-4 h-4 text-blue-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
              {$_("nav.standings")}
            </Link>
            <Link
              to="/ai"
              on:click={closeDropdowns}
              class="flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors {isActive(
                '/ai',
              )
                ? 'text-white bg-white/5'
                : 'text-slate-300'}"
            >
              <svg
                class="w-4 h-4 text-accent"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
              {$_("nav.aiModels")}
            </Link>
            <Link
              to="/smart-markets"
              on:click={closeDropdowns}
              class="flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors {isActive(
                '/smart-markets',
              )
                ? 'text-white bg-white/5'
                : 'text-slate-300'}"
            >
              <span class="text-base">💡</span>
              Smart Markets
            </Link>
            <Link
              to="/accumulators"
              on:click={closeDropdowns}
              class="flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors {isActive(
                '/accumulators',
              )
                ? 'text-white bg-white/5'
                : 'text-slate-300'}"
            >
              <span class="text-base">🎲</span>
              Daily Accas
            </Link>
            <Link
              to="/models"
              on:click={closeDropdowns}
              class="flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors {isActive(
                '/models',
              )
                ? 'text-white bg-white/5'
                : 'text-slate-300'}"
            >
              <svg
                class="w-4 h-4 text-purple-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                />
              </svg>
              {$_("nav.modelStats")}
            </Link>
            <Link
              to="/history"
              on:click={closeDropdowns}
              class="flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors {isActive(
                '/history',
              )
                ? 'text-white bg-white/5'
                : 'text-slate-300'}"
            >
              <svg
                class="w-4 h-4 text-amber-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              {$_("nav.history")}
            </Link>
          </div>
        {/if}
      </div>

      <!-- Language Switcher -->
      <LanguageSwitcher />

      <!-- PWA Install (shows only when installable) -->
      <PwaInstallButton />

      <!-- Admin metrics hidden - access via /admin/metrics directly -->
    </div>

    <!-- Mobile: More menu (main nav in bottom bar) -->
    <div class="flex items-center gap-2 md:hidden">
      <PwaInstallButton />
      <!-- More menu for secondary items -->
      <button
        on:click={toggleMobileMenu}
        class="p-2 rounded-lg hover:bg-white/10 touch-target btn-press text-slate-400 hover:text-white"
        aria-label="More options"
        aria-expanded={mobileMenuOpen}
      >
        <svg
          class="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 6h16M4 12h16M4 18h16"
          />
        </svg>
      </button>
    </div>
  </div>

  <!-- Mobile Search (always visible on tablet) -->
  <div class="lg:hidden mt-3">
    <SearchBar />
  </div>
</nav>

<!-- Mobile Menu Overlay -->
{#if mobileMenuOpen}
  <button
    class="mobile-overlay visible md:hidden"
    on:click={closeMobileMenu}
    on:keydown={(e) => e.key === "Escape" && closeMobileMenu()}
    aria-label="Close menu"
    tabindex="-1"
  ></button>
{/if}

<!-- Mobile Menu Drawer (Secondary items only - main nav in bottom bar) -->
<div
  class="fixed inset-y-0 right-0 w-72 max-w-[85vw] bg-surface z-50 transform md:hidden mobile-drawer {mobileMenuOpen
    ? 'open'
    : ''} border-l border-white/10 shadow-2xl"
  style="padding-top: calc(env(safe-area-inset-top) + 1rem);"
>
  <div class="flex flex-col h-full">
    <!-- Menu Header -->
    <div
      class="flex items-center justify-between px-6 pb-6 border-b border-white/5"
    >
      <span class="font-display font-bold text-xl">{$_("nav.menu")}</span>
      <button
        on:click={closeMobileMenu}
        class="p-2 -mr-2 rounded-lg hover:bg-white/10 touch-target btn-press text-slate-400 hover:text-white"
        aria-label="Close menu"
      >
        <svg
          class="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>
    </div>

    <!-- Secondary Navigation Links -->
    <nav class="flex-1 overflow-y-auto py-6">
      <div class="space-y-1 px-3">
        <Link
          to="/results"
          on:click={closeMobileMenu}
          class="flex items-center gap-4 px-4 py-3 rounded-xl hover:bg-white/5 touch-target menu-item group"
        >
          <div
            class="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400 group-hover:bg-blue-500/20 transition-colors"
          >
            <svg
              class="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              ><path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 002 2h2a2 2 0 002-2z"
              /></svg
            >
          </div>
          <span class="font-medium text-slate-200 group-hover:text-white"
            >{$_("nav.results")}</span
          >
        </Link>

        <div class="my-4 mx-4 border-t border-white/5"></div>

        <Link
          to="/accumulators"
          on:click={closeMobileMenu}
          class="flex items-center gap-4 px-4 py-3 rounded-xl hover:bg-white/5 touch-target menu-item group"
        >
          <div
            class="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center text-white group-hover:scale-105 transition-all"
          >
            <span class="text-xl">🎲</span>
          </div>
          <span class="font-medium text-slate-200 group-hover:text-white"
            >Daily Accas</span
          >
        </Link>

        <Link
          to="/models"
          on:click={closeMobileMenu}
          class="flex items-center gap-4 px-4 py-3 rounded-xl hover:bg-white/5 touch-target menu-item group"
        >
          <div
            class="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-400 group-hover:bg-purple-500/20 transition-colors"
          >
            <svg
              class="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              ><path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
              /></svg
            >
          </div>
          <span class="font-medium text-slate-200 group-hover:text-white"
            >{$_("nav.modelStats")}</span
          >
        </Link>

        <!-- Admin metrics hidden - access via /admin/metrics directly -->

        <Link
          to="/history"
          on:click={closeMobileMenu}
          class="flex items-center gap-4 px-4 py-3 rounded-xl hover:bg-white/5 touch-target menu-item group"
        >
          <div
            class="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400 group-hover:bg-amber-500/20 transition-colors"
          >
            <svg
              class="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              ><path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              /></svg
            >
          </div>
          <span class="font-medium text-slate-200 group-hover:text-white"
            >{$_("nav.history")}</span
          >
        </Link>
      </div>
    </nav>

    <!-- Menu Footer -->
    <div class="p-6 border-t border-white/5 safe-bottom bg-black/20">
      <div class="text-xs text-slate-500 text-center font-medium">
        FixtureCast v2.0 • AI-Powered Predictions
      </div>
    </div>
  </div>
</div>
