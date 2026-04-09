<script>
  import { _ } from "svelte-i18n";
  import { onMount } from "svelte";

  let deferredPrompt = null;
  let isInstallable = false;
  let isInstalled = false;
  let isIOS = false;

  function detectInstalled() {
    // iOS Safari exposes navigator.standalone
    const iosStandalone =
      typeof navigator !== "undefined" && (/** @type {any} */ (navigator)).standalone === true;
    const displayStandalone =
      typeof window !== "undefined" &&
      window.matchMedia &&
      window.matchMedia("(display-mode: standalone)").matches;
    isInstalled = iosStandalone || displayStandalone;
  }

  function detectIOS() {
    if (typeof navigator === "undefined") return false;
    const ua = navigator.userAgent || "";
    return /iphone|ipad|ipod/i.test(ua);
  }

  onMount(() => {
    isIOS = detectIOS();
    detectInstalled();

    // If already installed, never show.
    if (isInstalled) return;

    const onBeforeInstallPrompt = (e) => {
      // Store the event so we can trigger it later with our custom button
      // NOTE: We're NOT calling e.preventDefault() to allow the browser's native
      // install banner to show. Our button serves as an additional option.
      deferredPrompt = e;
      isInstallable = true;
    };

    const onAppInstalled = () => {
      isInstalled = true;
      isInstallable = false;
      deferredPrompt = null;
    };

    window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);
    window.addEventListener("appinstalled", onAppInstalled);

    // iOS has no beforeinstallprompt; still allow "Add to Home Screen" guidance.
    if (isIOS) {
      isInstallable = true;
    }

    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
      window.removeEventListener("appinstalled", onAppInstalled);
    };
  });

  async function install() {
    detectInstalled();
    if (isInstalled) return;

    if (deferredPrompt) {
      deferredPrompt.prompt();
      // Wait for the user to respond to the prompt
      try {
        await deferredPrompt.userChoice;
      } finally {
        deferredPrompt = null;
        // Some browsers won't fire appinstalled immediately; hide button after the attempt.
        isInstallable = false;
      }
      return;
    }

    // iOS / Safari: no prompt available.
    if (isIOS) {
      window.alert($_("pwaInstall.iosInstructions"));
    }
  }
</script>

{#if isInstallable && !isInstalled}
  <button
    type="button"
    on:click|stopPropagation={install}
    class="px-3 py-2 rounded-lg text-sm font-medium transition-all text-slate-300 hover:text-white hover:bg-white/10 bg-white/5"
    aria-label={$_("pwaInstall.install")}
    title={$_("pwaInstall.install")}
  >
    {$_("pwaInstall.install")}
  </button>
{/if}
