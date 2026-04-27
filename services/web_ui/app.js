// ===== Mock Data Engine =====
const STOCKS = {
  QQQ: {
    name: 'Invesco QQQ ETF',
    price: 447.82,
    change: +5.21,
    pct: +1.18,
    high: 449.30,
    low: 440.12,
    open: 441.50,
    volume: '38.2M',
    avgVol: '41.5M',
    mktCap: '-',
    rsi: 58.4,
    macdLine: 3.21,
    macdSignal: 2.18,
    sma20: 443.10,
    sma50: 429.80,
    bb_upper: 460.2,
    bb_lower: 425.8,
    signal: 'BUY',
    aiScore: 74,
    color: '#00d4ff',
  },
  VOO: {
    name: 'Vanguard S&P 500 ETF',
    price: 512.47,
    change: +4.86,
    pct: +0.96,
    high: 513.81,
    low: 506.22,
    open: 507.60,
    volume: '25.1M',
    avgVol: '28.7M',
    mktCap: '-',
    rsi: 54.7,
    macdLine: 1.85,
    macdSignal: 1.40,
    sma20: 509.20,
    sma50: 496.30,
    bb_upper: 526.4,
    bb_lower: 492.0,
    signal: 'HOLD',
    aiScore: 62,
    color: '#8b5cf6',
  },
  TSLA: {
    name: 'Tesla, Inc.',
    price: 243.15,
    change: -6.87,
    pct: -2.75,
    high: 251.40,
    low: 241.60,
    open: 250.20,
    volume: '112.4M',
    avgVol: '89.2M',
    mktCap: '780B',
    rsi: 38.2,
    macdLine: -4.30,
    macdSignal: -2.10,
    sma20: 256.80,
    sma50: 282.40,
    bb_upper: 278.3,
    bb_lower: 220.5,
    signal: 'SELL',
    aiScore: 32,
    color: '#ff4c6a',
  }
};

const NEWS = [
  {
    ticker: 'QQQ', tag: 'EARNINGS', sentiment: 'bullish',
    title: 'Nasdaq tech stocks surge as inflation data shows cooling, Fed signals possible pause',
    source: 'Reuters', time: '2h ago'
  },
  {
    ticker: 'TSLA', tag: 'EXECUTIVE', sentiment: 'bearish',
    title: 'Tesla delivery numbers disappoint Q1 estimates despite price cuts across model lineup',
    source: 'Bloomberg', time: '3h ago'
  },
  {
    ticker: 'VOO', tag: 'MACRO', sentiment: 'neutral',
    title: 'S&P 500 holds steady as investors weigh mixed jobs report against earnings season outlook',
    source: 'CNBC', time: '5h ago'
  },
  {
    ticker: 'TSLA', tag: 'POLITICS', sentiment: 'bearish',
    title: 'EV tax credit changes could impact Tesla\'s competitive edge in key markets, analysts warn',
    source: 'WSJ', time: '7h ago'
  },
  {
    ticker: 'QQQ', tag: 'TECH', sentiment: 'bullish',
    title: 'AI infrastructure spending boom continues; semiconductor demand exceeds earlier projections',
    source: 'FT', time: '9h ago'
  }
];

// ===== Chart Data Generator =====
function genPriceData(base, count, vol = 0.005) {
  const data = [];
  let price = base;
  const now = Date.now();
  for (let i = count; i >= 0; i--) {
    const drift = (Math.random() - 0.48) * vol;
    price = +(price * (1 + drift)).toFixed(2);
    data.push({ time: Math.floor((now - i * 5 * 60 * 1000) / 1000), value: price });
  }
  return data;
}

function genCandleData(base, count, vol = 0.007) {
  const data = [];
  let close = base;
  const now = Date.now();
  for (let i = count; i >= 0; i--) {
    const open = close;
    const change = (Math.random() - 0.48) * vol;
    close = +(open * (1 + change)).toFixed(2);
    const high = +(Math.max(open, close) * (1 + Math.random() * vol * 0.5)).toFixed(2);
    const low = +(Math.min(open, close) * (1 - Math.random() * vol * 0.5)).toFixed(2);
    data.push({ time: Math.floor((now - i * 5 * 60 * 1000) / 1000), open, high, low, close });
  }
  return data;
}

function genRSIData(count) {
  const data = [];
  let rsi = 50;
  const now = Date.now();
  for (let i = count; i >= 0; i--) {
    rsi = Math.max(10, Math.min(90, rsi + (Math.random() - 0.5) * 8));
    data.push({ time: Math.floor((now - i * 5 * 60 * 1000) / 1000), value: +rsi.toFixed(1) });
  }
  return data;
}

function genMACDData(count) {
  const macd = [], signal = [], hist = [];
  let m = 0, s = 0;
  const now = Date.now();
  for (let i = count; i >= 0; i--) {
    m += (Math.random() - 0.5) * 1.5;
    s = s * 0.85 + m * 0.15;
    const t = Math.floor((now - i * 5 * 60 * 1000) / 1000);
    macd.push({ time: t, value: +m.toFixed(3) });
    signal.push({ time: t, value: +s.toFixed(3) });
    hist.push({ time: t, value: +(m - s).toFixed(3) });
  }
  return { macd, signal, hist };
}

