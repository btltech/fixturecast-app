<script>
  export let size = 40;
  export let showText = true;
  export let textClass = "text-xl font-display font-bold text-white";
</script>

<div class="flex items-center gap-3 group">
  <!-- Logo Icon -->
  <svg
    width={size}
    height={size}
    viewBox="0 0 48 48"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    class="drop-shadow-lg transition-transform group-hover:scale-105"
  >
    <!-- Background gradient circle -->
    <defs>
      <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#3B82F6"/>
        <stop offset="50%" style="stop-color:#2563EB"/>
        <stop offset="100%" style="stop-color:#1D4ED8"/>
      </linearGradient>
      <linearGradient id="ballGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#FFFFFF"/>
        <stop offset="100%" style="stop-color:#E2E8F0"/>
      </linearGradient>
      <filter id="glow">
        <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
        <feMerge>
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    </defs>

    <!-- Main circle background -->
    <rect x="2" y="2" width="44" height="44" rx="12" fill="url(#logoGradient)"/>

    <!-- Football/Soccer ball -->
    <circle cx="24" cy="24" r="12" fill="url(#ballGradient)" filter="url(#glow)"/>

    <!-- Pentagon pattern on ball -->
    <path
      d="M24 14 L28.5 18 L27 23.5 L21 23.5 L19.5 18 Z"
      fill="#1E293B"
      opacity="0.9"
    />

    <!-- Hexagon lines -->
    <path
      d="M24 14 L24 12 M28.5 18 L31 16.5 M27 23.5 L30 25 M21 23.5 L18 25 M19.5 18 L17 16.5"
      stroke="#1E293B"
      stroke-width="1.5"
      stroke-linecap="round"
      opacity="0.7"
    />

    <!-- Lower pentagon hint -->
    <path
      d="M21 23.5 L19 28 L24 31 L29 28 L27 23.5"
      stroke="#1E293B"
      stroke-width="1"
      fill="none"
      opacity="0.5"
    />

    <!-- Prediction/AI indicator - lightning bolt -->
    <path
      d="M32 8 L28 16 L32 16 L28 24"
      stroke="#FCD34D"
      stroke-width="2.5"
      stroke-linecap="round"
      stroke-linejoin="round"
      fill="none"
      filter="url(#glow)"
    />
  </svg>

  <!-- Logo Text -->
  {#if showText}
    <span class={textClass}>
      <span class="text-transparent bg-clip-text bg-gradient-to-r from-white via-white to-slate-300">Fixture</span><span class="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400">Cast</span>
    </span>
  {/if}
</div>
