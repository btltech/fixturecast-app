<script>
  import { get } from "svelte/store";
  import { _ } from "svelte-i18n";
  import { onMount } from "svelte";

  let notificationsSupported = false;
  let permission = "default";
  let subscribed = false;
  let loading = false;
  let error = null;

  // VAPID public key - would come from backend in production
  // For now, we'll use a placeholder and check localStorage
  const VAPID_PUBLIC_KEY = null; // Set this from your backend

  function t(key, values) {
    return get(_)(key, values ? { values } : undefined);
  }

  onMount(() => {
    // Check if notifications are supported
    notificationsSupported = "Notification" in window && "serviceWorker" in navigator;

    if (notificationsSupported) {
      permission = Notification.permission;
      // Check if user has subscribed before
      subscribed = localStorage.getItem("push_subscribed") === "true";
    }
  });

  async function requestPermission() {
    loading = true;
    error = null;

    try {
      const result = await Notification.requestPermission();
      permission = result;

      if (result === "granted") {
        await subscribeToNotifications();
      } else if (result === "denied") {
        error = t("notificationSettings.errors.blocked");
      }
    } catch (e) {
      error = t("notificationSettings.errors.requestFailed", { message: e.message });
    } finally {
      loading = false;
    }
  }

  async function subscribeToNotifications() {
    try {
      const registration = await navigator.serviceWorker.ready;

      // Check if already subscribed
      let subscription = await registration.pushManager.getSubscription();

      if (!subscription && VAPID_PUBLIC_KEY) {
        // Subscribe with VAPID key
        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
        });

        // Send subscription to backend
        // await fetch('/api/push/subscribe', {
        //   method: 'POST',
        //   headers: { 'Content-Type': 'application/json' },
        //   body: JSON.stringify(subscription)
        // });
      }

      subscribed = true;
      localStorage.setItem("push_subscribed", "true");

      // Show a test notification
      if (permission === "granted") {
        showTestNotification();
      }
    } catch (e) {
      error = t("notificationSettings.errors.subscribeFailed", { message: e.message });
      console.error("Push subscription error:", e);
    }
  }

  async function unsubscribe() {
    loading = true;
    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();

      if (subscription) {
        await subscription.unsubscribe();
      }

      subscribed = false;
      localStorage.removeItem("push_subscribed");
    } catch (e) {
      error = t("notificationSettings.errors.unsubscribeFailed", { message: e.message });
    } finally {
      loading = false;
    }
  }

  function showTestNotification() {
    if (permission === "granted") {
      new Notification(t("notificationSettings.test.title"), {
        body: t("notificationSettings.test.body"),
        icon: "/icons/icon-192.png",
        badge: "/icons/icon-192.png"
      });
    }
  }

  function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, "+")
      .replace(/_/g, "/");
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }
</script>

<div class="glass-card p-4">
  <div class="flex items-center gap-3 mb-4">
    <span class="text-xl">🔔</span>
    <div>
      <h3 class="font-bold text-sm">{$_("notificationSettings.title")}</h3>
      <p class="text-xs text-slate-400">{$_("notificationSettings.subtitle")}</p>
    </div>
  </div>

  {#if !notificationsSupported}
    <div class="bg-slate-800/50 rounded-lg p-3 text-center">
      <p class="text-sm text-slate-400">
        {$_("notificationSettings.notSupported")}
      </p>
    </div>
  {:else if permission === "denied"}
    <div class="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
      <p class="text-sm text-red-400">
        ❌ {$_("notificationSettings.blockedTitle")}
      </p>
      <p class="text-xs text-slate-400 mt-1">
        {$_("notificationSettings.blockedDesc")}
      </p>
    </div>
  {:else if subscribed && permission === "granted"}
    <div class="space-y-3">
      <div class="flex items-center justify-between bg-green-500/10 border border-green-500/30 rounded-lg p-3">
        <div class="flex items-center gap-2">
          <span class="text-green-400">✓</span>
          <span class="text-sm text-green-400">{$_("notificationSettings.enabled")}</span>
        </div>
        <button
          on:click={showTestNotification}
          class="text-xs text-slate-400 hover:text-white transition-colors"
        >
          {$_("notificationSettings.testButton")}
        </button>
      </div>

      <button
        on:click={unsubscribe}
        disabled={loading}
        class="w-full px-3 py-2 text-sm text-slate-400 hover:text-red-400 border border-slate-600 hover:border-red-500/50 rounded-lg transition-colors disabled:opacity-50"
      >
        {loading ? "..." : $_("notificationSettings.disable")}
      </button>
    </div>
  {:else}
    <div class="space-y-3">
      <div class="bg-white/5 rounded-lg p-3">
        <ul class="text-xs text-slate-400 space-y-1">
          <li>⚽ {$_("notificationSettings.features.goals")}</li>
          <li>⏰ {$_("notificationSettings.features.kickoff")}</li>
          <li>📊 {$_("notificationSettings.features.daily")}</li>
        </ul>
      </div>

      <button
        on:click={requestPermission}
        disabled={loading}
        class="w-full btn-primary py-2 text-sm disabled:opacity-50"
      >
        {#if loading}
          <span class="inline-block animate-spin mr-2">⏳</span>
        {/if}
        {$_("notificationSettings.enable")}
      </button>

      {#if error}
        <p class="text-xs text-red-400 text-center">{error}</p>
      {/if}
    </div>
  {/if}
</div>