function genVolumeData(base, count) {
  const data = [];
  const now = Date.now();
  for (let i = count; i >= 0; i--) {
    const vol = Math.floor(base * (0.5 + Math.random() * 1.2));
    const up = Math.random() > 0.5;
    data.push({ time: Math.floor((now - i * 5 * 60 * 1000) / 1000), value: vol, color: up ? 'rgba(0,230,118,0.5)' : 'rgba(255,76,106,0.5)' });
  }
  return data;
}

// ===== App State =====
let currentPage = 'dashboard';
let currentStock = 'QQQ';
let charts = {};
let stockData = {};       // Stores history: stockData[symbol][interval]
let stockStats = {};      // Stores latest summary (stats) for each stock
let indicatorData = {};   // Stores computed technical indicators per stock
let watchlist = [];
let authToken = localStorage.getItem('brstock_token');
let currentInterval = '1d';
let authMode = 'login'; // 'login' or 'register'

async function initWatchlist() {
  const data = await apiFetch('/api/watchlist');
  watchlist = data || ['QQQ', 'VOO', 'TSLA', 'NVDA', 'AAPL', 'MSFT', 'AMZN', 'META', 'GOOGL'];
}

// ===== API Fetching =====
async function apiFetch(endpoint, options = {}) {
  const headers = { ...options.headers };
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  try {
    const response = await fetch(endpoint, { ...options, headers });

    if (response.status === 401) {
      console.warn('Unauthorized: Clearing token and showing login.');
      logout();
      return null;
    }

    if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
    return await response.json();
  } catch (err) {
    console.error(`Failed to fetch ${endpoint}:`, err);
    return null;
  }
}

async function refreshAllData() {
  const promises = watchlist.map(async (s) => {
    const [history, summary] = await Promise.all([
      apiFetch(`/api/stocks/${s}/history?interval=1d`), // Dashboard usually wants daily
      apiFetch(`/api/stocks/${s}/summary`)
    ]);
    if (history) {
      if (!stockData[s]) stockData[s] = {};
      stockData[s]['1d'] = history;
    }
    if (summary) stockStats[s] = summary;
  });
  await Promise.all(promises);
}

// ===== Page Navigation =====
async function navigate(page) {
  currentPage = page;
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById(`page-${page}`).classList.add('active');
  document.querySelector(`[data-page="${page}"]`).classList.add('active');

  const titles = {
    dashboard: '📊 Market Dashboard',
    chart: '📈 Chart Analysis',
    ai: '🤖 AI Insights'
  };
  document.getElementById('page-title').textContent = titles[page];

  if (page === 'dashboard') {
    await refreshAllData();
    renderDashboard();
  }
  if (page === 'chart') {
    await refreshStockData(currentStock, currentInterval);
    initChartPage();
  }
  if (page === 'ai') {
    renderAIPage();
  }
}

async function refreshStockData(symbol, interval = '1d') {
  const [history, summary, indicators] = await Promise.all([
    apiFetch(`/api/stocks/${symbol}/history?interval=${interval}`),
    apiFetch(`/api/stocks/${symbol}/summary`),
    apiFetch(`/api/stocks/${symbol}/indicators?interval=${interval}`)
  ]);
  
  if (!stockData[symbol]) stockData[symbol] = {};
  // Always overwrite the specific interval data, or set to empty if failed
  stockData[symbol][interval] = history || { data: [] };
  
  if (summary) stockStats[symbol] = summary;
  if (indicators) indicatorData[symbol] = indicators;
}

async function changeInterval(interval, btn) {
  currentInterval = interval;
  // UI update
  if (btn) {
    const tabs = btn.closest('.interval-tabs');
    if (tabs) {
      tabs.querySelectorAll('.interval-tab').forEach(t => t.classList.remove('active'));
      btn.classList.add('active');
    }
  }
  
  // Reload data and redraw
  await refreshStockData(currentStock, interval);
  initChartPage();
}

// ===== Dashboard =====
function renderDashboard() {
  renderStockCards();
  renderMiniCharts();
  renderTopMovers();
  renderAISummary();
}



function renderTopMovers() {
  const list = document.getElementById('top-movers-list');
  if (!list) return;
  // Sort watchlist by change pct
  const sorted = [...watchlist].sort((a, b) => {
    const sa = stockStats[a]?.change_pct || 0;
    const sb = stockStats[b]?.change_pct || 0;
    return Math.abs(sb) - Math.abs(sa);
  }).slice(0, 5); // Top 5

  list.innerHTML = sorted.map(ticker => {
    const s = stockStats[ticker];
    if (!s) return '';
    const isUp = s.change >= 0;
    return `
      <div class="stats-list-item">
        <span class="label">${ticker} – ${s.name || ''}</span>
        <span class="val ${isUp ? 'text-green' : 'text-red'}">${isUp ? '+' : ''}${s.change_pct.toFixed(2)}%</span>
      </div>
    `;
  }).join('');
}

function renderAISummary() {
  const list = document.getElementById('ai-score-summary-list');
  if (!list) return;

  list.innerHTML = watchlist.slice(0, 5).map(ticker => {
    const score = ticker === 'QQQ' ? 74 : ticker === 'TSLA' ? 32 : 60;
    const color = score > 65 ? 'var(--accent-green)' : score < 40 ? 'var(--accent-red)' : '#fbbf24';
    return `
      <div class="stats-list-item">
        <span class="label">${ticker} AI Score</span>
        <span class="val" style="color:${color}">${score} / 100</span>
      </div>
    `;
  }).join('');
}

