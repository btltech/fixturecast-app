<script>
  export let history = [];
  export let startingBank = 100.0;
  export let label = "Bankroll Growth";

  let hoveredPoint = null;

  $: points = (() => {
    if (!history || history.length === 0) {
      return [{
        index: 0,
        date: "Start",
        match: "Starting Bank",
        pnl: 0,
        bank: startingBank,
        won: null
      }];
    }

    const sorted = [...history].sort((a, b) => {
      const da = new Date(a.date || a.settled_at || 0);
      const db = new Date(b.date || b.settled_at || 0);
      return da - db;
    });

    let currentBank = startingBank;
    const pts = [{
      index: 0,
      date: "Launch (20 Aug)",
      match: "Starting Capital",
      pnl: 0,
      bank: startingBank,
      won: null
    }];

    sorted.forEach((item, idx) => {
      const pnl = Number(item.unit_pnl ?? (item.won ? ((item.odds || 1.0) - 1.0) : -1.0));
      currentBank = Number((currentBank + pnl).toFixed(2));
      pts.push({
        index: idx + 1,
        date: item.date || item.settled_at?.substring(0, 10) || "Match",
        match: item.match || `${item.home_team || ""} vs ${item.away_team || ""}`,
        selection: item.selection || item.market || "Single",
        odds: item.odds || 0,
        pnl,
        bank: currentBank,
        won: item.won ?? (pnl > 0)
      });
    });

    return pts;
  })();

  $: currentBank = points[points.length - 1].bank;
  $: profitUnits = Number((currentBank - startingBank).toFixed(2));
  $: isProfit = profitUnits >= 0;

  const width = 700;
  const height = 240;
  const padLeft = 45;
  const padRight = 25;
  const padTop = 25;
  const padBottom = 35;

  $: minBank = Math.min(startingBank * 0.95, ...points.map(p => p.bank));
  $: maxBank = Math.max(startingBank * 1.05, ...points.map(p => p.bank));
  $: bankRange = maxBank - minBank || 1;

  function getX(idx) {
    if (points.length <= 1) return padLeft + (width - padLeft - padRight) / 2;
    return padLeft + (idx / (points.length - 1)) * (width - padLeft - padRight);
  }

  function getY(bank) {
    return height - padBottom - ((bank - minBank) / bankRange) * (height - padTop - padBottom);
  }

  $: baselineY = getY(startingBank);

  $: pathString = (() => {
    if (points.length === 0) return "";
    return points.map((p, idx) => `${idx === 0 ? "M" : "L"} ${getX(idx)} ${getY(p.bank)}`).join(" ");
  })();

  $: areaString = (() => {
    if (points.length === 0) return "";
    const firstX = getX(0);
    const lastX = getX(points.length - 1);
    const bottomY = height - padBottom;
    return `${pathString} L ${lastX} ${bottomY} L ${firstX} ${bottomY} Z`;
  })();
</script>

<div class="glass-card p-5 sm:p-6 rounded-2xl border border-white/10 bg-slate-900/80 shadow-2xl relative overflow-hidden mb-8">
  <div class="flex flex-wrap items-center justify-between gap-4 mb-4">
    <div>
      <div class="flex items-center gap-2">
        <span class="text-xs font-bold uppercase tracking-wider text-slate-400">100-Unit Bankroll Tracker</span>
        <span class="px-2 py-0.5 rounded text-[10px] font-black uppercase {isProfit ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-rose-500/20 text-rose-400 border border-rose-500/30"}">
          {profitUnits >= 0 ? "+" : ""}{profitUnits}u ({((profitUnits / startingBank) * 100).toFixed(1)}%)
        </span>
      </div>
      <h3 class="text-xl sm:text-2xl font-black text-white mt-0.5">
        {currentBank.toFixed(2)} <span class="text-sm font-normal text-slate-400">Units</span>
      </h3>
    </div>

    <div class="flex items-center gap-4 text-xs font-medium text-slate-400">
      <div class="flex items-center gap-1.5">
        <span class="w-2.5 h-0.5 bg-emerald-400"></span>
        <span>Simulated Bank</span>
      </div>
      <div class="flex items-center gap-1.5">
        <span class="w-2.5 h-0.5 border-t border-dashed border-slate-500"></span>
        <span>100u Base</span>
      </div>
    </div>
  </div>

  <div class="relative w-full overflow-hidden">
    <svg
      viewBox={`0 0 ${width} ${height}`}
      class="w-full h-auto max-h-64 select-none overflow-visible"
    >
      <defs>
        <linearGradient id="bankrollGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color={isProfit ? "#10b981" : "#f43f5e"} stop-opacity="0.35" />
          <stop offset="100%" stop-color={isProfit ? "#10b981" : "#f43f5e"} stop-opacity="0.0" />
        </linearGradient>
      </defs>

      <line
        x1={padLeft}
        y1={baselineY}
        x2={width - padRight}
        y2={baselineY}
        stroke="#64748b"
        stroke-width="1.2"
        stroke-dasharray="4 4"
        opacity="0.5"
      />
      <text
        x={padLeft - 8}
        y={baselineY + 3.5}
        fill="#94a3b8"
        font-size="10"
        font-family="monospace"
        text-anchor="end"
      >
        100u
      </text>

      <text
        x={padLeft - 8}
        y={padTop + 6}
        fill="#64748b"
        font-size="9"
        font-family="monospace"
        text-anchor="end"
      >
        {maxBank.toFixed(0)}u
      </text>
      <text
        x={padLeft - 8}
        y={height - padBottom}
        fill="#64748b"
        font-size="9"
        font-family="monospace"
        text-anchor="end"
      >
        {minBank.toFixed(0)}u
      </text>

      {#if areaString}
        <path d={areaString} fill="url(#bankrollGrad)" />
      {/if}

      {#if pathString}
        <path
          d={pathString}
          fill="none"
          stroke={isProfit ? "#34d399" : "#f87171"}
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      {/if}

      {#each points as pt, idx}
        <circle
          cx={getX(idx)}
          cy={getY(pt.bank)}
          r={hoveredPoint?.index === pt.index ? "6" : "3.5"}
          fill={pt.won === true ? "#10b981" : (pt.won === false ? "#f43f5e" : "#38bdf8")}
          stroke="#0f172a"
          stroke-width="2"
          class="transition-all duration-150 cursor-pointer"
          on:mouseenter={() => hoveredPoint = pt}
          on:mouseleave={() => hoveredPoint = null}
        />
      {/each}
    </svg>
  </div>
</div>
