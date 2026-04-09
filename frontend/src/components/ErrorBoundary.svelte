<script>
    // Svelte error boundary – catches uncaught errors from child components
    // Usage: <ErrorBoundary><YourComponent /></ErrorBoundary>
    import { _ } from 'svelte-i18n';

    let hasError = false;
    let errorMessage = "";

    // Handle errors bubbled from children
    function handleError(event) {
        hasError = true;
        errorMessage =
            event?.detail?.message ||
            event?.message ||
            "An unexpected error occurred";
        console.error("[ErrorBoundary]", event);
    }

    function retry() {
        hasError = false;
        errorMessage = "";
        window.location.reload();
    }
</script>

<svelte:window on:error={handleError} on:unhandledrejection={handleError} />

{#if hasError}
    <div
        class="glass-card p-8 text-center border border-red-500/30 mx-auto max-w-lg mt-12"
    >
        <div class="text-5xl mb-4">⚠️</div>
        <h2 class="text-xl font-bold text-white mb-2">{$_('errorBoundary.title')}</h2>
        <p class="text-slate-400 mb-6 text-sm">{errorMessage}</p>
        <button
            on:click={retry}
            class="px-6 py-2 bg-primary/20 hover:bg-primary/30 text-primary rounded-lg font-medium transition-colors"
        >
            {$_('errorBoundary.reload')}
        </button>
    </div>
{:else}
    <slot />
{/if}