function renderStockCards() {
  const grid = document.getElementById('watchlist-grid');
  if (!grid) return;

  grid.innerHTML = watchlist.map(ticker => {
    const s = stockStats[ticker];
    if (!s) return `<div class="stock-card skeleton" style="height:140px"></div>`;

    const isUp = s.change >= 0;
    const signal = ticker === 'QQQ' ? 'BUY' : ticker === 'TSLA' ? 'SELL' : 'HOLD'; // Mock signal for now
    const signalClass = { BUY: 'signal-buy', SELL: 'signal-sell', HOLD: 'signal-hold' }[signal];

    return `
      <div class="stock-card ${currentStock === ticker ? 'selected' : ''}" onclick="selectStock('${ticker}')" id="card-${ticker}">
        <div class="stock-card-header">
          <div>
            <div class="ticker-badge">${ticker}</div>
            <div class="ticker-name">${ticker === 'QQQ' ? 'Invesco QQQ ETF' : ticker === 'VOO' ? 'Vanguard S&P 500' : 'Tesla, Inc.'}</div>
          </div>
          <div style="display:flex; flex-direction:column; align-items:flex-end; gap:4px">
            <span class="signal-badge ${signalClass}">${signal}</span>
            <button class="btn-icon" onclick="removeStock('${ticker}', event)" style="font-size:10px; opacity:0.5; background:none; border:none; color:var(--text-muted); cursor:pointer">✕ Remove</button>
          </div>
        </div>
        <div class="stock-price ${isUp ? 'text-green' : 'text-red'}">$${s.price.toFixed(2)}</div>
        <div class="stock-change ${isUp ? 'text-green' : 'text-red'}">
          ${isUp ? '▲' : '▼'} ${Math.abs(s.change).toFixed(2)} (${isUp ? '+' : ''}${s.change_pct.toFixed(2)}%)
        </div>
        <canvas class="mini-chart" id="mini-${ticker}"></canvas>
        <div class="stock-indicators">
          <span class="indicator-chip">RSI 58.4</span>
          <span class="indicator-chip">Vol ${(s.volume / 1000000).toFixed(1)}M</span>
          <span class="indicator-chip" style="color:${isUp ? 'var(--accent-green)' : 'var(--accent-red)'}">
            SMA20 ${(s.price * 0.99).toFixed(2)}
          </span>
        </div>
      </div>
    `;
  }).join('');
}

function renderMiniCharts() {
  const symbols = watchlist.slice(0, 9); // Show up to 9 mini charts
  symbols.forEach(ticker => {
    const canvas = document.getElementById(`mini-${ticker}`);
    // Check nested structure
    const hData = stockData[ticker] && stockData[ticker]['1d'];
    if (!canvas || !hData || !hData.data || hData.data.length === 0) return;

    const ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth * 2;
    canvas.height = canvas.offsetHeight * 2;
    ctx.scale(2, 2);

    const w = canvas.offsetWidth, h = canvas.offsetHeight;
    const vals = hData.data.slice(-30).map(d => d.Close);
    if (vals.length === 0) return;
    const min = Math.min(...vals), max = Math.max(...vals);
    const range = (max - min) || 1;

    const points = vals.map((v, i) => ({
      x: (i / (vals.length - 1)) * w,
      y: h - ((v - min) / range) * h * 0.8 - h * 0.1
    }));

    const isUp = stockStats[ticker].change >= 0;
    const color = isUp ? '#00e676' : '#ff4c6a';

    // Gradient fill
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, isUp ? 'rgba(0,230,118,0.3)' : 'rgba(255,76,106,0.3)');
    grad.addColorStop(1, 'rgba(0,0,0,0)');

    ctx.beginPath();
    if (points.length > 0) {
      ctx.moveTo(points[0].x, h);
      points.forEach(p => ctx.lineTo(p.x, p.y));
      ctx.lineTo(points[points.length - 1].x, h);
    }
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // Line
    if (points.length > 0) {
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      points.forEach(p => ctx.lineTo(p.x, p.y));
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  });
}

function selectStock(ticker) {
  currentStock = ticker;
  navigate('chart');
}

