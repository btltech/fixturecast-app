<script>
  import { get } from 'svelte/store';
  import { _ } from 'svelte-i18n';

  let email = '';
  let status = 'idle'; // idle, loading, success, error
  let message = '';

  // Kit (ConvertKit) Form ID
  const KIT_FORM_ID = '8837042';

  function t(key, values) {
    return get(_)(key, values);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!email || !email.includes('@')) {
      status = 'error';
      message = t('emailSignup.errors.invalidEmail');
      return;
    }

    status = 'loading';

    try {
      // Use Kit's public form submission endpoint (no API key needed)
      const response = await fetch(`https://app.kit.com/forms/${KIT_FORM_ID}/subscriptions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          email_address: email
        })
      });

      if (!response.ok) {
        // Try alternative endpoint
        const altResponse = await fetch(`https://api.convertkit.com/v3/forms/${KIT_FORM_ID}/subscribe`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            api_key: import.meta.env.VITE_CONVERTKIT_API_KEY || '',
            email: email
          })
        });

        if (!altResponse.ok) {
          throw new Error('Subscription failed');
        }
      }

      status = 'success';
      message = t('emailSignup.success.checkInbox');
      email = '';
    } catch (err) {
      // Fallback: Store locally
      const subscribers = JSON.parse(localStorage.getItem('fc_subscribers') || '[]');
      if (!subscribers.includes(email)) {
        subscribers.push(email);
        localStorage.setItem('fc_subscribers', JSON.stringify(subscribers));
      }
      status = 'success';
      message = t('emailSignup.success.thanks');
      email = '';
    }
  }
</script>

<div class="bg-gradient-to-r from-cyan-500/10 to-purple-500/10 border border-cyan-500/20 rounded-xl p-6">
  <div class="text-center mb-4">
    <h3 class="text-lg font-bold text-white mb-1">🔮 {$_('emailSignup.title')}</h3>
    <p class="text-sm text-slate-400">{$_('emailSignup.subtitle')}</p>
  </div>

  {#if status === 'success'}
    <div class="text-center py-4">
      <span class="text-2xl">✅</span>
      <p class="text-green-400 font-medium mt-2">{message}</p>
    </div>
  {:else}
    <form on:submit={handleSubmit} class="flex flex-col sm:flex-row gap-2">
      <input
        type="email"
        bind:value={email}
        placeholder="your@email.com"
        class="flex-1 px-4 py-2 rounded-lg bg-slate-800 border border-slate-600 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
        disabled={status === 'loading'}
      />
      <button
        type="submit"
        disabled={status === 'loading'}
        class="px-6 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-purple-500 text-white font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
      >
        {status === 'loading' ? '...' : $_('emailSignup.cta')}
      </button>
    </form>
    {#if status === 'error'}
      <p class="text-red-400 text-sm mt-2 text-center">{message}</p>
    {/if}
    <p class="text-xs text-slate-500 text-center mt-3">{$_('emailSignup.disclaimer')}</p>
  {/if}
</div>
