<script>
    import { link } from "svelte-routing";
    import { _ } from "svelte-i18n";
</script>

<div class="not-found">
    <div class="not-found-content">
        <span class="not-found-icon">⚽</span>
        <h1>{$_('notFound.title')}</h1>
        <p>{$_('notFound.desc')}</p>
        <a href="/" use:link class="home-btn">{$_('notFound.backHome')}</a>
    </div>
</div>

<style>
    .not-found {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 60vh;
        text-align: center;
    }
    .not-found-content {
        max-width: 400px;
    }
    .not-found-icon {
        font-size: 4rem;
        display: block;
        margin-bottom: 1rem;
    }
    .not-found h1 {
        font-size: 2rem;
        margin-bottom: 0.5rem;
        color: var(--text-primary, #fff);
    }
    .not-found p {
        color: var(--text-secondary, #aaa);
        margin-bottom: 1.5rem;
    }
    .home-btn {
        display: inline-block;
        padding: 0.75rem 1.5rem;
        background: var(--accent-color, #6366f1);
        color: white;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 600;
        transition: opacity 0.2s;
    }
    .home-btn:hover {
        opacity: 0.85;
    }
</style>