// ===== Chart Page =====
function initChartPage() {
  const s = stockStats[currentStock];
  if (!s) return;
  const priceEl = document.getElementById('chart-price');
  const changeEl = document.getElementById('chart-change-display');
  const isUp = s.change >= 0;

  const tickerEl = document.getElementById('chart-ticker');
  const nameEl = document.getElementById('chart-name');
  if (tickerEl) tickerEl.textContent = currentStock;
  if (nameEl) nameEl.textContent = s.name || currentStock;
  if (priceEl) priceEl.textContent = `$${s.price.toFixed(2)}`;
  if (changeEl) {
    changeEl.innerHTML = `<span class="${isUp ? 'text-green' : 'text-red'}">
      ${isUp ? '▲' : '▼'} ${Math.abs(s.change).toFixed(2)} (${isUp ? '+' : ''}${s.change_pct.toFixed(2)}%)
    </span>`;
  }

  // Stats - Defensive Checks
  const setS = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  setS('stat-open', `$${s.open.toFixed(2)}`);
  setS('stat-high', `$${s.high.toFixed(2)}`);
  setS('stat-low', `$${s.low.toFixed(2)}`);
  setS('stat-vol', (s.volume / 1000000).toFixed(2) + 'M');
  setS('stat-avgvol', '-');

  // ── Real Moving Averages ──
  const ind = indicatorData[currentStock];
  if (ind && ind.moving_averages) {
    const ma = ind.moving_averages;
    setS('stat-sma20', ma.sma20_latest != null ? `$${ma.sma20_latest.toFixed(2)}` : '-');
    setS('stat-sma50', ma.sma50_latest != null ? `$${ma.sma50_latest.toFixed(2)}` : '-');
    setS('stat-ema20', ma.ema20_latest != null ? `$${ma.ema20_latest.toFixed(2)}` : '-');
    setS('stat-ema50', ma.ema50_latest != null ? `$${ma.ema50_latest.toFixed(2)}` : '-');
  }

  // ── Real Technical Indicators panel ──
  if (ind) {
    const rsi = (ind.rsi && ind.rsi.latest) || null;
    const rsiEl = document.getElementById('ind-rsi');
    if (rsiEl) {
      rsiEl.textContent = rsi != null ? rsi.toFixed(1) : '–';
      rsiEl.className = `value ${rsi >= 70 ? 'text-red' : rsi <= 30 ? 'text-green' : 'text-blue'}`;
    }
    const rsiSignalMap = { overbought: '⚠️ Overbought', oversold: '✅ Oversold', neutral: '► Neutral', unknown: '' };
    setS('ind-rsi-signal', rsiSignalMap[ind.rsi && ind.rsi.signal] || '');

    // MACD
    const macdVal = (ind.macd && ind.macd.macd_latest) || null;
    const macdEl = document.getElementById('ind-macd');
    if (macdEl) {
      macdEl.textContent = macdVal != null ? macdVal.toFixed(2) : '–';
      macdEl.className = `value ${macdVal >= 0 ? 'text-green' : 'text-red'}`;
    }
    setS('ind-macd-signal', (ind.macd && ind.macd.signal === 'bullish') ? '▲ Bullish Cross' : '▼ Bearish Cross');

    // BB placeholders
    setS('ind-bb-upper', (s.price * 1.05).toFixed(2));
    setS('ind-bb-lower', (s.price * 0.95).toFixed(2));
  } else {
    // Fallback: mock values (safely)
    setS('ind-rsi', '58.4');
    setS('ind-rsi-signal', '► Neutral');
    setS('ind-macd', '3.21');
    setS('ind-macd-signal', '▲ Bullish Cross');
    setS('ind-bb-upper', (s.price * 1.05).toFixed(2));
    setS('ind-bb-lower', (s.price * 0.95).toFixed(2));
  }

  // AI Score (Mocked)
  const score = currentStock === 'QQQ' ? 74 : currentStock === 'VOO' ? 62 : 32;
  const signal = currentStock === 'QQQ' ? 'BUY' : currentStock === 'VOO' ? 'HOLD' : 'SELL';
  const scoreColor = score > 65 ? 'var(--accent-green)' : score < 40 ? 'var(--accent-red)' : '#fbbf24';
  const signalClass = signal === 'BUY' ? 'signal-buy' : signal === 'SELL' ? 'signal-sell' : 'signal-hold';

  // Top bar mini score
  const scoreValEl = document.getElementById('ai-score-val');
  const scoreFillEl = document.getElementById('ai-score-fill');
  const scoreLabelEl = document.getElementById('ai-score-label');
  if (scoreValEl) scoreValEl.textContent = score;
  if (scoreFillEl) { scoreFillEl.style.width = score + '%'; scoreFillEl.style.background = scoreColor; }
  if (scoreLabelEl) { scoreLabelEl.textContent = signal; scoreLabelEl.className = `score-label ${signal === 'BUY' ? 'text-green' : signal === 'SELL' ? 'text-red' : ''}`; }

  // Bottom panel large score + signal badge
  const scoreVal2El = document.getElementById('ai-score-val2');
  const scoreFill2El = document.getElementById('ai-score-fill2');
  const signalTextEl = document.getElementById('ai-signal-text');
  if (scoreVal2El) scoreVal2El.textContent = score;
  if (scoreFill2El) { scoreFill2El.style.width = score + '%'; scoreFill2El.style.background = scoreColor; }
  if (signalTextEl) { signalTextEl.textContent = signal; signalTextEl.className = `signal-badge ${signalClass}`; }

  // Init LightweightCharts
  drawCharts();

  // ── Render Dynamic Switch Symbol List ──
  renderSwitchSymbol();
}

function renderSwitchSymbol() {
  const list = document.getElementById('switch-symbol-list');
  if (!list) return;
  list.innerHTML = watchlist.map(ticker => {
    const s = stockStats[ticker];
    const changePct = s ? s.change_pct : 0;
    const isUp = changePct >= 0;
    return `
      <button class="btn btn-ghost" onclick="selectStock('${ticker}')" style="justify-content:space-between; ${ticker === currentStock ? 'background:rgba(255,255,255,0.05); border:1px solid var(--accent-blue)' : ''}">
        <span>${ticker}</span>
        <span class="${isUp ? 'text-green' : 'text-red'}">${isUp ? '+' : ''}${changePct.toFixed(2)}%</span>
      </button>
    `;
  }).join('');
}

