# Performance Optimization Guide

## Current Optimizations

### ✅ Implemented
1. **Code Splitting** - Vendor chunks separated for better caching
2. **Image Optimization** - `OptimizedImage.svelte` component with:
   - Lazy loading by default
   - Error handling with fallback
   - Async decoding
3. **DNS Prefetch** - External API domains pre-resolved
4. **PWA Caching** - Service Worker caches static assets
5. **CSS Code Splitting** - Separate CSS chunks
6. **Console Removal** - Console logs stripped in production
7. **Terser Minification** - Aggressive code minification

### 📈 Performance Metrics (Target)
- **First Contentful Paint (FCP)**: < 1.5s
- **Largest Contentful Paint (LCP)**: < 2.5s
- **Time to Interactive (TTI)**: < 3.5s
- **Cumulative Layout Shift (CLS)**: < 0.1

## Usage Best Practices

### Images
Use the `OptimizedImage` component instead of `<img>` tags:

```svelte
<!-- ❌ Don't -->
<img src={team.logo} alt="Team logo" class="w-12 h-12" />

<!-- ✅ Do -->
<OptimizedImage 
  src={team.logo} 
  alt="Team logo" 
  className="w-12 h-12"
  eager={isFoldImage}  
/>
```

### API Calls
Always show loading states:

```svelte
<script>
  import SkeletonLoader from "./components/SkeletonLoader.svelte";
  
  let loading = true;
  let data = null;
  
  onMount(async () => {
    try {
      const res = await fetch('/api/data');
      data = await res.json();
    } finally {
      loading = false;
    }
  });
</script>

{#if loading}
  <SkeletonLoader type="fixture" count={5} />
{:else if data}
  <!-- Render data -->
{/if}
```

### Bundle Size
- Current main bundle: ~627KB (159KB gzip)
- Target: < 500KB uncompressed

## Future Improvements
- [ ] Implement route-based code splitting
- [ ] Add image CDN with automatic WebP conversion
- [ ] Implement virtual scrolling for long lists
- [ ] Add Redis caching for API responses
- [ ] Use HTTP/2 Server Push for critical assets
