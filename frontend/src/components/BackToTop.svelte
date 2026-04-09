<script>
    import { onMount, onDestroy } from "svelte";
    import { _ } from "svelte-i18n";

    let visible = false;

    function handleScroll() {
        visible = window.scrollY > 400;
    }

    function scrollToTop() {
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    onMount(() => {
        window.addEventListener("scroll", handleScroll, { passive: true });
    });

    onDestroy(() => {
        window.removeEventListener("scroll", handleScroll);
    });
</script>

{#if visible}
    <button
        on:click={scrollToTop}
        aria-label={$_("backToTop.label")}
        class="fixed bottom-20 right-4 md:bottom-8 md:right-8 z-40 w-12 h-12 rounded-full bg-primary/80 backdrop-blur-sm text-white shadow-lg hover:bg-primary transition-all duration-300 flex items-center justify-center hover:scale-110"
        style="animation: fadeInUp 0.3s ease-out"
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
                d="M5 15l7-7 7 7"
            />
        </svg>
    </button>
{/if}

<style>
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(16px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
</style>