function drawCharts() {
  const LWC = LightweightCharts;
  const chartOptions = (height) => ({
    width: document.getElementById('kline-chart').offsetWidth,
    height,
    layout: { background: { color: 'transparent' }, textColor: '#7a8aab' },
    grid: { vertLines: { color: 'rgba(255,255,255,0.04)' }, horzLines: { color: 'rgba(255,255,255,0.04)' } },
    rightPriceScale: { borderColor: 'rgba(255,255,255,0.08)', scaleMargins: { top: 0.1, bottom: 0.1 } },
    timeScale: { borderColor: 'rgba(255,255,255,0.08)', timeVisible: true, secondsVisible: false },
    crosshair: { mode: LWC.CrosshairMode.Normal }
  });

  const hData = stockData[currentStock] && stockData[currentStock][currentInterval];
  if (!hData || !hData.data || hData.data.length === 0) {
    // Clear charts if no data
    if (charts.kline) { try { charts.kline.remove(); charts.kline = null; } catch (e) { } }
    if (charts.volume) { try { charts.volume.remove(); charts.volume = null; } catch (e) { } }
    const klineEl = document.getElementById('kline-chart');
    if (klineEl) klineEl.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted)">No historical data found for this interval. Please run the data pipeline.</div>';
    return;
  }

  const rawData = hData.data;
  // Map back-end OHLC to LWC format and handle string timestamps
  const candleData = rawData.map(d => ({
    time: Math.floor(new Date(d.timestamp).getTime() / 1000),
    open: d.Open,
    high: d.High,
    low: d.Low,
    close: d.Close
  }));

  // K-line
  if (charts.kline) { try { charts.kline.remove(); } catch (e) { } }
  const klineEl = document.getElementById('kline-chart');
  charts.kline = LWC.createChart(klineEl, chartOptions(340));
  const candleSeries = charts.kline.addCandlestickSeries({
    upColor: '#00e676', downColor: '#ff4c6a',
    borderUpColor: '#00e676', borderDownColor: '#ff4c6a',
    wickUpColor: '#00e676', wickDownColor: '#ff4c6a',
  });
  candleSeries.setData(candleData);

  // ── SMA / EMA Overlay on K-line chart ──
  const ind = indicatorData[currentStock];
  if (ind && ind.moving_averages && ind.moving_averages.history.length) {
    const maHist = ind.moving_averages.history;
    const toTime = ts => Math.floor(new Date(ts).getTime() / 1000);

    const sma20Data = maHist.filter(d => d.sma20 != null).map(d => ({ time: toTime(d.timestamp), value: d.sma20 }));
    const sma50Data = maHist.filter(d => d.sma50 != null).map(d => ({ time: toTime(d.timestamp), value: d.sma50 }));
    const ema20Data = maHist.filter(d => d.ema20 != null).map(d => ({ time: toTime(d.timestamp), value: d.ema20 }));
    const ema50Data = maHist.filter(d => d.ema50 != null).map(d => ({ time: toTime(d.timestamp), value: d.ema50 }));

    if (sma20Data.length) {
      const sma20Series = charts.kline.addLineSeries({ color: '#00d4ff', lineWidth: 1.5, title: 'SMA20', lastValueVisible: true, priceLineVisible: false });
      sma20Series.setData(sma20Data);
    }
    if (sma50Data.length) {
      const sma50Series = charts.kline.addLineSeries({ color: '#fbbf24', lineWidth: 1.5, title: 'SMA50', lastValueVisible: true, priceLineVisible: false });
      sma50Series.setData(sma50Data);
    }
    if (ema20Data.length) {
      const ema20Series = charts.kline.addLineSeries({ color: '#a78bfa', lineWidth: 1, title: 'EMA20', lineStyle: 1, lastValueVisible: true, priceLineVisible: false });
      ema20Series.setData(ema20Data);
    }
    if (ema50Data.length) {
      const ema50Series = charts.kline.addLineSeries({ color: '#fb923c', lineWidth: 1, title: 'EMA50', lineStyle: 1, lastValueVisible: true, priceLineVisible: false });
      ema50Series.setData(ema50Data);
    }
  }

  // Vol
  const volumeData = rawData.map(d => ({
    time: Math.floor(new Date(d.timestamp).getTime() / 1000),
    value: d.Volume,
    color: d.Close >= d.Open ? 'rgba(0,230,118,0.5)' : 'rgba(255,76,106,0.5)'
  }));

  if (charts.volume) { try { charts.volume.remove(); } catch (e) { } }
  const volEl = document.getElementById('volume-chart');
  charts.volume = LWC.createChart(volEl, { ...chartOptions(90), timeScale: { visible: false } });
  const volSeries = charts.volume.addHistogramSeries({ priceFormat: { type: 'volume' } });
  volSeries.setData(volumeData);

  // ── RSI (real data from backend) ──
  if (charts.rsi) { try { charts.rsi.remove(); } catch (e) { } }
  const rsiEl = document.getElementById('rsi-chart');
  charts.rsi = LWC.createChart(rsiEl, { ...chartOptions(100), timeScale: { visible: false } });
  const rsiSeries = charts.rsi.addLineSeries({ color: '#00d4ff', lineWidth: 1.5, priceFormat: { minMove: 0.01 } });

  // Overbought / Oversold reference lines
  const rsiPriceLine70 = { price: 70, color: 'rgba(255,76,106,0.5)', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: 'OB' };
  const rsiPriceLine30 = { price: 30, color: 'rgba(0,230,118,0.5)', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: 'OS' };
  rsiSeries.createPriceLine(rsiPriceLine70);
  rsiSeries.createPriceLine(rsiPriceLine30);

  if (ind && ind.rsi && ind.rsi.history.length) {
    const rsiData = ind.rsi.history.map(d => ({
      time: Math.floor(new Date(d.timestamp).getTime() / 1000),
      value: d.value
    }));
    rsiSeries.setData(rsiData);
  }
  charts.rsi.priceScale('right').applyOptions({ autoScale: false, minimum: 0, maximum: 100 });

  // ── MACD (real data from backend) ──
  if (charts.macd) { try { charts.macd.remove(); } catch (e) { } }
  const macdEl = document.getElementById('macd-chart');
  charts.macd = LWC.createChart(macdEl, { ...chartOptions(110), timeScale: { visible: false } });

  if (ind && ind.macd && ind.macd.history.length) {
    const toTime = ts => Math.floor(new Date(ts).getTime() / 1000);
    const mhist = ind.macd.history;

    const histData = mhist.map(d => ({
      time: toTime(d.timestamp),
      value: d.histogram,
      color: d.histogram >= 0 ? 'rgba(0,230,118,0.6)' : 'rgba(255,76,106,0.6)'
    }));
    const macdLineData = mhist.map(d => ({ time: toTime(d.timestamp), value: d.macd }));
    const signalLineData = mhist.map(d => ({ time: toTime(d.timestamp), value: d.signal }));

    const histSeries = charts.macd.addHistogramSeries({ priceFormat: { minMove: 0.001 } });
    histSeries.setData(histData);
    const macdLineSeries = charts.macd.addLineSeries({ color: '#00d4ff', lineWidth: 1.5 });
    macdLineSeries.setData(macdLineData);
    const signalLineSeries = charts.macd.addLineSeries({ color: '#fbbf24', lineWidth: 1 });
    signalLineSeries.setData(signalLineData);
  } else {
    // Fallback: mock MACD if backend data not available
    const { macd, signal, hist } = genMACDData(120);
    const histSeries = charts.macd.addHistogramSeries({ color: 'rgba(0,212,255,0.5)', priceFormat: { minMove: 0.001 } });
    histSeries.setData(hist.map(d => ({ ...d, color: d.value >= 0 ? 'rgba(0,230,118,0.6)' : 'rgba(255,76,106,0.6)' })));
    const macdLineSeries = charts.macd.addLineSeries({ color: '#00d4ff', lineWidth: 1.5 });
    macdLineSeries.setData(macd);
    const signalLineSeries = charts.macd.addLineSeries({ color: '#fbbf24', lineWidth: 1 });
    signalLineSeries.setData(signal);
  }

  // ── Sync and Zoom ──
  // Sync the main chart's time scale to others (Volume, RSI, MACD)
  charts.kline.timeScale().subscribeVisibleTimeRangeChange(range => {
    if (charts.volume) charts.volume.timeScale().setVisibleRange(range);
    if (charts.rsi) charts.rsi.timeScale().setVisibleRange(range);
    if (charts.macd) charts.macd.timeScale().setVisibleRange(range);
  });

  // Zoom to last year (approx 252 trading days) for 1D/1W/1M
  if (currentInterval !== '5m' && candleData.length > 252) {
    charts.kline.timeScale().setVisibleRange({
      from: candleData[candleData.length - 252].time,
      to: candleData[candleData.length - 1].time
    });
  } else {
    charts.kline.timeScale().fitContent();
  }
} // end drawCharts

