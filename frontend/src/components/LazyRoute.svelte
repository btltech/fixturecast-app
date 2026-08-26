<script context="module">
  // Module scope, not instance scope: a new LazyRoute is created on every
  // navigation, so an instance-level cache would be discarded each time and the
  // loading spinner would flash again on pages the visitor has already opened.
  const cache = new Map();
</script>

<script>
  /**
   * Loads a page component on demand instead of bundling it into the initial
   * download.
   *
   * Why: every page was imported directly into the router, so all 23 compiled
   * into one chunk that every visitor downloaded before seeing anything -
   * someone opening a match prediction was also fetching the admin metrics
   * page, the accumulator builder, and the cookie policy.
   *
   * `load` is a function returning a dynamic import, e.g.
   *   <LazyRoute load={() => import("../pages/Home.svelte")} />
   * It must be written inline like that (not a variable holding a path), or the
   * bundler cannot statically find the module to split it out.
   *
   * `props` is spread onto the loaded component, which is how route params such
   * as :id continue to reach pages that expect them.
   */
  export let load;
  export let props = {};

  function resolve(loader) {
    if (!cache.has(loader)) {
      cache.set(loader, loader());
    }
    return cache.get(loader);
  }

  $: promise = resolve(load);
</script>

{#await promise}
  <!--
    Deliberately minimal and roughly the height of a page header. A large or
    animated placeholder is more jarring than a brief quiet gap, since most of
    these chunks resolve in well under a second.
  -->
  <div class="min-h-[40vh] flex items-center justify-center" aria-busy="true">
    <div
      class="w-8 h-8 border-4 border-accent border-t-transparent rounded-full animate-spin"
      role="status"
      aria-label="Loading"
    ></div>
  </div>
{:then module}
  <svelte:component this={module.default} {...props} />
{:catch}
  <!--
    A failed chunk load is usually a stale cached index referencing assets that
    a new deploy has replaced. Reloading fetches the current index and fixes it.
  -->
  <div class="glass-card p-6 text-center">
    <p class="text-slate-300">This page didn't load properly.</p>
    <button
      class="mt-3 px-4 py-2 rounded-lg bg-accent text-slate-900 font-semibold"
      on:click={() => location.reload()}
    >
      Reload
    </button>
  </div>
{/await}
