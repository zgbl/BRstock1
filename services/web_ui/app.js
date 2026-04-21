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
let stockData = {};       // Stores latest history for each stock
let stockStats = {};      // Stores latest summary (stats) for each stock
let indicatorData = {};   // Stores computed technical indicators per stock

// ===== API Fetching =====
async function apiFetch(endpoint) {
  try {
    const response = await fetch(endpoint);
    if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
    return await response.json();
  } catch (err) {
    console.error(`Failed to fetch ${endpoint}:`, err);
    return null;
  }
}

async function refreshAllData() {
  const symbols = ['QQQ', 'VOO', 'TSLA'];
  const promises = symbols.map(async (s) => {
    const [history, summary] = await Promise.all([
      apiFetch(`/api/stocks/${s}/history?limit=200`),
      apiFetch(`/api/stocks/${s}/summary`)
    ]);
    if (history) stockData[s] = history;
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
    await refreshStockData(currentStock);
    initChartPage();
  }
  if (page === 'ai') {
    renderAIPage();
  }
}

async function refreshStockData(symbol) {
  const [history, summary, indicators] = await Promise.all([
    apiFetch(`/api/stocks/${symbol}/history?limit=200`),
    apiFetch(`/api/stocks/${symbol}/summary`),
    apiFetch(`/api/stocks/${symbol}/indicators`)
  ]);
  if (history)    stockData[symbol]     = history;
  if (summary)    stockStats[symbol]    = summary;
  if (indicators) indicatorData[symbol] = indicators;
}

// ===== Dashboard =====
function renderDashboard() {
  renderStockCards();
  renderMiniCharts();
}

function renderStockCards() {
  const grid = document.getElementById('watchlist-grid');
  const symbols = ['QQQ', 'VOO', 'TSLA'];
  grid.innerHTML = symbols.map(ticker => {
    const s = stockStats[ticker];
    if (!s) return `<div class="stock-card">Loading ${ticker}...</div>`;
    
    const isUp = s.change >= 0;
    const signal = ticker === 'QQQ' ? 'BUY' : ticker === 'TSLA' ? 'SELL' : 'HOLD'; // Mock signal for now
    const signalClass = { BUY: 'signal-buy', SELL: 'signal-sell', HOLD: 'signal-hold' }[signal];
    
    return `
      <div class="stock-card" onclick="selectStock('${ticker}')" id="card-${ticker}">
        <div class="stock-card-header">
          <div>
            <div class="ticker-badge">${ticker}</div>
            <div class="ticker-name">${ticker === 'QQQ' ? 'Invesco QQQ ETF' : ticker === 'VOO' ? 'Vanguard S&P 500' : 'Tesla, Inc.'}</div>
          </div>
          <span class="signal-badge ${signalClass}">${signal}</span>
        </div>
        <div class="stock-price ${isUp ? 'text-green' : 'text-red'}">$${s.price.toFixed(2)}</div>
        <div class="stock-change ${isUp ? 'text-green' : 'text-red'}">
          ${isUp ? '▲' : '▼'} ${Math.abs(s.change).toFixed(2)} (${isUp ? '+' : ''}${s.change_pct.toFixed(2)}%)
        </div>
        <canvas class="mini-chart" id="mini-${ticker}"></canvas>
        <div class="stock-indicators">
          <span class="indicator-chip">RSI 58.4</span>
          <span class="indicator-chip">Vol ${(s.volume/1000000).toFixed(1)}M</span>
          <span class="indicator-chip" style="color:${isUp ? 'var(--accent-green)' : 'var(--accent-red)'}">
            SMA20 ${ (s.price * 0.99).toFixed(2) }
          </span>
        </div>
      </div>
    `;
  }).join('');
}

function renderMiniCharts() {
  const symbols = ['QQQ', 'VOO', 'TSLA'];
  symbols.forEach(ticker => {
    const canvas = document.getElementById(`mini-${ticker}`);
    const hData = stockData[ticker];
    if (!canvas || !hData) return;
    
    const ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth * 2;
    canvas.height = canvas.offsetHeight * 2;
    ctx.scale(2, 2);

    const w = canvas.offsetWidth, h = canvas.offsetHeight;
    const vals = hData.data.slice(-30).map(d => d.Close);
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
    ctx.moveTo(points[0].x, h);
    points.forEach(p => ctx.lineTo(p.x, p.y));
    ctx.lineTo(points[points.length-1].x, h);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // Line
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    points.forEach(p => ctx.lineTo(p.x, p.y));
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.stroke();
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

  document.getElementById('chart-ticker').textContent = currentStock;
  document.getElementById('chart-name').textContent = currentStock === 'QQQ' ? 'Invesco QQQ ETF' : currentStock === 'VOO' ? 'Vanguard S&P 500' : 'Tesla, Inc.';
  document.getElementById('chart-price').textContent = `$${s.price.toFixed(2)}`;
  
  const isUp = s.change >= 0;
  document.getElementById('chart-change-display').innerHTML =
    `<span class="${isUp ? 'text-green' : 'text-red'}">
      ${isUp ? '▲' : '▼'} ${Math.abs(s.change).toFixed(2)} (${isUp ? '+' : ''}${s.change_pct.toFixed(2)}%)
    </span>`;

  // Stats
  document.getElementById('stat-open').textContent = `$${s.open.toFixed(2)}`;
  document.getElementById('stat-high').textContent = `$${s.high.toFixed(2)}`;
  document.getElementById('stat-low').textContent  = `$${s.low.toFixed(2)}`;
  document.getElementById('stat-vol').textContent  = (s.volume / 1000000).toFixed(2) + 'M';
  document.getElementById('stat-avgvol').textContent = '-';

  // ── Real Moving Averages ──
  const ind = indicatorData[currentStock];
  if (ind && ind.moving_averages) {
    const ma = ind.moving_averages;
    document.getElementById('stat-sma20').textContent =
      ma.sma20_latest != null ? `$${ma.sma20_latest.toFixed(2)}` : '-';
    document.getElementById('stat-sma50').textContent =
      ma.sma50_latest != null ? `$${ma.sma50_latest.toFixed(2)}` : '-';
    document.getElementById('stat-ema20').textContent =
      ma.ema20_latest != null ? `$${ma.ema20_latest.toFixed(2)}` : '-';
    document.getElementById('stat-ema50').textContent =
      ma.ema50_latest != null ? `$${ma.ema50_latest.toFixed(2)}` : '-';
  } else {
    document.getElementById('stat-sma20').textContent = `$${(s.price * 0.99).toFixed(2)}`;
    document.getElementById('stat-sma50').textContent = `$${(s.price * 0.97).toFixed(2)}`;
    document.getElementById('stat-ema20').textContent = '-';
    document.getElementById('stat-ema50').textContent = '-';
  }

  // ── Real Technical Indicators panel ──
  if (ind) {
    // RSI
    const rsi = ind.rsi.latest;
    const rsiEl = document.getElementById('ind-rsi');
    rsiEl.textContent = rsi != null ? rsi.toFixed(1) : '–';
    rsiEl.className = `value ${
      rsi >= 70 ? 'text-red' : rsi <= 30 ? 'text-green' : 'text-blue'
    }`;
    const rsiSignalMap = { overbought: '⚠️ Overbought', oversold: '✅ Oversold', neutral: '► Neutral', unknown: '' };
    document.getElementById('ind-rsi-signal').textContent = rsiSignalMap[ind.rsi.signal] || '';

    // MACD
    const macdVal = ind.macd.macd_latest;
    const macdEl  = document.getElementById('ind-macd');
    macdEl.textContent = macdVal != null ? macdVal.toFixed(3) : '–';
    macdEl.className   = `value ${macdVal >= 0 ? 'text-green' : 'text-red'}`;
    document.getElementById('ind-macd-signal').textContent =
      ind.macd.signal === 'bullish' ? '▲ Bullish Cross' : '▼ Bearish Cross';

    // BB placeholders (still mocked until we add Bollinger Bands)
    document.getElementById('ind-bb-upper').textContent = (s.price * 1.05).toFixed(2);
    document.getElementById('ind-bb-lower').textContent = (s.price * 0.95).toFixed(2);
  } else {
    // Fallback: mock values
    document.getElementById('ind-rsi').textContent  = '58.4';
    document.getElementById('ind-rsi').className    = 'value text-blue';
    document.getElementById('ind-rsi-signal').textContent = '► Neutral';
    document.getElementById('ind-macd').textContent = '3.21';
    document.getElementById('ind-macd').className   = 'value text-green';
    document.getElementById('ind-macd-signal').textContent = '▲ Bullish Cross';
    document.getElementById('ind-bb-upper').textContent = (s.price * 1.05).toFixed(2);
    document.getElementById('ind-bb-lower').textContent = (s.price * 0.95).toFixed(2);
  }

  // AI Score (Mocked)
  const score = currentStock === 'QQQ' ? 74 : currentStock === 'VOO' ? 62 : 32;
  const signal = currentStock === 'QQQ' ? 'BUY' : currentStock === 'VOO' ? 'HOLD' : 'SELL';
  
  document.getElementById('ai-score-val').textContent = score;
  document.getElementById('ai-score-fill').style.width = score + '%';
  document.getElementById('ai-score-fill').style.background =
    score > 65 ? 'var(--accent-green)' : score < 40 ? 'var(--accent-red)' : '#fbbf24';
  document.getElementById('ai-signal-text').textContent = signal;
  document.getElementById('ai-signal-text').className =
    `signal-badge ${signal === 'BUY' ? 'signal-buy' : signal === 'SELL' ? 'signal-sell' : 'signal-hold'}`;

  // Init LightweightCharts
  drawCharts();
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

  const hData = stockData[currentStock];
  if (!hData) return;

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
  if (charts.kline) { try { charts.kline.remove(); } catch(e) {} }
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

  if (charts.volume) { try { charts.volume.remove(); } catch(e) {} }
  const volEl = document.getElementById('volume-chart');
  charts.volume = LWC.createChart(volEl, { ...chartOptions(90), timeScale: { visible: false } });
  const volSeries = charts.volume.addHistogramSeries({ priceFormat: { type: 'volume' } });
  volSeries.setData(volumeData);

  // ── RSI (real data from backend) ──
  if (charts.rsi) { try { charts.rsi.remove(); } catch(e) {} }
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
      time:  Math.floor(new Date(d.timestamp).getTime() / 1000),
      value: d.value
    }));
    rsiSeries.setData(rsiData);
  }
  charts.rsi.priceScale('right').applyOptions({ autoScale: false, minimum: 0, maximum: 100 });

  // ── MACD (real data from backend) ──
  if (charts.macd) { try { charts.macd.remove(); } catch(e) {} }
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
    const macdLineData   = mhist.map(d => ({ time: toTime(d.timestamp), value: d.macd }));
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
} // end drawCharts