// ===== AI Page =====
function renderAIPage() {
  // Signal grid
  const grid = document.getElementById('signal-grid');
  if (!grid) return;
  grid.innerHTML = watchlist.map(ticker => {
    const s = stockStats[ticker] || { change_pct: 0 };
    const signal = ticker === 'QQQ' ? 'BUY' : ticker === 'TSLA' ? 'SELL' : (s.change_pct > 0 ? 'BUY' : 'HOLD');
    const aiScore = ticker === 'QQQ' ? 74 : ticker === 'TSLA' ? 32 : 60;

    const bgColor = { BUY: 'var(--accent-green-dim)', SELL: 'var(--accent-red-dim)', HOLD: 'rgba(251,191,36,0.08)' }[signal];
    const textColor = { BUY: 'var(--accent-green)', SELL: 'var(--accent-red)', HOLD: '#fbbf24' }[signal];
    return `
      <div class="signal-item" style="background:${bgColor}; border: 1px solid ${textColor}22;">
        <div class="s-ticker">${ticker}</div>
        <div class="s-action" style="color:${textColor}">${signal}</div>
        <div class="s-confidence" style="color:${textColor}">AI ${aiScore}%</div>
      </div>`;
  }).join('');
  renderNews();
}

function renderNews() {
  const list = document.getElementById('news-list');
  list.innerHTML = NEWS.map(n => `
    <div class="news-item">
      <div class="news-tag">
        <span class="indicator-chip" style="font-size:9px">${n.ticker}</span>
        <span style="color:var(--text-muted)">${n.tag}</span>
      </div>
      <h4>${n.title}</h4>
      <div class="news-meta">
        <span>${n.source}</span>
        <span>${n.time}</span>
        <span class="sentiment-tag sentiment-${n.sentiment}">${n.sentiment.toUpperCase()}</span>
      </div>
    </div>
  `).join('');
}

