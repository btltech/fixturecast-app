<script>
  /**
   * Optimized Image Component
   * Automatically adds loading="lazy" and proper error handling
   */
  export let src;
  export let alt = "";
  export let className = "";
  export let width = undefined;
  export let height = undefined;
  export let eager = false; // Set to true for above-the-fold images

  let imageError = false;
  let fallbackSrc = "/icons/icon-192.png"; // Default fallback

  function handleError() {
    imageError = true;
  }
</script>

<img
  src={imageError ? fallbackSrc : src}
  {alt}
  class={className}
  {width}
  {height}
  loading={eager ? "eager" : "lazy"}
  decoding="async"
  on:error={handleError}
/>