// ===== AI Page =====
function renderAIPage() {
  // Signal grid
  const grid = document.getElementById('signal-grid');
  grid.innerHTML = Object.entries(STOCKS).map(([ticker, s]) => {
    const isUp = s.change >= 0;
    const bgColor = { BUY: 'var(--accent-green-dim)', SELL: 'var(--accent-red-dim)', HOLD: 'rgba(251,191,36,0.08)' }[s.signal];
    const textColor = { BUY: 'var(--accent-green)', SELL: 'var(--accent-red)', HOLD: '#fbbf24' }[s.signal];
    return `
      <div class="signal-item" style="background:${bgColor}; border: 1px solid ${textColor}22;">
        <div class="s-ticker">${ticker}</div>
        <div class="s-action" style="color:${textColor}">${s.signal}</div>
        <div class="s-confidence" style="color:${textColor}">AI ${s.aiScore}%</div>
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
window.addEventListener('load', () => {
  updateClock();
  setInterval(updateClock, 1000);
  renderDashboard();
  renderGlobalStats();
  navigate('dashboard');
});

window.addEventListener('resize', () => {
  if (currentPage === 'chart') {
    Object.values(charts).forEach(c => { try { c.timeScale().fitContent(); } catch(e){} });
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
    <div style="display: flex; flex-direction: column; gap: 10px;">
      <div class="skeleton" style="height: 14px; width: 100%;"></div>
      <div class="skeleton" style="height: 14px; width: 90%;"></div>
      <div class="skeleton" style="height: 14px; width: 95%;"></div>
      <div class="skeleton" style="height: 14px; width: 60%;"></div>
    </div>
  `;
  
  try {
    const lang = document.getElementById('ai-lang-select')?.value || 'zh';
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