// ===== Clock =====
function updateClock() {
  const el = document.getElementById('market-time');
  if (!el) return;
  const now = new Date();
  const nyTime = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
  }).format(now);
  const h = parseInt(nyTime.split(':')[0]);
  const isOpen = h >= 9 && h < 16;
  el.innerHTML = `NYSE ${nyTime} ET &nbsp; <span style="color:${isOpen ? 'var(--accent-green)' : 'var(--accent-red)'}">● ${isOpen ? 'OPEN' : 'CLOSED'}</span>`;
}

// ===== Global stats =====
function renderGlobalStats() {
  document.getElementById('spy-val').textContent = '+1.05%';
  document.getElementById('vix-val').textContent = '17.32';
  document.getElementById('fear-val').textContent = '42 – Neutral';
  document.getElementById('ai-picks').textContent = '2 BUY · 1 SELL';
}

// ===== Init =====
window.addEventListener('load', async () => {
  updateClock();
  setInterval(updateClock, 1000);

  // 无论是否登录，直接加载数据
  await initWatchlist();
  await refreshAllData();
  renderDashboard();
  renderGlobalStats();
  navigate('dashboard');

  updateAuthUI();
});

function updateAuthUI() {
  const logoutBtn = document.getElementById('btn-logout');
  if (logoutBtn) {
    logoutBtn.innerHTML = authToken ? '<span class="icon">🚪</span><span>Logout</span>' : '<span class="icon">👤</span><span>Login</span>';
  }
}

function handleLogoutOrLogin() {
  if (authToken) {
    localStorage.removeItem('brstock_token');
    authToken = null;
    location.reload(); // 重新加载以游客身份进入
  } else {
    showAuthModal();
  }
}

window.addEventListener('resize', () => {
  if (currentPage === 'chart') {
    Object.values(charts).forEach(c => { try { c.timeScale().fitContent(); } catch (e) { } });
  }
});

async function generateAIAnalysis() {
  const btn = document.getElementById('btn-generate-ai-analysis');
  const content = document.getElementById('ai-analysis-content');

  if (!btn || !content) return;

  // Set loading state
  btn.disabled = true;
  btn.textContent = '⌛ Generating...';
  content.innerHTML = `
    <div style="display: flex; flex-direction: column; gap: 12px; padding: 10px;">
      <div style="color: var(--accent-blue); font-weight: bold; font-size: 14px; margin-bottom: 8px;">🤖 AI is analyzing technical patterns... Please wait.</div>
      <div class="skeleton" style="height: 16px; width: 100%; border-radius: 4px;"></div>
      <div class="skeleton" style="height: 16px; width: 90%; border-radius: 4px;"></div>
      <div class="skeleton" style="height: 16px; width: 95%; border-radius: 4px;"></div>
      <div class="skeleton" style="height: 16px; width: 60%; border-radius: 4px;"></div>
    </div>
  `;
  // Scroll it into view so the user knows something is happening below
  content.scrollIntoView({ behavior: 'smooth', block: 'center' });


  try {
    const lang = document.getElementById('ai-lang-select')?.value || 'en';
    const url = `/api/stocks/${currentStock}/ai_analysis?lang=${lang}`;
    console.log(`[AI-AGENT] Fetching: ${url}`);
    const res = await apiFetch(url);
    console.log(`[AI-AGENT] Result:`, res);
    if (res && res.analysis) {
      content.textContent = res.analysis;
    } else {
      content.innerHTML = `<span class="text-red">Error: Could not retrieve AI analysis.</span>`;
    }
  } catch (err) {
    console.error('AI Analysis Fetch Error:', err);
    content.innerHTML = `<span class="text-red">Error: ${err.message}</span>`;
  } finally {
    btn.disabled = false;
    btn.textContent = '⟳ Generate Analysis';
  }
}
// ===== Search & Add Watchlist Logic =====
async function handleSearchInput(e) {
  // Called on keydown — read value from the input element directly
  const input = e.target || e;
  const q = (input.value || '').trim();
  const resultsEl = document.getElementById('search-results');
  if (!resultsEl) return;

  if (q.length < 2) {
    resultsEl.style.display = 'none';
    return;
  }

  const results = await apiFetch(`/api/stocks/search?q=${encodeURIComponent(q)}`);
  if (results && results.length > 0) {
    resultsEl.innerHTML = results.map(r => `
      <div class="search-result-item" onclick="handleSearchResultClick('${r.ticker}')">
        <span class="ticker">${r.ticker}</span>
        <span class="name">${r.name}</span>
      </div>
    `).join('');
    resultsEl.style.display = 'block';
  } else {
    resultsEl.style.display = 'none';
  }
}

function handleSearchResultClick(ticker) {
  document.getElementById('search-results').style.display = 'none';
  document.getElementById('search-input').value = '';
  addStock(ticker);
}

async function addStockFromInput() {
  const input = document.getElementById('add-stock-input');
  const symbol = input.value.toUpperCase().trim();
  if (!symbol) return;

  await addStock(symbol);
  input.value = '';
}

async function addStock(symbol) {
  if (!authToken) {
    alert("Please login to add stocks to your personal watchlist.");
    showAuthModal();
    return;
  }
  const statusEl = document.getElementById('add-stock-status');
  if (statusEl) statusEl.textContent = `⏳ Adding ${symbol}...`;

  // 1. Trigger fetch to ensure data exists
  const res = await fetch(`/api/stocks/${symbol}/fetch`, { method: 'POST' });
  if (!res.ok) {
    if (statusEl) statusEl.textContent = `❌ Error fetching data for ${symbol}`;
    return;
  }

  // 2. Add to DB watchlist
  await fetch(`/api/watchlist/${symbol}`, { method: 'POST' });

  // 3. Update local state and refresh
  await initWatchlist();
  await refreshAllData();

  if (statusEl) statusEl.textContent = `✅ ${symbol} added to watchlist!`;

  if (currentPage === 'dashboard') renderDashboard();
  currentStock = symbol;
  navigate('chart');
}

async function removeStock(symbol, event) {
  if (event) event.stopPropagation(); // Don't navigate to chart
  if (!authToken) {
    alert("Please login to manage your watchlist.");
    showAuthModal();
    return;
  }
  if (!confirm(`Remove ${symbol} from watchlist?`)) return;

  await fetch(`/api/watchlist/${symbol}`, { method: 'DELETE' });
  await initWatchlist();
  renderDashboard();
}

// Close search results when clicking outside
document.addEventListener('click', e => {
  const box = document.querySelector('.search-box');
  const results = document.getElementById('search-results');
  if (box && results && !box.contains(e.target)) {
    results.style.display = 'none';
  }
});

// ===== Authentication Logic =====
function showAuthModal() {
  document.getElementById('auth-overlay').style.display = 'flex';
}

function hideAuthModal() {
  document.getElementById('auth-overlay').style.display = 'none';
}

function toggleAuthMode() {
  authMode = authMode === 'login' ? 'register' : 'login';
  updateAuthModeUI();
}

function showResetMode() {
  authMode = 'reset';
  updateAuthModeUI();
}

function showLoginMode() {
  authMode = 'login';
  updateAuthModeUI();
}

function updateAuthModeUI() {
  const isLogin = authMode === 'login';
  const isReg = authMode === 'register';
  const isReset = authMode === 'reset';

  document.getElementById('auth-title').textContent =
    isLogin ? 'Login to BRStock AI' : (isReg ? 'Create an Account' : 'Reset Password');
  document.getElementById('auth-subtitle').textContent =
    isLogin ? 'Access your personal watchlist and AI insights' :
      (isReg ? 'Join our intelligent market community' : 'Enter your email and Secret PIN to reset');

  document.getElementById('btn-auth-submit').textContent =
    isLogin ? 'Login' : (isReg ? 'Sign Up' : 'Update Password');

  document.getElementById('group-fullname').style.display = isReg ? 'block' : 'none';
  document.getElementById('group-pin').style.display = (isReg || isReset) ? 'block' : 'none';
  document.getElementById('group-new-password').style.display = isReset ? 'block' : 'none';

  // Repurpose password field for login/reg
  document.getElementById('auth-password').closest('.input-group').style.display = isReset ? 'none' : 'block';

  document.getElementById('auth-switch-text').textContent = isLogin ? "Don't have an account?" : "Back to";
  document.getElementById('auth-switch-link').textContent = isLogin ? 'Sign Up' : 'Login';
  document.getElementById('auth-forgot-link').style.display = isLogin ? 'block' : 'none';
  document.getElementById('auth-error').style.display = 'none';
}

async function handleAuthSubmit() {
  const email = document.getElementById('auth-email').value.trim();
  const password = document.getElementById('auth-password').value.trim();
  const fullName = document.getElementById('auth-fullname').value.trim();
  const pin = document.getElementById('auth-pin').value.trim();
  const newPassword = document.getElementById('auth-new-password').value.trim();
  const errorEl = document.getElementById('auth-error');

  if (!email || (authMode !== 'reset' && !password)) {
    errorEl.textContent = 'Please fill in required fields';
    errorEl.style.display = 'block';
    return;
  }

  errorEl.style.display = 'none';
  const btn = document.getElementById('btn-auth-submit');
  btn.disabled = true;
  btn.textContent = '⌛ Processing...';

  try {
    if (authMode === 'register') {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, full_name: fullName, reset_pin: pin })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Registration failed');
      }
      authMode = 'login';
      updateAuthModeUI();
      errorEl.textContent = 'Registration successful! Please login.';
      errorEl.className = 'auth-error success'; // Assume a success class
      errorEl.style.display = 'block';
      return;
    }

    if (authMode === 'reset') {
      const res = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, reset_pin: pin, new_password: newPassword })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Reset failed');
      }
      authMode = 'login';
      updateAuthModeUI();
      alert('Password reset successful! Please login with your new password.');
      return;
    }

    // Login logic
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);

    const res = await fetch('/api/auth/login', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Invalid email or password');
    }

    const data = await res.json();
    authToken = data.access_token;
    localStorage.setItem('brstock_token', authToken);

    hideAuthModal();
    location.reload(); // Refresh fully to update all states

  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.className = 'auth-error';
    errorEl.style.display = 'block';
  } finally {
    btn.disabled = false;
    btn.textContent = authMode === 'login' ? 'Login' : (authMode === 'register' ? 'Sign Up' : 'Update Password');
  }
}
