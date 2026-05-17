// ===== Static metadata only. Prices always come from backend market data. =====
const TICKER_METADATA = {
  QQQ: { name: 'Invesco QQQ Trust' },
  VOO: { name: 'Vanguard S&P 500 ETF' },
  SPY: { name: 'SPDR S&P 500 ETF' },
  TSLA: { name: 'Tesla, Inc.' },
  NVDA: { name: 'NVIDIA Corp.' },
  AAPL: { name: 'Apple Inc.' },
  MSFT: { name: 'Microsoft Corp.' },
  AMZN: { name: 'Amazon.com, Inc.' },
  META: { name: 'Meta Platforms, Inc.' },
  GOOGL: { name: 'Alphabet Inc.' }
};

const DEMO_NEWS_FALLBACK = [
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
let currentLanguage = localStorage.getItem('brstock_lang') || 'en';
let chainCalibrationStatus = null;
const DEFAULT_WATCHLIST = ['QQQ', 'VOO', 'TSLA', 'NVDA', 'AAPL', 'MSFT', 'AMZN', 'META', 'GOOGL'];
const MARKET_STATS_SYMBOLS = ['^VIX'];

const I18N = {
  en: {
    'brand.subtitle': 'Market Intelligence',
    'nav.main': 'Main',
    'nav.tools': 'Tools',
    'nav.dashboard': 'Dashboard',
    'nav.chart': 'Chart Analysis',
    'nav.ai': 'AI Insights',
    'nav.backtest': 'Backtesting',
    'nav.strategy': 'Strategy',
    'nav.options': 'Options Analysis',
    'nav.synthChain': 'Synth Chain',
    'page.dashboard': '📊 Market Dashboard',
    'page.chart': '📈 Chart Analysis',
    'page.ai': '🤖 AI Insights',
    'page.strategy': '⚙️ My Strategies',
    'page.backtest': '⏪ Backtesting',
    'page.options': '📈 Options Analysis',
    'page.synthChain': '🧪 Synthetic Chain',
    'settings.language': 'Language',
    'auth.login': 'Login',
    'auth.loginTitle': 'Login to BRStock AI',
    'auth.loginSubtitle': 'Access your personal watchlist and AI insights',
    'auth.registerTitle': 'Create an Account',
    'auth.registerSubtitle': 'Join our intelligent market community',
    'auth.resetTitle': 'Reset Password',
    'auth.resetSubtitle': 'Enter your email and Secret PIN to reset',
    'auth.backTo': 'Back to',
    'auth.processing': 'Processing...',
    'auth.requiredFields': 'Please fill in required fields',
    'auth.registerFailed': 'Registration failed',
    'auth.registerSuccess': 'Registration successful! Please login.',
    'auth.resetFailed': 'Reset failed',
    'auth.resetSuccess': 'Password reset successful! Please login with your new password.',
    'auth.invalidLogin': 'Invalid email or password',
    'auth.passwordMismatch': 'Passwords do not match',
    'auth.passwordUpdated': 'Password updated successfully!',
    'auth.updateFailed': 'Update failed',
    'auth.email': 'Email Address',
    'auth.password': 'Password',
    'auth.fullName': 'Full Name',
    'auth.resetPin': 'Secret Reset PIN (6 digits)',
    'auth.newPassword': 'New Password',
    'auth.noAccount': "Don't have an account?",
    'auth.signUp': 'Sign Up',
    'auth.forgotPassword': 'Forgot Password?',
    'auth.changePasswordTitle': 'Change Password',
    'auth.changePasswordSubtitle': 'Ensure your account stays secure',
    'auth.oldPassword': 'Old Password',
    'auth.confirmNewPassword': 'Confirm New Password',
    'auth.updatePassword': 'Update Password',
    'auth.recoveryPlaceholder': 'Used for recovery',
    'auth.logout': 'Logout',
    'auth.loggedInAs': 'Logged in as:',
    'auth.changePassword': 'Change Password',
    'status.dataLive': 'Data Live',
    'common.error': 'Error',
    'search.placeholder': 'Search ticker...',
    'actions.addStock': 'Add Stock',
    'actions.runBacktest': 'Run Backtest Simulation',
    'actions.generateChain': 'Generate Chain',
    'actions.generating': 'Generating...',
    'backtest.settings': 'Backtest Settings',
    'backtest.selectStrategy': 'Select Strategy',
    'backtest.noStrategy': '-- No strategy selected --',
    'backtest.verticalParams': 'Vertical Spread Parameters',
    'backtest.leapsParams': 'LEAPS Parameters',
    'backtest.portfolioParams': 'Portfolio Sleeves',
    'backtest.coreSleeve': 'Core ETF Sleeve',
    'backtest.optionsSleeve': 'Options Sleeve',
    'backtest.resultsSummary': 'Results Summary',
    'backtest.tradeLog': 'Trade Log',
    'backtest.totalReturn': 'Total Return',
    'backtest.winRate': 'Win Rate',
    'backtest.finalValue': 'Final Value',
    'backtest.totalTrades': 'Total Trades',
    'backtest.cashBalance': 'Cash Balance',
    'backtest.riskAtWork': 'Risk at Work',
    'backtest.availableCash': 'Available Cash',
    'backtest.position': 'Position',
    'backtest.event': 'Event',
    'backtest.underlying': 'Underlying',
    'backtest.legs': 'Legs',
    'backtest.cashFlow': 'Cash Flow',
    'backtest.entryCost': 'Entry Cost',
    'backtest.settlement': 'Settlement',
    'backtest.openDate': 'Open Date',
    'backtest.closeDate': 'Close Date',
    'backtest.netPl': 'Net P/L',
    'backtest.riskBalance': 'Risk / Balance',
    'backtest.price': 'Price',
    'backtest.shares': 'Shares',
    'backtest.details': 'Details',
    'fields.stockTicker': 'Stock Ticker',
    'fields.initialCapital': 'Initial Capital ($)',
    'fields.timeframe': 'Timeframe',
    'fields.startDate': 'Start Date',
    'fields.endDate': 'End Date',
    'fields.dteTarget': 'DTE Target',
    'fields.spreadWidth': 'Spread Width ($)',
    'fields.capitalUtilization': 'Capital Utilization (%)',
    'fields.longDelta': 'Long Delta Target',
    'fields.shortDelta': 'Short Delta Target',
    'fields.maxOpenPositions': 'Max Open Positions',
    'fields.deltaTolerance': 'Delta Tolerance',
    'fields.fillSlippage': 'Fill Slippage',
    'fields.openInterval': 'Open Interval (days)',
    'fields.rollDte': 'Roll When DTE Below',
    'fields.sleeveAllocation': 'Allocation (%)',
    'fields.rebalance': 'Portfolio Rebalance',
    'fields.weight': 'Weight (%)',
    'fields.optionTicker': 'Option Ticker',
    'placeholder.sameAsStockTicker': 'same as stock ticker',
    'fields.optionStrategy': 'Option Strategy',
    'fields.bullRsiMin': 'Bull Entry RSI Min',
    'fields.bearRsiMax': 'Bear Entry RSI Max',
    'fields.ticker': 'Ticker',
    'fields.date': 'Date',
    'fields.dteList': 'DTE List',
    'fields.spot': 'Spot',
    'fields.actualDate': 'Actual Date',
    'fields.rsi': 'RSI',
    'fields.hv20d': 'HV 20D',
    'fields.type': 'Type',
    'fields.strike': 'Strike',
    'fields.delta': 'Delta',
    'fields.bid': 'Bid',
    'fields.ask': 'Ask',
    'fields.mid': 'Mid',
    'fields.premium': 'Premium',
    'timeframe.1y': 'Past 1 Year',
    'timeframe.2y': 'Past 2 Years',
    'timeframe.5y': 'Past 5 Years',
    'timeframe.custom': 'Custom Range',
    'help.bullCallDefaults': 'Bull Call default: buy ~0.60 delta call, sell higher strike by width. Capital utilization caps total open max debit/risk across all active spreads. Fill slippage is 0 for mid, 0.50 for natural ask/bid.',
    'help.leapsDefaults': 'LEAPS default: buy long-term calls near 0.80 delta, allocate a chosen percent of equity, and roll when remaining DTE drops below the roll threshold.',
    'help.portfolioSleeves': 'Options capital utilization is measured inside the options sleeve by default.',
    'portfolio.rebalanceNone': 'None',
    'portfolio.rebalanceMonthly': 'Monthly',
    'portfolio.rebalanceQuarterly': 'Quarterly',
    'portfolio.rebalanceAnnual': 'Annual',
    'synth.title': 'Synthetic Option Chain Inspector',
    'synth.emptyStatus': 'Choose a date and generate the synthetic chain.',
    'synth.generatedChain': 'Generated Chain',
    'synth.noChain': 'No chain generated yet.',
    'synth.noMatch': 'No rows match the current filters.',
    'synth.pickDate': 'Pick a date first.',
    'synth.generatingFor': 'Generating {ticker} synthetic chain for {date}...',
    'synth.generatedStatus': '{ticker} {date}: {count} contracts generated from synthetic IV, bid/ask, and Greeks.',
    'synth.failed': 'Failed to generate synthetic chain.',
    'filters.all': 'All',
    'filters.calls': 'Calls',
    'filters.puts': 'Puts',
    'filters.allDte': 'All DTE',
    'options.title': 'Options Analysis',
    'options.subtitle': 'Explore chains, scan candidates, and validate strategy ideas.',
    'options.expiration': 'Expiration',
    'options.contract': 'Contract',
    'options.allExpirations': 'All expirations',
    'options.callsPuts': 'Calls & Puts',
    'options.allDeltas': 'All deltas',
    'options.nearAtm': 'Near ATM',
    'options.wheelPuts': 'Wheel puts',
    'options.coveredCalls': 'Covered calls',
    'options.leapsCalls': 'LEAPS calls',
    'options.refresh': 'Refresh',
    'options.chain': 'Chain',
    'options.candidates': 'Candidates',
    'options.builder': 'Strategy Builder',
    'options.backtest': 'Backtest',
    'options.authRequired': 'Authorization Required',
    'options.authHelp': 'Refresh your market data token from the backend when authorization expires.',
    'options.oauthPlaceholder': 'OAuth code or redirect URL',
    'options.saveToken': 'Save Token',
    'options.savingToken': 'Saving Schwab token...',
    'options.tokenSaveFailed': 'Failed to save Schwab token',
    'options.networkError': 'Network error',
    'options.getAuthUrl': 'Get Auth URL',
    'options.authRequestFailed': 'Failed to request code',
    'options.underlying': 'Underlying',
    'options.contracts': 'Contracts',
    'options.atmStrike': 'ATM Strike',
    'options.spreadHealth': 'Spread Health',
    'options.optionChain': 'Option Chain',
    'options.loadChain': 'Load a chain to begin.',
    'options.chooseTicker': 'Choose a ticker and refresh the chain.',
    'options.noContracts': 'No contracts match the current filters.',
    'options.strategyBuilderEmpty': 'Click contracts in the chain to start building a strategy.',
    'options.creditSpreadShorts': 'Credit Spread Shorts',
    'options.optionBacktest': 'Option Strategy Backtest',
    'options.strategyType': 'Strategy Type',
    'options.runOptionBacktest': 'Run Option Backtest',
    'options.backtestResults': 'Backtest Results',
    'options.ready': 'Ready',
    'options.checkingStatus': 'Checking market data status...',
    'options.authorizationNeeded': 'Authorization needed',
    'options.checkingChain': 'Checking chain directly...',
    'options.statusError': 'Status Error',
    'options.refreshing': 'Refreshing {ticker}...',
    'options.usingCached': 'Using cached {ticker} chain...',
    'options.updated': '{ticker} updated {time} · cache {cacheAge}s',
    'options.fetchFailed': 'Failed to fetch real-time data from Schwab.',
    'options.authRequiredStatus': 'Schwab authorization required.',
    'options.authExpired': 'Authorization expired.',
    'options.refreshFailed': 'Option chain refresh failed.',
    'options.filteredMeta': '{ticker} · {visible} ATM-centered rows · {total} filtered contracts · {time}',
    'options.noCandidates': 'No candidates match the current chain.',
    'options.wheelCandidate': 'Cash-secured put candidate',
    'options.coveredCallCandidate': 'Covered call candidate',
    'options.leapsCandidate': 'Long-dated directional candidate',
    'options.shortLegCandidate': 'Potential short leg',
    'options.legs': 'Legs {count}',
    'options.netDebit': 'Net Debit',
    'options.netCredit': 'Net Credit',
    'options.clear': 'Clear',
    'options.remove': 'Remove',
    'options.tokenSaved': 'Schwab token saved.',
    'options.loadingAuthUrl': 'Loading Schwab authorization URL...',
    'options.openAuthUrl': 'Open this URL, authorize, then paste the redirect URL above:',
    'options.authUrlLabel': 'Schwab authorization URL',
    'options.healthGood': 'Good',
    'options.healthWatch': 'Watch',
    'options.healthWide': 'Wide'
  },
  zh: {
    'brand.subtitle': '市场智能',
    'nav.main': '主要',
    'nav.tools': '工具',
    'nav.dashboard': '仪表盘',
    'nav.chart': '图表分析',
    'nav.ai': 'AI 洞察',
    'nav.backtest': '回测',
    'nav.strategy': '策略',
    'nav.options': '期权分析',
    'nav.synthChain': '合成期权链',
    'page.dashboard': '📊 市场仪表盘',
    'page.chart': '📈 图表分析',
    'page.ai': '🤖 AI 洞察',
    'page.strategy': '⚙️ 我的策略',
    'page.backtest': '⏪ 回测',
    'page.options': '📈 期权分析',
    'page.synthChain': '🧪 合成期权链',
    'settings.language': '语言',
    'auth.login': '登录',
    'auth.loginTitle': '登录 BRStock AI',
    'auth.loginSubtitle': '访问你的自选列表和 AI 洞察',
    'auth.registerTitle': '创建账户',
    'auth.registerSubtitle': '加入智能市场社区',
    'auth.resetTitle': '重置密码',
    'auth.resetSubtitle': '输入邮箱和 Secret PIN 来重置密码',
    'auth.backTo': '返回',
    'auth.processing': '处理中...',
    'auth.requiredFields': '请填写必填项',
    'auth.registerFailed': '注册失败',
    'auth.registerSuccess': '注册成功，请登录。',
    'auth.resetFailed': '重置失败',
    'auth.resetSuccess': '密码重置成功，请用新密码登录。',
    'auth.invalidLogin': '邮箱或密码无效',
    'auth.passwordMismatch': '两次输入的密码不一致',
    'auth.passwordUpdated': '密码更新成功！',
    'auth.updateFailed': '更新失败',
    'auth.email': '邮箱地址',
    'auth.password': '密码',
    'auth.fullName': '姓名',
    'auth.resetPin': '重置 PIN（6 位）',
    'auth.newPassword': '新密码',
    'auth.noAccount': '还没有账户？',
    'auth.signUp': '注册',
    'auth.forgotPassword': '忘记密码？',
    'auth.changePasswordTitle': '修改密码',
    'auth.changePasswordSubtitle': '保持账户安全',
    'auth.oldPassword': '旧密码',
    'auth.confirmNewPassword': '确认新密码',
    'auth.updatePassword': '更新密码',
    'auth.recoveryPlaceholder': '用于找回账户',
    'auth.logout': '退出',
    'auth.loggedInAs': '当前用户：',
    'auth.changePassword': '修改密码',
    'status.dataLive': '数据在线',
    'common.error': '错误',
    'search.placeholder': '搜索股票代码...',
    'actions.addStock': '添加股票',
    'actions.runBacktest': '运行回测',
    'actions.generateChain': '生成期权链',
    'actions.generating': '生成中...',
    'backtest.settings': '回测设置',
    'backtest.selectStrategy': '选择策略',
    'backtest.noStrategy': '-- 未选择策略 --',
    'backtest.verticalParams': '垂直价差参数',
    'backtest.leapsParams': 'LEAPS 参数',
    'backtest.portfolioParams': '组合仓位',
    'backtest.coreSleeve': '核心 ETF 仓位',
    'backtest.optionsSleeve': '期权仓位',
    'backtest.resultsSummary': '结果摘要',
    'backtest.tradeLog': '交易记录',
    'backtest.totalReturn': '总回报',
    'backtest.winRate': '胜率',
    'backtest.finalValue': '最终资产',
    'backtest.totalTrades': '交易次数',
    'backtest.cashBalance': '现金余额',
    'backtest.riskAtWork': '风险占用',
    'backtest.availableCash': '可用现金',
    'backtest.position': '仓位',
    'backtest.event': '事件',
    'backtest.underlying': '标的价格',
    'backtest.legs': '期权腿',
    'backtest.cashFlow': '现金流',
    'backtest.entryCost': '开仓成本',
    'backtest.settlement': '结算收入',
    'backtest.openDate': '开仓日',
    'backtest.closeDate': '平仓日',
    'backtest.netPl': '净盈亏',
    'backtest.riskBalance': '风险 / 余额',
    'backtest.price': '价格',
    'backtest.shares': '股数',
    'backtest.details': '详情',
    'fields.stockTicker': '股票代码',
    'fields.initialCapital': '初始资金 ($)',
    'fields.timeframe': '时间范围',
    'fields.startDate': '开始日期',
    'fields.endDate': '结束日期',
    'fields.dteTarget': '目标 DTE',
    'fields.spreadWidth': '价差宽度 ($)',
    'fields.capitalUtilization': '资金利用率 (%)',
    'fields.longDelta': '买入腿 Delta 目标',
    'fields.shortDelta': '卖出腿 Delta 目标',
    'fields.maxOpenPositions': '最大持仓数',
    'fields.deltaTolerance': 'Delta 容忍度',
    'fields.fillSlippage': '成交滑点',
    'fields.openInterval': '开仓间隔 (天)',
    'fields.rollDte': '剩余 DTE 低于此值时滚动',
    'fields.sleeveAllocation': '仓位比例 (%)',
    'fields.rebalance': '组合再平衡',
    'fields.weight': '权重 (%)',
    'fields.optionTicker': '期权标的',
    'placeholder.sameAsStockTicker': '默认同股票代码',
    'fields.optionStrategy': '期权策略',
    'fields.bullRsiMin': '做多入场 RSI 下限',
    'fields.bearRsiMax': '做空入场 RSI 上限',
    'fields.ticker': '代码',
    'fields.date': '日期',
    'fields.dteList': 'DTE 列表',
    'fields.spot': '现价',
    'fields.actualDate': '实际日期',
    'fields.rsi': 'RSI',
    'fields.hv20d': '20日历史波动率',
    'fields.type': '类型',
    'fields.strike': '行权价',
    'fields.delta': 'Delta',
    'fields.bid': '买价',
    'fields.ask': '卖价',
    'fields.mid': '中间价',
    'fields.premium': '理论价',
    'timeframe.1y': '过去 1 年',
    'timeframe.2y': '过去 2 年',
    'timeframe.5y': '过去 5 年',
    'timeframe.custom': '自定义区间',
    'help.bullCallDefaults': 'Bull Call 默认：买入约 0.60 delta 的 call，并按宽度卖出更高行权价。资金利用率限制所有未平仓价差的合计最大 debit/风险。成交滑点 0 表示按 mid，0.50 表示按自然 ask/bid。',
    'help.leapsDefaults': 'LEAPS 默认：买入接近 0.80 delta 的长期 call，按指定资金比例参与，并在剩余 DTE 低于阈值时滚动。',
    'help.portfolioSleeves': '默认情况下，期权资金利用率按期权仓位内部计算。',
    'portfolio.rebalanceNone': '不再平衡',
    'portfolio.rebalanceMonthly': '月度',
    'portfolio.rebalanceQuarterly': '季度',
    'portfolio.rebalanceAnnual': '年度',
    'synth.title': '合成期权链检查器',
    'synth.emptyStatus': '选择日期并生成合成期权链。',
    'synth.generatedChain': '生成的期权链',
    'synth.noChain': '尚未生成期权链。',
    'synth.noMatch': '当前筛选条件下没有记录。',
    'synth.pickDate': '请先选择日期。',
    'synth.generatingFor': '正在生成 {ticker} 在 {date} 的合成期权链...',
    'synth.generatedStatus': '{ticker} {date}: 已生成 {count} 条合约，包含合成 IV、bid/ask 和 Greeks。',
    'synth.failed': '生成合成期权链失败。',
    'filters.all': '全部',
    'filters.calls': '看涨',
    'filters.puts': '看跌',
    'filters.allDte': '全部 DTE',
    'options.title': '期权分析',
    'options.subtitle': '查看期权链，筛选候选合约，并验证策略想法。',
    'options.expiration': '到期日',
    'options.contract': '合约',
    'options.allExpirations': '全部到期日',
    'options.callsPuts': '看涨和看跌',
    'options.allDeltas': '全部 Delta',
    'options.nearAtm': '接近 ATM',
    'options.wheelPuts': 'Wheel 看跌',
    'options.coveredCalls': '备兑看涨',
    'options.leapsCalls': 'LEAPS 看涨',
    'options.refresh': '刷新',
    'options.chain': '期权链',
    'options.candidates': '候选合约',
    'options.builder': '策略构建',
    'options.backtest': '回测',
    'options.authRequired': '需要授权',
    'options.authHelp': '行情授权过期时，请从后端刷新市场数据 token。',
    'options.oauthPlaceholder': 'OAuth code 或跳转 URL',
    'options.saveToken': '保存 Token',
    'options.savingToken': '正在保存 Schwab token...',
    'options.tokenSaveFailed': '保存 Schwab token 失败',
    'options.networkError': '网络错误',
    'options.getAuthUrl': '获取授权链接',
    'options.authRequestFailed': '请求授权码失败',
    'options.underlying': '标的价格',
    'options.contracts': '合约数',
    'options.atmStrike': 'ATM 行权价',
    'options.spreadHealth': '价差质量',
    'options.optionChain': '期权链',
    'options.loadChain': '加载期权链后开始。',
    'options.chooseTicker': '选择股票代码并刷新期权链。',
    'options.noContracts': '当前筛选条件下没有合约。',
    'options.strategyBuilderEmpty': '点击期权链中的合约开始构建策略。',
    'options.creditSpreadShorts': '信用价差卖出腿',
    'options.optionBacktest': '期权策略回测',
    'options.strategyType': '策略类型',
    'options.runOptionBacktest': '运行期权回测',
    'options.backtestResults': '回测结果',
    'options.ready': '就绪',
    'options.checkingStatus': '正在检查市场数据状态...',
    'options.authorizationNeeded': '需要授权',
    'options.checkingChain': '正在直接检查期权链...',
    'options.statusError': '状态错误',
    'options.refreshing': '正在刷新 {ticker}...',
    'options.usingCached': '正在使用缓存的 {ticker} 期权链...',
    'options.updated': '{ticker} 已更新 {time} · 缓存 {cacheAge}s',
    'options.fetchFailed': '获取 Schwab 实时期权数据失败。',
    'options.authRequiredStatus': '需要 Schwab 授权。',
    'options.authExpired': '授权已过期。',
    'options.refreshFailed': '期权链刷新失败。',
    'options.filteredMeta': '{ticker} · {visible} 行 ATM 居中 · {total} 条筛选合约 · {time}',
    'options.noCandidates': '当前期权链下没有匹配候选合约。',
    'options.wheelCandidate': '现金担保看跌候选',
    'options.coveredCallCandidate': '备兑看涨候选',
    'options.leapsCandidate': '长期方向性候选',
    'options.shortLegCandidate': '潜在卖出腿',
    'options.legs': '{count} 条腿',
    'options.netDebit': '净支出',
    'options.netCredit': '净收入',
    'options.clear': '清空',
    'options.remove': '移除',
    'options.tokenSaved': 'Schwab token 已保存。',
    'options.loadingAuthUrl': '正在加载 Schwab 授权链接...',
    'options.openAuthUrl': '打开此链接完成授权，然后把跳转 URL 粘贴到上方：',
    'options.authUrlLabel': 'Schwab 授权链接',
    'options.healthGood': '良好',
    'options.healthWatch': '关注',
    'options.healthWide': '偏宽'
  }
};

function t(key, vars = {}) {
  let text = I18N[currentLanguage]?.[key] || I18N.en[key] || key;
  Object.entries(vars).forEach(([name, value]) => {
    text = text.replaceAll(`{${name}}`, value);
  });
  return text;
}

function applyI18n() {
  document.documentElement.lang = currentLanguage === 'zh' ? 'zh-CN' : 'en';
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  const languageSelect = document.getElementById('language-select');
  if (languageSelect) languageSelect.value = currentLanguage;
  const titleEl = document.getElementById('page-title');
  if (titleEl) titleEl.textContent = pageTitle(currentPage);
}

function setLanguage(lang) {
  currentLanguage = lang === 'zh' ? 'zh' : 'en';
  localStorage.setItem('brstock_lang', currentLanguage);
  applyI18n();
  updateAuthUI();
  if (currentPage === 'options') {
    updateOptionsSummary({
      underlying_price: optionsChainState.underlying,
      options: optionsChainState.options,
    });
    updateOptionsExpirationFilter();
    applyI18n();
    renderOptionsChainTable();
    renderOptionsCandidates();
    renderOptionsBuilder();
  }
}

function pageTitle(page) {
  const keyMap = {
    dashboard: 'page.dashboard',
    chart: 'page.chart',
    ai: 'page.ai',
    strategy: 'page.strategy',
    backtest: 'page.backtest',
    options: 'page.options',
    'synth-chain': 'page.synthChain'
  };
  return t(keyMap[page] || 'brand.subtitle');
}

async function initWatchlist() {
  // Only fetch user watchlist if logged in. Without a token the backend returns
  // 401 which triggers performLogout → navigate('dashboard') → initWatchlist loop.
  if (!authToken) {
    watchlist = DEFAULT_WATCHLIST;
    return;
  }
  const data = await apiFetch('/api/watchlist');
  watchlist = Array.isArray(data) ? data : DEFAULT_WATCHLIST;
}

// ===== API Fetching =====
async function apiFetch(endpoint, options = {}) {
  apiFetch.lastError = null;
  const headers = { ...options.headers };
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  if (options.body && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  try {
    const response = await fetch(endpoint, { ...options, headers });

    if (response.status === 401) {
      console.warn('[AUTH] 401 from API, clearing token and showing login gate.', { endpoint });
      performLogout(`401 from ${endpoint}`);
      return null;
    }

    if (!response.ok) {
      let message = response.statusText || `HTTP ${response.status}`;
      try {
        const errorPayload = await response.json();
        message = errorPayload.detail || errorPayload.error || message;
      } catch (_) {
        try {
          const errorText = await response.text();
          if (errorText) message = errorText;
        } catch (_) {}
      }
      const apiError = new Error(`API Error: ${message}`);
      apiError.status = response.status;
      apiError.endpoint = endpoint;
      throw apiError;
    }
    return await response.json();
  } catch (err) {
    apiFetch.lastError = err;
    const status = err?.status ? `HTTP ${err.status}` : (err?.name || 'NetworkError');
    console.error(`Failed to fetch ${endpoint}: ${status}`);
    return null;
  }
}

function performLogout(reason = 'manual/session reset') {
  console.warn('[AUTH] performLogout', { reason, currentPage });
  localStorage.removeItem('brstock_token');
  authToken = null;
  updateAuthUI();
  navigate('dashboard'); // 如果未授权，跳回首页是合理的，但我们要确保它是受控的
}


async function refreshAllData() {
  const symbols = [...new Set([...watchlist, ...MARKET_STATS_SYMBOLS])];
  const promises = symbols.map(s => refreshSymbolData(s));
  await Promise.all(promises);
}

async function refreshSymbolData(symbol) {
  const s = symbol.toUpperCase();
  const [history, summary] = await Promise.all([
    apiFetch(`/api/stocks/${s}/history?interval=1d`), // Dashboard usually wants daily
    apiFetch(`/api/stocks/${s}/summary`)
  ]);
  if (history) {
    if (!stockData[s]) stockData[s] = {};
    stockData[s]['1d'] = history;
  }
  if (summary) stockStats[s] = summary;
  return { history, summary };
}

// ===== Page Navigation =====
let isNavigating = false;

async function navigate(page) {
  console.log('>>> Navigating to:', page);
  if (isNavigating) return;
  isNavigating = true;

  try {
    const pageEl = document.getElementById(`page-${page}`);
    if (!pageEl) {
      throw new Error(`Page element #page-${page} NOT FOUND in DOM!`);
    }
    currentPage = page;

    // UI Update
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    pageEl.classList.add('active');
    const navItem = document.querySelector(`[data-page="${page}"]`);
    if (navItem) navItem.classList.add('active');

    const titleEl = document.getElementById('page-title');
    if (titleEl) titleEl.textContent = pageTitle(page);

    // Page Specific Logic
    if (page === 'dashboard') {
      await refreshAllData();
      renderDashboard();
    } else if (page === 'chart') {
      await refreshStockData(currentStock, currentInterval);
      if (typeof initChartPage === 'function') initChartPage();
    } else if (page === 'ai') {
      if (typeof renderAIPage === 'function') renderAIPage();
    } else if (page === 'strategy') {
      await loadStrategies();
    } else if (page === 'backtest') {
      await loadBacktestPage();
    } else if (page === 'options') {
      applyI18n();
      renderOptionsPage();
    } else if (page === 'synth-chain') {
      initSyntheticChainPage();
    }

  } catch (err) {
    console.error('Navigation Error:', err);
    // If it's a critical error on first load, we don't want a black screen
    const content = document.querySelector('.content');
    if (content && content.innerHTML === '') {
      content.innerHTML = `<div class="panel-card" style="margin:20px; color:var(--accent-red)">Error loading page: ${err.message}</div>`;
    }
  } finally {
    setTimeout(() => { isNavigating = false; }, 300);
  }
}


let syntheticChainRows = [];
let syntheticChainSpot = null;

function initSyntheticChainPage() {
  const dateEl = document.getElementById('synth-chain-date');
  if (dateEl && !dateEl.value) {
    dateEl.value = new Date().toISOString().slice(0, 10);
  }
  loadChainCalibrationStatus();
}

async function loadSyntheticChainByDate() {
  const ticker = (document.getElementById('synth-chain-ticker')?.value || 'QQQ').trim().toUpperCase();
  const date = document.getElementById('synth-chain-date')?.value;
  const dtes = (document.getElementById('synth-chain-dtes')?.value || '30,40,45,90,180,365').trim();
  const statusEl = document.getElementById('synth-chain-status');
  const bodyEl = document.getElementById('synth-chain-body');

  if (!date) {
    if (statusEl) statusEl.textContent = t('synth.pickDate');
    return;
  }

  if (statusEl) statusEl.textContent = t('synth.generatingFor', { ticker, date });
  if (bodyEl) bodyEl.innerHTML = `<tr><td colspan="13" style="padding:24px; text-align:center; color:var(--text-muted);">${t('actions.generating')}</td></tr>`;

  const data = await apiFetch(`/api/options/synth/chain-by-date/${encodeURIComponent(ticker)}?date=${encodeURIComponent(date)}&dtes=${encodeURIComponent(dtes)}`);
  if (!data || !data.options) {
    const message = apiFetch.lastError?.message || t('synth.failed');
    if (statusEl) statusEl.textContent = message;
    if (bodyEl) bodyEl.innerHTML = `<tr><td colspan="13" style="padding:24px; text-align:center; color:var(--accent-red);">${message}</td></tr>`;
    syntheticChainRows = [];
    return;
  }

  syntheticChainRows = data.options || [];
  syntheticChainSpot = Number(data.spot_price || 0);
  const formatMoney = (v) => `$${Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  document.getElementById('synth-chain-spot').textContent = formatMoney(data.spot_price);
  document.getElementById('synth-chain-actual-date').textContent = data.actual_date || data.requested_date || '-';
  document.getElementById('synth-chain-rsi').textContent = data.rsi ?? '-';
  document.getElementById('synth-chain-hv').textContent = `${((data.hv_20 || 0) * 100).toFixed(2)}%`;
  if (data.calibration?.version) {
    const applied = Number(data.calibration.applied_count || 0);
    if (statusEl) statusEl.textContent = `Generated ${syntheticChainRows.length} contracts. Calibration v${data.calibration.version} applied to ${applied} contracts.`;
  }

  const dteFilter = document.getElementById('synth-chain-dte-filter');
  if (dteFilter) {
    const dteValues = [...new Set(syntheticChainRows.map(o => o.expiry_dte))].sort((a, b) => a - b);
    dteFilter.innerHTML = `<option value="ALL">${t('filters.allDte')}</option>` + dteValues.map(d => `<option value="${d}">${d} DTE</option>`).join('');
  }

  if (statusEl) {
    const baseStatus = t('synth.generatedStatus', { ticker: data.ticker, date: data.actual_date, count: syntheticChainRows.length });
    const calibrationStatus = data.calibration?.version
      ? ` Calibration v${data.calibration.version}, applied ${Number(data.calibration.applied_count || 0)}.`
      : '';
    statusEl.textContent = `${baseStatus}${calibrationStatus}`;
  }
  renderSyntheticChainTable();
}

async function loadChainCalibrationStatus() {
  const pill = document.getElementById('calibration-version-pill');
  const statusEl = document.getElementById('calibration-status');
  const buttonEl = document.getElementById('calibration-run-button');
  if (!pill && !statusEl && !buttonEl) return;
  const status = await apiFetch('/api/options/calibration/status');
  chainCalibrationStatus = status || null;
  if (!status) {
    if (pill) pill.textContent = 'Calibration unavailable';
    if (statusEl) statusEl.textContent = 'Saved calibration status is currently unavailable.';
    if (buttonEl) {
      buttonEl.disabled = true;
      buttonEl.textContent = 'Local calibration only';
    }
    return;
  }
  const sourceLabel = status.source_kind === 'bundled' ? 'bundled' : status.source_kind === 'runtime' ? 'runtime' : 'none';
  if (pill) pill.textContent = `Version ${status.version || 0} · ${status.bucket_count || 0} buckets · ${sourceLabel}`;
  if (buttonEl) {
    buttonEl.disabled = !status.can_run_live_calibration;
    buttonEl.textContent = status.can_run_live_calibration ? 'Calibrate from Schwab' : 'Local calibration only';
    buttonEl.title = status.can_run_live_calibration ? 'Fetch live Schwab option quotes and update local calibration buckets.' : (status.message || 'Schwab calibration requires local authenticated mode.');
  }
  if (statusEl) {
    const saved = status.bucket_count
      ? `Saved calibration v${status.version || 0} is active from ${sourceLabel} parameters.`
      : 'No saved calibration parameters are active yet.';
    const live = status.can_run_live_calibration
      ? 'Live Schwab calibration is available in this local authenticated session.'
      : (status.message || 'Schwab calibration is available only in local authenticated mode.');
    statusEl.textContent = `${saved} ${live}`;
  }
}

async function runChainCalibration() {
  const ticker = (document.getElementById('calibration-ticker')?.value || document.getElementById('synth-chain-ticker')?.value || 'QQQ').trim().toUpperCase();
  const numberValue = (id, fallback) => {
    const value = parseFloat(document.getElementById(id)?.value);
    return Number.isFinite(value) ? value : fallback;
  };
  const payload = {
    ticker,
    strike_count: numberValue('calibration-strike-count', 60),
    dte_min: numberValue('calibration-dte-min', 5),
    dte_max: numberValue('calibration-dte-max', 75),
    max_spread_pct: numberValue('calibration-max-spread', 35) / 100,
    save: true
  };
  const statusEl = document.getElementById('calibration-status');
  const bodyEl = document.getElementById('calibration-sample-body');
  if (chainCalibrationStatus && !chainCalibrationStatus.can_run_live_calibration) {
    const message = chainCalibrationStatus.message || 'Schwab calibration is available only in local authenticated mode. Remote demo uses saved calibration parameters.';
    if (statusEl) statusEl.textContent = message;
    if (bodyEl) bodyEl.innerHTML = `<tr><td colspan="8" style="padding:20px; text-align:center; color:var(--text-muted);">${message}</td></tr>`;
    return;
  }
  if (statusEl) statusEl.textContent = `Fetching Schwab ${ticker} chain and comparing against synthetic chain...`;
  if (bodyEl) bodyEl.innerHTML = '<tr><td colspan="8" style="padding:20px; text-align:center; color:var(--text-muted);">Running calibration...</td></tr>';

  const result = await apiFetch('/api/options/calibration/run', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
  if (!result) {
    const message = (apiFetch.lastError?.message || 'Schwab calibration is available only in local authenticated mode. Remote demo uses saved calibration parameters.')
      .replace(/^API Error:\s*/i, '');
    if (statusEl) statusEl.textContent = message;
    if (bodyEl) bodyEl.innerHTML = `<tr><td colspan="8" style="padding:20px; text-align:center; color:var(--text-muted);">${message}</td></tr>`;
    return;
  }

  const pct = (value) => Number.isFinite(Number(value)) ? `${Number(value).toFixed(2)}%` : '-';
  document.getElementById('calibration-matched').textContent = result.matched_contracts ?? '-';
  document.getElementById('calibration-before-median').textContent = pct(result.before?.median_abs_error_pct);
  document.getElementById('calibration-after-median').textContent = pct(result.after?.median_abs_error_pct);
  document.getElementById('calibration-before-p90').textContent = pct(result.before?.p90_abs_error_pct);
  document.getElementById('calibration-after-p90').textContent = pct(result.after?.p90_abs_error_pct);

  if (statusEl) {
    statusEl.textContent = `Saved calibration v${result.calibration_version}. ${result.updated_bucket_count} buckets updated from ${result.matched_contracts} matched contracts.`;
  }
  await loadChainCalibrationStatus();

  const rows = result.sample_rows || [];
  if (!rows.length) {
    if (bodyEl) bodyEl.innerHTML = '<tr><td colspan="8" style="padding:20px; text-align:center; color:var(--text-muted);">No matched sample rows returned.</td></tr>';
    return;
  }
  if (bodyEl) {
    bodyEl.innerHTML = rows.slice(0, 30).map(row => {
      const before = Number(row.error_pct || 0) * 100;
      const after = Number(row.adjusted_error_pct || 0) * 100;
      const afterColor = Math.abs(after) <= Math.abs(before) ? 'var(--accent-green)' : 'var(--accent-red)';
      return `
        <tr style="border-bottom:1px solid rgba(255,255,255,0.045); text-align:right;">
          <td style="padding:9px; text-align:left; color:var(--text-muted);">${row.contract || `${row.symbol} ${row.type}`}</td>
          <td style="padding:9px;">${row.expiry_dte}</td>
          <td style="padding:9px;">${Number(row.strike).toFixed(2)}</td>
          <td style="padding:9px;">${Number(row.real_mid).toFixed(2)}</td>
          <td style="padding:9px;">${Number(row.synth_mid).toFixed(2)}</td>
          <td style="padding:9px;">${before.toFixed(2)}%</td>
          <td style="padding:9px; color:${afterColor}; font-weight:700;">${after.toFixed(2)}%</td>
          <td style="padding:9px; font-size:10px; color:var(--text-muted);">${row.bucket_key || '-'}</td>
        </tr>
      `;
    }).join('');
  }
}

function renderSyntheticChainTable() {
  const bodyEl = document.getElementById('synth-chain-body');
  if (!bodyEl) return;

  const typeFilter = document.getElementById('synth-chain-type-filter')?.value || 'ALL';
  const dteFilter = document.getElementById('synth-chain-dte-filter')?.value || 'ALL';
  const sortMode = document.getElementById('synth-chain-sort')?.value || 'ATM';
  const rows = syntheticChainRows
    .filter(o => typeFilter === 'ALL' || o.type === typeFilter)
    .filter(o => dteFilter === 'ALL' || String(o.expiry_dte) === String(dteFilter))
    .sort((a, b) => {
      const dteSort = a.expiry_dte - b.expiry_dte;
      if (dteSort) return dteSort;

      if (sortMode === 'STRIKE_ASC') {
        return (a.strike - b.strike) || a.type.localeCompare(b.type);
      }

      if (sortMode === 'DELTA') {
        const targetDelta = a.type === 'CALL' ? 0.5 : -0.5;
        const aDeltaDistance = Math.abs(Number(a.delta) - targetDelta);
        const bDeltaDistance = Math.abs(Number(b.delta) - targetDelta);
        return aDeltaDistance - bDeltaDistance || (a.strike - b.strike) || a.type.localeCompare(b.type);
      }

      const spot = syntheticChainSpot || Number(a.spot_price || b.spot_price || 0);
      const aAtmDistance = Math.abs(Number(a.strike) - spot);
      const bAtmDistance = Math.abs(Number(b.strike) - spot);
      return aAtmDistance - bAtmDistance || (a.strike - b.strike) || a.type.localeCompare(b.type);
    });

  if (!rows.length) {
    bodyEl.innerHTML = `<tr><td colspan="13" style="padding:24px; text-align:center; color:var(--text-muted);">${t('synth.noMatch')}</td></tr>`;
    return;
  }

  const spot = syntheticChainSpot || Number(rows[0]?.spot_price || 0);
  const atmStrikeByDte = rows.reduce((acc, row) => {
    const dte = String(row.expiry_dte);
    const distance = Math.abs(Number(row.strike) - spot);
    if (!acc[dte] || distance < acc[dte].distance) {
      acc[dte] = { strike: Number(row.strike), distance };
    }
    return acc;
  }, {});
  const insertedAtmMarkers = new Set();

  bodyEl.innerHTML = rows.map(o => {
    const typeColor = o.type === 'CALL' ? 'var(--accent-green)' : 'var(--accent-red)';
    const gamma = Number(o.gamma);
    const vega = Number(o.vega);
    const strike = Number(o.strike);
    const dte = String(o.expiry_dte);
    const atmStrike = atmStrikeByDte[dte]?.strike;
    const isAtmStrike = Math.abs(strike - atmStrike) < 0.0001;
    const isItm = o.type === 'CALL' ? strike < spot : strike > spot;
    const moneynessLabel = isAtmStrike ? 'ATM' : (isItm ? 'ITM' : 'OTM');
    const rowBg = isAtmStrike
      ? 'rgba(0, 212, 255, 0.090)'
      : isItm
        ? (o.type === 'CALL' ? 'rgba(0, 255, 136, 0.045)' : 'rgba(255, 77, 109, 0.045)')
        : 'rgba(255, 255, 255, 0.012)';
    const rowTitle = [
      `Expiry ${o.expiry_date || '-'}`,
      moneynessLabel,
      `Moneyness ${((Number(o.moneyness || 0)) * 100).toFixed(2)}%`,
      `Intrinsic ${Number(o.intrinsic || 0).toFixed(2)}`,
      `Extrinsic ${Number(o.extrinsic || 0).toFixed(2)}`
    ].join(' · ');
    const markerKey = `${dte}-${atmStrike}`;
    const atmMarker = isAtmStrike && !insertedAtmMarkers.has(markerKey)
      ? (() => {
          insertedAtmMarkers.add(markerKey);
          return `
            <tr>
              <td colspan="13" style="padding:0; height:18px; position:relative; background:rgba(0,212,255,0.035);">
                <div style="position:absolute; left:0; right:0; top:50%; border-top:1px dashed rgba(0,212,255,0.72);"></div>
                <div style="position:relative; display:inline-block; margin-left:50%; transform:translateX(-50%); padding:1px 10px; border:1px solid rgba(0,212,255,0.35); border-radius:999px; background:var(--bg-secondary); color:var(--accent-blue); font-size:10px; font-weight:800; letter-spacing:0;">
                  ATM · ${o.expiry_dte} DTE · Spot $${spot.toFixed(2)}
                </div>
              </td>
            </tr>
          `;
        })()
      : '';
    return `
      ${atmMarker}
      <tr title="${rowTitle}" style="border-bottom:1px solid rgba(255,255,255,0.045); text-align:right; background:${rowBg}; ${isAtmStrike ? 'box-shadow: inset 0 1px 0 rgba(0,212,255,0.25), inset 0 -1px 0 rgba(0,212,255,0.15);' : ''}">
        <td style="padding:9px; text-align:left; color:var(--text-muted);">${o.date || '-'}</td>
        <td style="padding:9px;">${o.expiry_dte}</td>
        <td style="padding:9px; text-align:left; color:${typeColor}; font-weight:700;">${o.type}</td>
        <td style="padding:9px; font-family:var(--font-mono); font-weight:700;">${Number(o.strike).toFixed(2)}</td>
        <td style="padding:9px;">${Number(o.bid).toFixed(2)}</td>
        <td style="padding:9px;">${Number(o.ask).toFixed(2)}</td>
        <td style="padding:9px; color:var(--accent-blue); font-weight:700;">${Number(o.mid ?? ((o.bid + o.ask) / 2)).toFixed(2)}</td>
        <td style="padding:9px;">${Number(o.premium).toFixed(2)}</td>
        <td style="padding:9px;">${(Number(o.iv) * 100).toFixed(2)}%</td>
        <td style="padding:9px;">${Number(o.delta).toFixed(4)}</td>
        <td style="padding:9px;">${Math.abs(gamma) < 0.000001 ? '<0.000001' : gamma.toFixed(6)}</td>
        <td style="padding:9px;">${Number(o.theta).toFixed(4)}</td>
        <td style="padding:9px;">${Math.abs(vega) < 0.0001 ? '<0.0001' : vega.toFixed(4)}</td>
      </tr>
    `;
  }).join('');
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
  if (!watchlist.length) {
    list.innerHTML = `<div class="stats-list-item"><span class="label">Add stocks to build market movers.</span><span class="val">-</span></div>`;
    return;
  }

  // Sort watchlist by change pct
  const sorted = [...watchlist].sort((a, b) => {
    const sa = stockStats[a]?.change_pct || 0;
    const sb = stockStats[b]?.change_pct || 0;
    return Math.abs(sb) - Math.abs(sa);
  }).slice(0, 5); // Top 5

  const rows = sorted.map(ticker => {
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
  list.innerHTML = rows || `<div class="stats-list-item"><span class="label">Loading market movers...</span><span class="val">-</span></div>`;
}

function renderAISummary() {
  const list = document.getElementById('ai-score-summary-list');
  if (!list) return;
  if (!watchlist.length) {
    list.innerHTML = `<div class="stats-list-item"><span class="label">Add stocks to build AI scores.</span><span class="val">-</span></div>`;
    return;
  }

  list.innerHTML = watchlist.slice(0, 5).map(ticker => {
    const score = getSignalScore(stockStats[ticker]);
    const color = score == null ? 'var(--text-muted)' : score > 65 ? 'var(--accent-green)' : score < 40 ? 'var(--accent-red)' : '#fbbf24';
    return `
      <div class="stats-list-item">
        <span class="label">${ticker} AI Score</span>
        <span class="val" style="color:${color}">${score == null ? '-' : `${score} / 100`}</span>
      </div>
    `;
  }).join('');
}

function getSignalScore(summary) {
  if (!summary || !Number.isFinite(Number(summary.change_pct))) return null;
  const pct = Number(summary.change_pct);
  return Math.max(5, Math.min(95, Math.round(50 + pct * 8)));
}

function getSignalFromSummary(summary) {
  const score = getSignalScore(summary);
  if (score == null) return { signal: '-', score: null, className: 'signal-hold', color: 'var(--text-muted)' };
  if (score >= 65) return { signal: 'BUY', score, className: 'signal-buy', color: 'var(--accent-green)' };
  if (score <= 35) return { signal: 'SELL', score, className: 'signal-sell', color: 'var(--accent-red)' };
  return { signal: 'HOLD', score, className: 'signal-hold', color: '#fbbf24' };
}

function latestSmaFromHistory(ticker, period = 20) {
  const rows = stockData[ticker]?.['1d']?.data || [];
  const closes = rows.map(row => Number(row.Close)).filter(Number.isFinite);
  if (closes.length < period) return null;
  const slice = closes.slice(-period);
  return slice.reduce((sum, value) => sum + value, 0) / slice.length;
}

function renderStockCards() {
  const grid = document.getElementById('watchlist-grid');
  if (!grid) return;
  if (!watchlist.length) {
    grid.innerHTML = `
      <div class="stock-card watchlist-empty-state">
        <div class="ticker-badge">No watchlist stocks</div>
        <div class="ticker-name">Use the Add Stock box above to add tickers.</div>
      </div>
    `;
    return;
  }

  grid.innerHTML = watchlist.map((ticker, idx) => {
    const s = stockStats[ticker];
    if (!s) return `
      <div class="stock-card loading-stock-card" id="card-${ticker}">
        <div class="stock-card-header">
          <div>
            <div class="ticker-badge">${ticker}</div>
            <div class="ticker-name">Loading market data...</div>
          </div>
          <div class="watchlist-card-actions" onclick="event.stopPropagation()">
            <button class="watchlist-action-btn" onclick="moveWatchlistItem('${ticker}', -1, event)" title="Move left / up" ${idx === 0 ? 'disabled' : ''}>←</button>
            <button class="watchlist-action-btn" onclick="moveWatchlistItem('${ticker}', 1, event)" title="Move right / down" ${idx === watchlist.length - 1 ? 'disabled' : ''}>→</button>
            <button class="watchlist-action-btn danger" onclick="removeStock('${ticker}', event)" title="Remove">✕</button>
          </div>
        </div>
        <div class="stock-price loading-price">Fetching...</div>
        <div class="stock-change loading-copy">Downloading price history and summary.</div>
        <div class="loading-bar"><span></span></div>
        <div class="stock-indicators">
          <span class="indicator-chip">Price pending</span>
          <span class="indicator-chip">Chart pending</span>
        </div>
      </div>
    `;

    const changeValue = Number(s.change || 0);
    const changePct = Number(s.change_pct || 0);
    const price = Number(s.price || 0);
    const isUp = changeValue >= 0;
    const signalInfo = getSignalFromSummary(s);
    const displayName = s.name || TICKER_METADATA[ticker]?.name || ticker;
    const providerLabel = s.provider === 'schwab' ? 'Schwab live' : 'DB';
    const asOfLabel = s.as_of
      ? new Date(s.as_of).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
      : 'n/a';
    const rsi = indicatorData[ticker]?.rsi?.latest;
    const sma20 = indicatorData[ticker]?.moving_averages?.sma20_latest ?? latestSmaFromHistory(ticker, 20);

    return `
      <div class="stock-card ${currentStock === ticker ? 'selected' : ''}" onclick="selectStock('${ticker}')" id="card-${ticker}">
        <div class="stock-card-header">
          <div>
            <div class="ticker-badge">${ticker}</div>
            <div class="ticker-name">${escapeHtml(displayName)}</div>
          </div>
          <div style="display:flex; flex-direction:column; align-items:flex-end; gap:4px">
            <span class="signal-badge ${signalInfo.className}">${signalInfo.signal}</span>
            <div class="watchlist-card-actions">
              <button class="watchlist-action-btn" onclick="moveWatchlistItem('${ticker}', -1, event)" title="Move left / up" ${idx === 0 ? 'disabled' : ''}>←</button>
              <button class="watchlist-action-btn" onclick="moveWatchlistItem('${ticker}', 1, event)" title="Move right / down" ${idx === watchlist.length - 1 ? 'disabled' : ''}>→</button>
              <button class="watchlist-action-btn danger" onclick="removeStock('${ticker}', event)" title="Remove">✕</button>
            </div>
          </div>
        </div>
        <div class="stock-price ${isUp ? 'text-green' : 'text-red'}">$${price.toFixed(2)}</div>
        <div class="stock-change ${isUp ? 'text-green' : 'text-red'}">
          ${isUp ? '▲' : '▼'} ${Math.abs(changeValue).toFixed(2)} (${isUp ? '+' : ''}${changePct.toFixed(2)}%)
        </div>
        <canvas class="mini-chart" id="mini-${ticker}"></canvas>
        <div class="stock-indicators">
          <span class="indicator-chip">${providerLabel}</span>
          <span class="indicator-chip">As of ${asOfLabel}</span>
          <span class="indicator-chip">RSI ${Number.isFinite(Number(rsi)) ? Number(rsi).toFixed(1) : '-'}</span>
          <span class="indicator-chip">Vol ${(s.volume / 1000000).toFixed(1)}M</span>
          <span class="indicator-chip" style="color:${isUp ? 'var(--accent-green)' : 'var(--accent-red)'}">
            SMA20 ${Number.isFinite(Number(sma20)) ? Number(sma20).toFixed(2) : '-'}
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

  } else {
    setS('ind-rsi', '-');
    setS('ind-rsi-signal', 'No indicator data');
    setS('ind-macd', '-');
    setS('ind-macd-signal', 'No indicator data');
  }
  setS('ind-bb-upper', ind?.bollinger?.upper_latest != null ? ind.bollinger.upper_latest.toFixed(2) : '-');
  setS('ind-bb-lower', ind?.bollinger?.lower_latest != null ? ind.bollinger.lower_latest.toFixed(2) : '-');

  const signalInfo = getSignalFromSummary(s);
  const score = signalInfo.score;
  const signal = signalInfo.signal;
  const scoreColor = signalInfo.color;
  const signalClass = signalInfo.className;

  // Top bar mini score
  const scoreValEl = document.getElementById('ai-score-val');
  const scoreFillEl = document.getElementById('ai-score-fill');
  const scoreLabelEl = document.getElementById('ai-score-label');
  if (scoreValEl) scoreValEl.textContent = score == null ? '-' : score;
  if (scoreFillEl) { scoreFillEl.style.width = `${score || 0}%`; scoreFillEl.style.background = scoreColor; }
  if (scoreLabelEl) { scoreLabelEl.textContent = signal; scoreLabelEl.className = `score-label ${signal === 'BUY' ? 'text-green' : signal === 'SELL' ? 'text-red' : ''}`; }

  // Bottom panel large score + signal badge
  const scoreVal2El = document.getElementById('ai-score-val2');
  const scoreFill2El = document.getElementById('ai-score-fill2');
  const signalTextEl = document.getElementById('ai-signal-text');
  if (scoreVal2El) scoreVal2El.textContent = score == null ? '-' : score;
  if (scoreFill2El) { scoreFill2El.style.width = `${score || 0}%`; scoreFill2El.style.background = scoreColor; }
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
  } else {
    rsiEl.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted)">No RSI data</div>';
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
    macdEl.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted)">No MACD data</div>';
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
async function renderAIPage() {
  renderAISignalsLoading();
  renderAIBrief();
  renderNews();
}

function renderAISignalsLoading() {
  const grid = document.getElementById('signal-grid');
  if (!grid) return;
  const tickers = (watchlist || DEFAULT_WATCHLIST).slice(0, 8);
  grid.innerHTML = tickers.map(ticker => `
    <div class="signal-item" style="background:rgba(255,255,255,0.035); border:1px solid var(--border);">
      <div class="s-ticker">${escapeHtml(ticker)}</div>
      <div class="s-action" style="color:var(--text-muted)">...</div>
      <div class="s-confidence" style="color:var(--text-muted)">Loading</div>
    </div>
  `).join('');
}

async function renderAIBrief() {
  const ids = {
    market_overview: 'ai-market-overview',
    technical_analysis: 'ai-technical-analysis',
    news_sentiment: 'ai-news-sentiment',
    risk_assessment: 'ai-risk-assessment'
  };
  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  };

  try {
    const tickers = (watchlist || DEFAULT_WATCHLIST).slice(0, 8).join(',');
    const res = await apiFetch(`/api/stocks/ai-brief?tickers=${encodeURIComponent(tickers)}&limit=8`);
    const brief = res?.brief || {};
    Object.entries(ids).forEach(([key, id]) => {
      setText(id, brief[key] || 'No real market brief available yet.');
    });
    renderAISignals(res?.signals || []);

    const riskLevel = document.getElementById('ai-risk-level');
    const gauge = document.getElementById('ai-risk-gauge');
    if (riskLevel) riskLevel.textContent = brief.risk_level || 'Unknown';
    if (gauge) {
      const width = Math.max(10, Math.min(90, Number(brief.risk_score || 50)));
      const color = width >= 65
        ? 'linear-gradient(90deg,#fbbf24,var(--accent-red))'
        : width <= 35
          ? 'linear-gradient(90deg,var(--accent-green),#86efac)'
          : 'linear-gradient(90deg,var(--accent-green),#fbbf24)';
      gauge.style.width = `${width}%`;
      gauge.style.background = color;
    }

    const reportDate = document.querySelector('#page-ai .report-header .report-date');
    if (reportDate && res?.data_source) {
      reportDate.textContent = `${res.analysis_source} • ${res.data_source}`;
    }
  } catch (err) {
    console.error('AI market brief failed:', err);
    Object.values(ids).forEach(id => setText(id, 'Real market brief is temporarily unavailable. Try refreshing after market data reconnects.'));
    renderAISignals([]);
  }
}

function renderAISignals(signals) {
  const grid = document.getElementById('signal-grid');
  if (!grid) return;

  if (!signals.length) {
    grid.innerHTML = `
      <div class="signal-item" style="background:rgba(255,255,255,0.035); border:1px solid var(--border);">
        <div class="s-ticker">DATA</div>
        <div class="s-action" style="color:var(--text-muted)">WAIT</div>
        <div class="s-confidence" style="color:var(--text-muted)">No live signals</div>
      </div>`;
    return;
  }

  grid.innerHTML = signals.map(s => {
    const signal = s.signal || 'HOLD';
    const aiScore = Number(s.score || 50);
    const bgColor = { BUY: 'var(--accent-green-dim)', SELL: 'var(--accent-red-dim)', HOLD: 'rgba(251,191,36,0.08)' }[signal];
    const textColor = { BUY: 'var(--accent-green)', SELL: 'var(--accent-red)', HOLD: '#fbbf24' }[signal];
    const price = Number(s.price || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
    const change = Number(s.change_pct || 0);
    return `
      <div class="signal-item" style="background:${bgColor}; border: 1px solid ${textColor}22;" title="$${price} · ${change >= 0 ? '+' : ''}${change.toFixed(2)}% · as of ${escapeHtml(s.as_of || 'latest')}">
        <div class="s-ticker">${escapeHtml(s.ticker)}</div>
        <div class="s-action" style="color:${textColor}">${signal}</div>
        <div class="s-confidence" style="color:${textColor}">$${price} · ${aiScore}%</div>
      </div>`;
  }).join('');
}

async function renderNews() {
  const list = document.getElementById('news-list');
  if (!list) return;

  list.innerHTML = `
    <div class="news-item">
      <div class="news-meta">Loading real market news...</div>
    </div>
  `;

  try {
    const tickers = (watchlist || []).slice(0, 12).join(',');
    const res = await apiFetch(`/api/stocks/news?tickers=${encodeURIComponent(tickers)}&limit=10&today_only=true`);
    const items = res?.items || [];
    const header = document.querySelector('#page-ai .report-date');
    if (header) {
      const scopeText = res?.scope === 'today'
        ? 'Real news • Today'
        : 'Real news • Latest available';
      const sources = (res?.sources || []).join(', ');
      header.textContent = `${scopeText}${sources ? ` • ${sources}` : ''}`;
    }

    if (!items.length) {
      list.innerHTML = `
        <div class="news-item">
          <h4>No market news available from configured feeds right now.</h4>
          <div class="news-meta"><span>Try refresh later</span><span class="sentiment-tag sentiment-neutral">LIVE FEEDS</span></div>
        </div>
      `;
      return;
    }

    list.innerHTML = items.map(renderNewsItem).join('');
  } catch (err) {
    console.error('Real news fetch failed:', err);
    list.innerHTML = DEMO_NEWS_FALLBACK.map(n => renderNewsItem({ ...n, url: '#', source: `${n.source} demo` })).join('');
    const header = document.querySelector('#page-ai .report-date');
    if (header) header.textContent = 'Demo fallback • Real news temporarily unavailable';
  }
}

function renderNewsItem(n) {
  const url = n.url && /^https?:\/\//i.test(String(n.url)) ? String(n.url) : null;
  const safeUrl = url ? url.replace(/'/g, "\\'") : null;
  const clickAttr = safeUrl ? ` onclick="window.open('${safeUrl}', '_blank', 'noopener')"` : '';
  const ticker = escapeHtml(n.ticker || 'MARKET');
  const tag = escapeHtml(n.tag || 'BUSINESS');
  const title = escapeHtml(n.title || 'Untitled market update');
  const source = escapeHtml(n.source || 'Source');
  const time = escapeHtml(n.time || 'recent');
  const sentiment = ['bullish', 'bearish', 'neutral'].includes(n.sentiment) ? n.sentiment : 'neutral';
  return `
    <div class="news-item">
      <div class="news-tag">
        <span class="indicator-chip" style="font-size:9px">${ticker}</span>
        <span style="color:var(--text-muted)">${tag}</span>
      </div>
      <h4>${title}</h4>
      <div class="news-meta">
        <span>${source}</span>
        <span>${time}</span>
        ${n.is_today === false ? '<span>latest</span>' : ''}
        <span class="sentiment-tag sentiment-${sentiment}">${sentiment.toUpperCase()}</span>
      </div>
    </div>
  `.replace('<div class="news-item">', `<div class="news-item"${clickAttr}>`);
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[ch]));
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

// ===== Options Page =====
let optionsCurrentTab = 'chain';
const optionsChainClientCache = {};
const OPTIONS_CHAIN_CLIENT_CACHE_MS = 60 * 1000;
let optionsChainState = { ticker: 'TSLA', underlying: null, options: [], loadedAt: null };
let optionsBuilderLegs = [];

function switchOptionsTab(tab) {
  optionsCurrentTab = tab;
  
  // Update Buttons
  document.querySelectorAll('#page-options .interval-tab').forEach(btn => btn.classList.remove('active'));
  document.getElementById(`tab-options-${tab}`).classList.add('active');

  // Update Content
  document.getElementById('options-content-chain').style.display = tab === 'chain' ? 'block' : 'none';
  document.getElementById('options-content-candidates').style.display = tab === 'candidates' ? 'block' : 'none';
  document.getElementById('options-content-builder').style.display = tab === 'builder' ? 'block' : 'none';
  document.getElementById('options-content-backtest').style.display = tab === 'backtest' ? 'block' : 'none';

  if (tab === 'candidates') {
    renderOptionsCandidates();
  } else if (tab === 'builder') {
    renderOptionsBuilder();
  }
}

function handleOptionsTickerKey(event) {
  if (event.key === 'Enter') refreshOptionsData();
}

function money2(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(2) : '-';
}

function pct1(value) {
  const n = Number(value);
  return Number.isFinite(n) ? `${(n * 100).toFixed(1)}%` : '-';
}

function num0(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toLocaleString() : '-';
}

async function fetchSimulatedChain() {
  const ticker = document.getElementById('sim-options-ticker').value.toUpperCase() || 'TSLA';
  const statusEl = document.getElementById('sim-options-status');
  const body = document.getElementById('sim-options-body');
  
  statusEl.textContent = '🔮 Generating...';
  
  try {
    const data = await apiFetch(`/api/options/synth/chain/${ticker}`);
    if (!data || !data.options) throw new Error("No data");
    
    document.getElementById('sim-spot').textContent = `$${data.spot_price.toFixed(2)}`;
    document.getElementById('sim-rsi').textContent = data.rsi;
    document.getElementById('sim-hv').textContent = (data.hv_20 * 100).toFixed(1) + '%';
    
    body.innerHTML = data.options.map(o => `
      <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
        <td style="padding:10px;">${o.expiry_dte}d</td>
        <td style="padding:10px;"><span class="indicator-chip" style="background:${o.type === 'CALL' ? 'rgba(0,230,118,0.1)' : 'rgba(255,76,106,0.1)'}; color:${o.type === 'CALL' ? 'var(--accent-green)' : 'var(--accent-red)'}; border:none;">${o.type}</span></td>
        <td style="padding:10px; font-weight:bold;">${o.strike}</td>
        <td style="padding:10px; color:var(--accent-blue);">$${o.premium.toFixed(2)}</td>
        <td style="padding:10px;">${o.bid.toFixed(2)} / ${o.ask.toFixed(2)}</td>
        <td style="padding:10px; color:${o.delta > 0 ? 'var(--accent-green)' : 'var(--accent-red)'}">${o.delta.toFixed(2)}</td>
        <td style="padding:10px;">${o.theta.toFixed(3)}</td>
        <td style="padding:10px;">${(o.iv * 100).toFixed(1)}%</td>
      </tr>
    `).join('');
    
    statusEl.textContent = 'Updated ' + new Date().toLocaleTimeString();
  } catch (err) {
    statusEl.textContent = '❌ Error';
    body.innerHTML = `<tr><td colspan="8" style="padding:20px; text-align:center; color:var(--accent-red);">Failed to generate: ${err.message}</td></tr>`;
  }
}

async function runOptionBacktest() {
  const ticker = document.getElementById('opt-bt-ticker').value.toUpperCase();
  const type = document.getElementById('opt-bt-type').value;
  const start = document.getElementById('opt-bt-start').value;
  const end = document.getElementById('opt-bt-end').value;
  
  const resultPanel = document.getElementById('opt-bt-results');
  const summaryEl = document.getElementById('opt-bt-summary');
  
  resultPanel.style.display = 'block';
  summaryEl.innerHTML = '⌛ Running simulation... This may take a few seconds.';
  
  try {
    const endpointMap = {
      'WHEELS': '/api/options/backtest/wheels',
      'LEAPS': '/api/options/backtest/leaps',
      'SPREADS': '/api/options/backtest/spreads'
    };
    const endpoint = endpointMap[type] || endpointMap['WHEELS'];

    const res = await apiFetch(endpoint, {
      method: 'POST',
      body: JSON.stringify({
        ticker,
        start_date: start,
        end_date: end,
        initial_capital: 50000,
        params: { put_delta: -0.3, call_delta: 0.3, dte_target: 30 }
      })
    });
    
    if (!res || res.error) throw new Error(res.error || "Unknown error");
    
    const profit = res.final_capital - res.initial_capital;
    const profitPct = (profit / res.initial_capital) * 100;
    
    summaryEl.innerHTML = `
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:15px;">
        <div class="stat-card" style="padding:12px; background:rgba(255,255,255,0.03);">
          <div style="font-size:12px; color:var(--text-muted);">Final Capital</div>
          <div style="font-size:20px; font-weight:bold; color:var(--accent-green);">$${res.final_capital.toLocaleString()}</div>
        </div>
        <div class="stat-card" style="padding:12px; background:rgba(255,255,255,0.03);">
          <div style="font-size:12px; color:var(--text-muted);">Total Return</div>
          <div style="font-size:20px; font-weight:bold; color:${profit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}">${profit >= 0 ? '+' : ''}${profitPct.toFixed(2)}%</div>
        </div>
      </div>
      <div style="font-size:12px; color:var(--text-muted);">
        Total Trades: ${res.trades.length}<br>
        Period: ${start} to ${end}
      </div>
    `;
    
    // Draw Equity Chart
    const chartEl = document.getElementById('opt-bt-chart');
    chartEl.innerHTML = '';
    const chart = LightweightCharts.createChart(chartEl, {
      width: chartEl.offsetWidth,
      height: 250,
      layout: { background: { color: 'transparent' }, textColor: '#7a8aab' },
      grid: { vertLines: { visible: false }, horzLines: { color: 'rgba(255,255,255,0.05)' } },
      timeScale: { borderColor: 'rgba(255,255,255,0.1)' }
    });
    const lineSeries = chart.addLineSeries({ color: 'var(--accent-blue)', lineWidth: 2 });
    lineSeries.setData(res.equity_curve.map(d => ({
      time: d.date,
      value: d.equity
    })));
    chart.timeScale().fitContent();
    
  } catch (err) {
    summaryEl.innerHTML = `<div class="text-red">Error: ${err.message}</div>`;
  }
}

async function renderOptionsPage() {
  applyI18n();
  const statusEl = document.getElementById('options-refresh-status');
  const authMsgEl = document.getElementById('schwab-auth-msg');
  const authSection = document.getElementById('schwab-auth-section');
  if (!statusEl) return;

  statusEl.textContent = t('options.checkingStatus');
  try {
    const data = await apiFetch('/api/options/schwab/status');
    if (data && data.connected) {
      statusEl.textContent = t('options.ready');
      if (authSection) authSection.style.display = 'none';
      refreshOptionsData();
    } else if (data && data.configured === false) {
      statusEl.textContent = data.message || 'Real-time Schwab data is not configured in this deployment.';
      if (authSection) authSection.style.display = 'none';
      if (authMsgEl) authMsgEl.textContent = '';
    } else if (data && data.status === 'NEEDS_AUTH') {
      statusEl.textContent = t('options.authorizationNeeded');
      if (authSection) authSection.style.display = 'block';
      if (authMsgEl) authMsgEl.textContent = `Status: ${data?.status || 'Offline'}`;
    } else {
      statusEl.textContent = t('options.checkingChain');
      if (authSection) authSection.style.display = 'none';
      refreshOptionsData();
    }
  } catch (err) {
    statusEl.innerHTML = `<span style="color:var(--accent-red); font-weight:bold;">${t('options.statusError')}</span>`;
    console.error("Status check failed:", err);
  }
}

async function refreshOptionsData(ticker = null) {
  const inputTicker = ticker || document.getElementById('options-chain-ticker')?.value || 'TSLA';
  const cleanTicker = inputTicker.trim().toUpperCase() || 'TSLA';
  const tickerInput = document.getElementById('options-chain-ticker');
  if (tickerInput) tickerInput.value = cleanTicker;

  const statusEl = document.getElementById('options-refresh-status');
  const refreshBtn = document.querySelector('button[onclick^="refreshOptionsData"]');
  const bodyEl = document.getElementById('options-chain-body');
  if (!statusEl || !bodyEl) return;

  statusEl.textContent = t('options.refreshing', { ticker: cleanTicker });
  if (refreshBtn) refreshBtn.disabled = true;

  try {
    const cacheKey = `${cleanTicker}:ALL:20`;
    const cached = optionsChainClientCache[cacheKey];
    let data = cached && Date.now() - cached.ts < OPTIONS_CHAIN_CLIENT_CACHE_MS ? cached.data : null;
    if (data) {
      statusEl.textContent = t('options.usingCached', { ticker: cleanTicker });
    } else {
      data = await apiFetch(`/api/options/schwab/chain/${encodeURIComponent(cleanTicker)}?contractType=ALL&strikeCount=20`);
      if (data && data.options) {
        optionsChainClientCache[cacheKey] = { ts: Date.now(), data };
      }
    }
    if (!data || !data.options) {
      statusEl.textContent = apiFetch.lastError?.message || t('options.fetchFailed');
      if (apiFetch.lastError?.status === 403) {
        statusEl.textContent = t('options.authRequiredStatus');
        const authSection = document.getElementById('schwab-auth-section');
        if (authSection) {
          authSection.style.opacity = "1";
          authSection.style.display = 'block';
        }
        const authMsgEl = document.getElementById('schwab-auth-msg');
        if (authMsgEl) authMsgEl.textContent = 'Status: NEEDS_AUTH';
      }
      return;
    }

    optionsChainState = {
      ticker: cleanTicker,
      underlying: Number(data.underlying_price || 0),
      options: data.options || [],
      loadedAt: new Date(),
    };

    updateOptionsExpirationFilter();
    updateOptionsSummary(data);
    renderOptionsChainTable();
    renderOptionsCandidates();
    renderOptionsBuilder();

    const cacheAge = optionsChainClientCache[cacheKey] ? Math.round((Date.now() - optionsChainClientCache[cacheKey].ts) / 1000) : 0;
    statusEl.textContent = t('options.updated', {
      ticker: cleanTicker,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      cacheAge,
    });

    const authSection = document.getElementById('schwab-auth-section');
    if (authSection) {
        authSection.style.transition = "opacity 0.5s";
        authSection.style.opacity = "0";
        setTimeout(() => authSection.style.display = 'none', 500);
    }

  } catch (err) {
    console.error("Options refresh error:", err);
    const message = err.message.toLowerCase();
    if (message.includes('authorization') || message.includes('token')) {
      statusEl.textContent = t('options.authExpired');
      const authSection = document.getElementById('schwab-auth-section');
      if (authSection) authSection.style.display = 'block';
    } else {
      statusEl.textContent = t('options.refreshFailed');
    }
  } finally {
    if (refreshBtn) refreshBtn.disabled = false;
  }
}

function updateOptionsExpirationFilter() {
  const select = document.getElementById('options-expiration-filter');
  if (!select) return;
  const current = select.value || 'ALL';
  const expiries = [...new Set(optionsChainState.options.map(o => o.expiry).filter(Boolean))].sort();
  select.innerHTML = `<option value="ALL">${t('options.allExpirations')}</option>` + expiries.map(exp => {
    const first = optionsChainState.options.find(o => o.expiry === exp);
    const dte = first?.expiry_dte ?? '-';
    return `<option value="${exp}">${exp} · ${dte} DTE</option>`;
  }).join('');
  select.value = expiries.includes(current) ? current : 'ALL';
}

function updateOptionsSummary(data) {
  const options = data.options || [];
  const spot = Number(data.underlying_price || 0);
  const strikes = [...new Set(options.map(o => Number(o.strike)).filter(Number.isFinite))];
  const atm = strikes.length ? strikes.reduce((best, strike) => Math.abs(strike - spot) < Math.abs(best - spot) ? strike : best, strikes[0]) : null;
  const liquid = options.filter(o => Number(o.bid) > 0 && Number(o.ask) > 0);
  const avgSpreadPct = liquid.length
    ? liquid.reduce((sum, o) => {
      const mid = (Number(o.bid) + Number(o.ask)) / 2;
      return sum + (mid > 0 ? (Number(o.ask) - Number(o.bid)) / mid : 0);
    }, 0) / liquid.length
    : null;
  const health = avgSpreadPct == null ? '-' : avgSpreadPct < 0.08 ? t('options.healthGood') : avgSpreadPct < 0.18 ? t('options.healthWatch') : t('options.healthWide');

  document.getElementById('options-underlying-price').textContent = spot ? `$${spot.toFixed(2)}` : '-';
  document.getElementById('options-contract-count').textContent = options.length.toLocaleString();
  document.getElementById('options-atm-strike').textContent = atm != null ? `$${atm.toFixed(2)}` : '-';
  document.getElementById('options-spread-health').textContent = health;
}

function getFilteredOptionsRows() {
  const expiryFilter = document.getElementById('options-expiration-filter')?.value || 'ALL';
  const typeFilter = document.getElementById('options-type-filter')?.value || 'BOTH';
  const deltaFilter = document.getElementById('options-delta-filter')?.value || 'ALL';
  const spot = Number(optionsChainState.underlying || 0);

  return optionsChainState.options.filter(o => {
    if (expiryFilter !== 'ALL' && o.expiry !== expiryFilter) return false;
    if (typeFilter !== 'BOTH' && o.type !== typeFilter) return false;
    const delta = Number(o.delta);
    const dte = Number(o.expiry_dte);
    const strike = Number(o.strike);
    if (deltaFilter === 'ATM') return spot && Math.abs(strike - spot) / spot <= 0.025;
    if (deltaFilter === 'WHEEL') return o.type === 'PUT' && delta <= -0.18 && delta >= -0.38 && dte >= 20 && dte <= 60;
    if (deltaFilter === 'COVERED_CALL') return o.type === 'CALL' && delta >= 0.15 && delta <= 0.35 && dte >= 20 && dte <= 60;
    if (deltaFilter === 'LEAPS') return o.type === 'CALL' && delta >= 0.6 && delta <= 0.9 && dte >= 300;
    return true;
  });
}

function renderOptionsChainTable() {
  const body = document.getElementById('options-chain-body');
  const meta = document.getElementById('options-chain-meta');
  if (!body) return;
  const rows = getFilteredOptionsRows();
  const expiryFilter = document.getElementById('options-expiration-filter')?.value || 'ALL';
  const spot = Number(optionsChainState.underlying || 0);
  const grouped = new Map();
  rows.forEach(o => {
    const key = `${o.expiry}|${Number(o.strike).toFixed(2)}`;
    if (!grouped.has(key)) grouped.set(key, { expiry: o.expiry, dte: o.expiry_dte, strike: Number(o.strike), call: null, put: null });
    grouped.get(key)[o.type === 'CALL' ? 'call' : 'put'] = o;
  });

  const groupedRows = [...grouped.values()];
  const expiries = [...new Set(groupedRows.map(row => row.expiry || ''))].sort();
  const rowsPerExpiry = expiryFilter === 'ALL' ? 21 : 61;
  const maxRows = 220;
  const centeredRows = [];

  expiries.forEach(expiry => {
    const expiryRows = groupedRows
      .filter(row => (row.expiry || '') === expiry)
      .sort((a, b) => a.strike - b.strike);
    if (!expiryRows.length) return;
    if (!spot || expiryRows.length <= rowsPerExpiry) {
      centeredRows.push(...expiryRows);
      return;
    }
    const atmIndex = expiryRows.reduce((bestIdx, row, idx) =>
      Math.abs(row.strike - spot) < Math.abs(expiryRows[bestIdx].strike - spot) ? idx : bestIdx
    , 0);
    const halfWindow = Math.floor(rowsPerExpiry / 2);
    let start = Math.max(0, atmIndex - halfWindow);
    let end = Math.min(expiryRows.length, start + rowsPerExpiry);
    start = Math.max(0, end - rowsPerExpiry);
    centeredRows.push(...expiryRows.slice(start, end));
  });

  const tableRows = centeredRows.slice(0, maxRows);

  if (meta) {
    meta.textContent = optionsChainState.loadedAt
      ? t('options.filteredMeta', {
        ticker: optionsChainState.ticker,
        visible: tableRows.length.toLocaleString(),
        total: rows.length.toLocaleString(),
        time: optionsChainState.loadedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      })
      : t('options.loadChain');
  }

  if (!tableRows.length) {
    body.innerHTML = `<tr><td colspan="13" class="options-empty-row">${t('options.noContracts')}</td></tr>`;
    return;
  }

  const cell = (o, field, formatter = money2) => o ? formatter(o[field]) : '-';
  body.innerHTML = tableRows.map(row => {
    const isAtm = spot && Math.abs(row.strike - spot) / spot <= 0.0075;
    return `
      <tr class="${isAtm ? 'atm-row' : ''}">
        <td class="call-cell">${cell(row.call, 'bid')}</td>
        <td class="call-cell">${cell(row.call, 'ask')}</td>
        <td class="call-cell">${cell(row.call, 'delta', v => money2(v))}</td>
        <td class="call-cell">${cell(row.call, 'iv', pct1)}</td>
        <td class="call-cell">${cell(row.call, 'open_interest', num0)}</td>
        <td class="call-cell">${cell(row.call, 'volume', num0)}</td>
        <td class="strike-cell" title="${row.expiry} · ${row.dte} DTE">$${row.strike.toFixed(2)}</td>
        <td class="put-cell">${cell(row.put, 'bid')}</td>
        <td class="put-cell">${cell(row.put, 'ask')}</td>
        <td class="put-cell">${cell(row.put, 'delta', v => money2(v))}</td>
        <td class="put-cell">${cell(row.put, 'iv', pct1)}</td>
        <td class="put-cell">${cell(row.put, 'open_interest', num0)}</td>
        <td class="put-cell">${cell(row.put, 'volume', num0)}</td>
      </tr>
    `;
  }).join('');
}

function renderOptionsCandidates() {
  const options = optionsChainState.options || [];
  const byLiquidity = (a, b) => (Number(b.volume || 0) + Number(b.open_interest || 0)) - (Number(a.volume || 0) + Number(a.open_interest || 0));
  const putWheel = options.filter(o => o.type === 'PUT' && o.delta <= -0.18 && o.delta >= -0.38 && o.expiry_dte >= 20 && o.expiry_dte <= 60).sort(byLiquidity).slice(0, 6);
  const coveredCalls = options.filter(o => o.type === 'CALL' && o.delta >= 0.15 && o.delta <= 0.35 && o.expiry_dte >= 20 && o.expiry_dte <= 60).sort(byLiquidity).slice(0, 6);
  const leaps = options.filter(o => o.type === 'CALL' && o.delta >= 0.6 && o.delta <= 0.9 && o.expiry_dte >= 300).sort((a, b) => b.expiry_dte - a.expiry_dte).slice(0, 6);
  const spreadShorts = options.filter(o => Math.abs(Number(o.delta)) >= 0.18 && Math.abs(Number(o.delta)) <= 0.35 && o.expiry_dte >= 20 && o.expiry_dte <= 60).sort(byLiquidity).slice(0, 6);

  renderCandidateList('options-wheel-candidates', putWheel, t('options.wheelCandidate'));
  renderCandidateList('options-covered-call-candidates', coveredCalls, t('options.coveredCallCandidate'));
  renderCandidateList('options-leaps-candidates', leaps, t('options.leapsCandidate'));
  renderCandidateList('options-spread-candidates', spreadShorts, t('options.shortLegCandidate'));
}

function renderCandidateList(id, rows, label) {
  const el = document.getElementById(id);
  if (!el) return;
  if (!rows.length) {
    el.innerHTML = `<div class="options-empty-note">${t('options.noCandidates')}</div>`;
    return;
  }
  el.innerHTML = rows.map(o => `
    <button class="options-candidate-card" onclick="addOptionLeg('${encodeURIComponent(o.symbol)}')">
      <span>${label}</span>
      <strong>${o.expiry} · ${o.expiry_dte}D · $${money2(o.strike)} ${o.type}</strong>
      <small>Bid/Ask ${money2(o.bid)} / ${money2(o.ask)} · Δ ${money2(o.delta)} · IV ${pct1(o.iv)} · OI ${num0(o.open_interest)}</small>
    </button>
  `).join('');
}

function addOptionLeg(encodedSymbol) {
  const symbol = decodeURIComponent(encodedSymbol);
  const contract = optionsChainState.options.find(o => o.symbol === symbol);
  if (!contract) return;
  optionsBuilderLegs.push({ ...contract, action: contract.type === 'PUT' ? 'SELL' : 'BUY', qty: 1 });
  switchOptionsTab('builder');
}

function renderOptionsBuilder() {
  const empty = document.getElementById('options-builder-empty');
  const legsEl = document.getElementById('options-builder-legs');
  if (!empty || !legsEl) return;
  empty.style.display = optionsBuilderLegs.length ? 'none' : 'block';
  if (!optionsBuilderLegs.length) {
    legsEl.innerHTML = '';
    return;
  }
  const netDebit = optionsBuilderLegs.reduce((sum, leg) => {
    const mid = Number(leg.mid || ((Number(leg.bid || 0) + Number(leg.ask || 0)) / 2));
    return sum + (leg.action === 'BUY' ? mid : -mid) * Number(leg.qty || 1) * 100;
  }, 0);
  legsEl.innerHTML = `
    <div class="options-builder-summary">
      <span>${t('options.legs', { count: optionsBuilderLegs.length })}</span>
      <span>${netDebit >= 0 ? t('options.netDebit') : t('options.netCredit')} $${Math.abs(netDebit).toFixed(0)}</span>
      <button class="btn btn-ghost" onclick="optionsBuilderLegs=[]; renderOptionsBuilder();">${t('options.clear')}</button>
    </div>
    ${optionsBuilderLegs.map((leg, idx) => `
      <div class="options-builder-leg">
        <strong>${leg.action} ${leg.qty} ${leg.expiry} $${money2(leg.strike)} ${leg.type}</strong>
        <span>Mid ${money2(leg.mid)} · Δ ${money2(leg.delta)} · IV ${pct1(leg.iv)}</span>
        <button onclick="optionsBuilderLegs.splice(${idx},1); renderOptionsBuilder();">${t('options.remove')}</button>
      </div>
    `).join('')}
  `;
}

async function submitSchwabOAuthCode() {
  const code = document.getElementById('schwab-auth-code').value;
  const msgEl = document.getElementById('schwab-auth-msg');
  if (!code) return;

  msgEl.textContent = t('options.savingToken');
  msgEl.style.color = "var(--text-muted)";

  try {
    const res = await fetch('/api/options/schwab/exchange-code', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`
      },
      body: JSON.stringify({ code })
    });

    const result = await res.json();
    if (res.ok) {
      msgEl.innerHTML = `<span style="color:var(--accent-green); font-weight:bold;">${t('options.tokenSaved')}</span>`;
      setTimeout(() => renderOptionsPage(), 800);
    } else {
      msgEl.textContent = `${t('common.error')}: ${result.detail || t('options.tokenSaveFailed')}`;
      msgEl.style.color = "var(--accent-red)";
    }
  } catch (err) {
    msgEl.textContent = t('options.networkError');
    msgEl.style.color = "var(--accent-red)";
  }
}
async function showSchwabAuthUrl() {
  const msgEl = document.getElementById('schwab-auth-msg');
  msgEl.textContent = t('options.loadingAuthUrl');
  msgEl.style.color = "var(--accent-blue)";

  try {
    const res = await fetch('/api/options/schwab/auth-url', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });
    const result = await res.json();
    if (res.ok) {
      msgEl.innerHTML = `${t('options.openAuthUrl')}<br><a href="${result.authorization_url}" target="_blank" style="color:var(--accent-blue);">${t('options.authUrlLabel')}</a>`;
    } else {
      msgEl.textContent = result.detail || t('options.authRequestFailed');
    }
  } catch (err) {
    msgEl.textContent = `${t('options.networkError')}: ${err.message}`;
  }
}

// ===== Global stats =====
function renderGlobalStats() {
  const setText = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  };
  const setClass = (id, className) => {
    const el = document.getElementById(id);
    if (el) {
      el.classList.remove('up', 'down', 'neutral', 'text-green', 'text-red');
      el.classList.add(className);
    }
  };
  const formatAsOf = (summary) => summary?.as_of
    ? new Date(summary.as_of).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : 'time unknown';
  const renderProxyMove = ({ valueId, labelId, summary, fallbackLabel, proxyLabel }) => {
    if (summary) {
      const pct = Number(summary.change_pct || 0);
      const up = pct >= 0;
      setText(valueId, `${up ? '+' : ''}${pct.toFixed(2)}%`);
      setClass(valueId, up ? 'up' : 'down');
      setText(labelId, `${up ? '▲' : '▼'} ${proxyLabel} proxy · ${summary.provider || 'data'} · ${formatAsOf(summary)}`);
      setClass(labelId, up ? 'up' : 'down');
    } else {
      setText(valueId, '-');
      setClass(valueId, 'neutral');
      setText(labelId, fallbackLabel);
      setClass(labelId, 'neutral');
    }
  };

  const spProxy = stockStats.SPY || stockStats.VOO || stockStats.QQQ;
  renderProxyMove({
    valueId: 'spy-val',
    labelId: 'spy-change-label',
    summary: spProxy,
    fallbackLabel: 'Waiting for S&P data',
    proxyLabel: spProxy?.symbol || (stockStats.VOO ? 'VOO' : 'QQQ')
  });

  renderProxyMove({
    valueId: 'nasdaq-val',
    labelId: 'nasdaq-change-label',
    summary: stockStats.QQQ,
    fallbackLabel: 'Waiting for NASDAQ data',
    proxyLabel: 'QQQ'
  });

  const vix = stockStats['^VIX'];
  if (vix && Number.isFinite(Number(vix.price))) {
    const change = Number(vix.change || 0);
    const up = change >= 0;
    setText('vix-val', Number(vix.price).toFixed(2));
    setClass('vix-val', up ? 'up' : 'down');
    setText('vix-change-label', `${up ? '▲' : '▼'} ${Math.abs(change).toFixed(2)} (${up ? '+' : ''}${Number(vix.change_pct || 0).toFixed(2)}%) · ${vix.provider || 'data'} · ${formatAsOf(vix)}`);
    setClass('vix-change-label', up ? 'up' : 'down');
  } else {
    setText('vix-val', '-');
    setClass('vix-val', 'neutral');
    setText('vix-change-label', 'Waiting for VIX data');
    setClass('vix-change-label', 'neutral');
  }

  const signals = Object.values(stockStats).reduce((acc, s) => {
    if (s.symbol === '^VIX') return acc;
    const pct = Number(s.change_pct || 0);
    if (pct > 0.5) acc.buy += 1;
    else if (pct < -0.5) acc.sell += 1;
    else acc.hold += 1;
    return acc;
  }, { buy: 0, sell: 0, hold: 0 });
  setText('ai-picks', `${signals.buy} BUY · ${signals.sell} SELL`);
  setText('ai-picks-label', `${signals.hold} HOLD · based on loaded watchlist`);
}

// ===== Init =====
window.addEventListener('load', async () => {
  applyI18n();
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

async function updateAuthUI() {
  const logoutBtn = document.getElementById('btn-logout');
  const userProfile = document.getElementById('user-profile-info');
  const userNameEl = document.getElementById('current-user-name');

  if (logoutBtn) {
    logoutBtn.innerHTML = authToken
      ? `<span class="icon">🚪</span><span id="logout-text">${t('auth.logout')}</span>`
      : `<span class="icon">👤</span><span id="logout-text">${t('auth.login')}</span>`;
  }

  if (authToken) {
    if (userProfile) userProfile.style.display = 'block';
    // Fetch user info
    const info = await apiFetch('/api/users/me');
    if (info && userNameEl) {
      userNameEl.textContent = info.full_name || info.email;
    }
  } else {
    if (userProfile) userProfile.style.display = 'none';
  }
}

// --- Change Password Handlers ---
function showChangePasswordModal() {
  const overlay = document.getElementById('password-overlay');
  if (overlay) overlay.style.display = 'flex';
}

function hideChangePasswordModal() {
  const overlay = document.getElementById('password-overlay');
  if (overlay) overlay.style.display = 'none';
}

async function handleChangePasswordSubmit() {
  const oldPw = document.getElementById('old-password').value;
  const newPw = document.getElementById('new-password').value;
  const confirmPw = document.getElementById('confirm-password').value;
  const errorEl = document.getElementById('password-error');

  if (newPw !== confirmPw) {
    errorEl.textContent = t('auth.passwordMismatch');
    errorEl.style.display = 'block';
    return;
  }

  try {
    const res = await fetch('/api/auth/change-password', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`
      },
      body: JSON.stringify({ old_password: oldPw, new_password: newPw })
    });

    if (res.ok) {
      alert(t('auth.passwordUpdated'));
      hideChangePasswordModal();
    } else {
      const err = await res.json();
      errorEl.textContent = err.detail || t('auth.updateFailed');
      errorEl.style.display = 'block';
    }
  } catch (err) {
    errorEl.textContent = t('options.networkError');
    errorEl.style.display = 'block';
  }
}

function handleLogoutOrLogin() {
  if (authToken) {
    performLogout('user clicked logout');
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
    const provider = document.getElementById('ai-model-select')?.value || 'auto';
    const url = `/api/stocks/${currentStock}/analysis?language=${lang}&provider=${provider}`;
    console.log(`[AI-AGENT] Fetching: ${url}`);
    const res = await apiFetch(url);
    console.log(`[AI-AGENT] Result:`, res);
    if (res && res.analysis) {
      const statusText = res.status_message || (
        res.source === 'BRStock Technical Engine'
          ? 'Live model is temporarily unavailable, so BRStock generated this report with its built-in technical engine.'
          : ''
      );
      content.innerHTML = `
        <div style="margin-bottom: 12px; font-size: 11px; color: var(--accent-blue); opacity: 0.9;">
          Analysis source: ${res.source || 'BRStock Analysis'}${statusText ? ` · ${statusText}` : ''}
        </div>
        <div style="white-space: pre-wrap; line-height: 1.6;">${res.analysis}</div>
      `;
    } else {
      content.innerHTML = `<span style="color:var(--text-secondary);">Live model is temporarily unavailable. Please try again shortly.</span>`;
    }
  } catch (err) {
    console.error('AI Analysis Fetch Error:', err);
    content.innerHTML = `<span style="color:var(--text-secondary);">Live model is temporarily unavailable. Please try again shortly.</span>`;
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
  const input = document.getElementById('top-add-stock-input');
  if (input) input.value = '';
  addStock(ticker);
}

async function handleTopAddStockClick() {
  console.log('[WATCHLIST] Top add button clicked', {
    hasToken: Boolean(authToken),
    currentPage
  });
  if (!authToken) {
    showAuthModal();
    return;
  }

  const input = document.getElementById('top-add-stock-input');
  const symbol = (input?.value || '').trim().toUpperCase();
  if (!symbol) {
    input?.focus();
    const statusEl = document.getElementById('add-stock-status');
    if (statusEl) statusEl.textContent = 'Type a ticker first, then click Add Stock.';
    return;
  }

  await addStock(symbol);
  if (input) input.value = '';
}

async function addStockFromInput(inputId = 'top-add-stock-input') {
  const input = document.getElementById(inputId);
  if (!input) {
    console.warn('[WATCHLIST] addStockFromInput could not find input', { inputId });
    return;
  }
  const symbol = input.value.toUpperCase().trim();
  if (!symbol) return;

  await addStock(symbol);
  input.value = '';
}

async function addStock(symbol) {
  symbol = symbol.toUpperCase().trim();
  console.log('[WATCHLIST] addStock start', { symbol, hasToken: Boolean(authToken) });
  if (!authToken) {
    alert("Please login to add stocks to your personal watchlist.");
    showAuthModal();
    return;
  }
  const statusEl = document.getElementById('add-stock-status');
  if (statusEl) statusEl.textContent = `⏳ Adding ${symbol}...`;

  const addResult = await apiFetch(`/api/stocks/watchlist/${symbol}`, { method: 'POST' });
  if (!addResult) {
    console.warn('[WATCHLIST] add watchlist failed', { symbol, error: apiFetch.lastError });
    if (statusEl) statusEl.textContent = `❌ Error adding ${symbol} to watchlist`;
    return;
  }

  if (!watchlist.includes(symbol)) watchlist.push(symbol);
  if (currentPage === 'dashboard') renderDashboard();
  if (statusEl) statusEl.textContent = `✅ ${symbol} added. Fetching chart data...`;

  const fetchResult = await apiFetch(`/api/stocks/${symbol}/fetch`, { method: 'POST' });
  if (!fetchResult) {
    console.warn('[WATCHLIST] fetch stock data failed', { symbol, error: apiFetch.lastError });
    if (statusEl) statusEl.textContent = `⚠️ ${symbol} added, but data fetch failed.`;
    return;
  }
  if (fetchResult.cached && statusEl) {
    statusEl.textContent = `✅ ${symbol} added. Using cached market data.`;
  }

  await initWatchlist();
  await refreshSymbolData(symbol);

  if (statusEl) {
    statusEl.textContent = fetchResult.cached
      ? `✅ ${symbol} added from cached data.`
      : `✅ ${symbol} added to watchlist.`;
  }
  console.log('[WATCHLIST] addStock success', { symbol, watchlist });

  if (currentPage === 'dashboard') renderDashboard();
  currentStock = symbol;
  if (currentPage !== 'dashboard') navigate('chart');
}

async function removeStock(symbol, event) {
  if (event) event.stopPropagation(); // Don't navigate to chart
  if (!authToken) {
    alert("Please login to manage your watchlist.");
    showAuthModal();
    return;
  }
  if (!confirm(`Remove ${symbol} from watchlist?`)) return;

  const removeResult = await apiFetch(`/api/stocks/watchlist/${symbol}`, { method: 'DELETE' });
  if (!removeResult) {
    alert(`Failed to remove ${symbol} from watchlist.`);
    return;
  }
  await initWatchlist();
  delete stockData[symbol];
  delete stockStats[symbol];
  renderDashboard();
}

async function persistWatchlistOrder() {
  if (!authToken) return;
  const result = await apiFetch('/api/stocks/watchlist/order', {
    method: 'PUT',
    body: JSON.stringify({ tickers: watchlist })
  });
  if (!result) {
    console.warn('[WATCHLIST] order save failed', { error: apiFetch.lastError, watchlist });
  }
}

async function moveWatchlistItem(symbol, direction, event) {
  if (event) event.stopPropagation();
  const idx = watchlist.indexOf(symbol);
  const nextIdx = idx + direction;
  if (idx < 0 || nextIdx < 0 || nextIdx >= watchlist.length) return;

  const next = [...watchlist];
  [next[idx], next[nextIdx]] = [next[nextIdx], next[idx]];
  watchlist = next;
  renderDashboard();
  await persistWatchlistOrder();
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
  console.warn('[AUTH] showAuthModal called', { hasToken: Boolean(authToken), currentPage });
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
    isLogin ? t('auth.loginTitle') : (isReg ? t('auth.registerTitle') : t('auth.resetTitle'));
  document.getElementById('auth-subtitle').textContent =
    isLogin ? t('auth.loginSubtitle') :
      (isReg ? t('auth.registerSubtitle') : t('auth.resetSubtitle'));

  document.getElementById('btn-auth-submit').textContent =
    isLogin ? t('auth.login') : (isReg ? t('auth.signUp') : t('auth.updatePassword'));

  document.getElementById('group-fullname').style.display = isReg ? 'block' : 'none';
  document.getElementById('group-pin').style.display = (isReg || isReset) ? 'block' : 'none';
  document.getElementById('group-new-password').style.display = isReset ? 'block' : 'none';

  // Repurpose password field for login/reg
  document.getElementById('auth-password').closest('.input-group').style.display = isReset ? 'none' : 'block';

  document.getElementById('auth-switch-text').textContent = isLogin ? t('auth.noAccount') : t('auth.backTo');
  document.getElementById('auth-switch-link').textContent = isLogin ? t('auth.signUp') : t('auth.login');
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
    errorEl.textContent = t('auth.requiredFields');
    errorEl.style.display = 'block';
    return;
  }

  errorEl.style.display = 'none';
  const btn = document.getElementById('btn-auth-submit');
  btn.disabled = true;
  btn.textContent = `⌛ ${t('auth.processing')}`;

  try {
    console.log('[AUTH] submit start', { mode: authMode, email });
    if (authMode === 'register') {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, full_name: fullName, reset_pin: pin })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || t('auth.registerFailed'));
      }
      authMode = 'login';
      updateAuthModeUI();
      errorEl.textContent = t('auth.registerSuccess');
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
        throw new Error(err.detail || t('auth.resetFailed'));
      }
      authMode = 'login';
      updateAuthModeUI();
      alert(t('auth.resetSuccess'));
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
      throw new Error(err.detail || t('auth.invalidLogin'));
    }

    const data = await res.json();
    authToken = data.access_token;
    localStorage.setItem('brstock_token', authToken);
    console.log('[AUTH] login success', { email, hasToken: Boolean(authToken) });

    hideAuthModal();
    location.reload(); // Refresh fully to update all states

  } catch (err) {
    console.warn('[AUTH] submit failed', { mode: authMode, email, error: err.message });
    errorEl.textContent = err.message;
    errorEl.className = 'auth-error';
    errorEl.style.display = 'block';
  } finally {
    btn.disabled = false;
    btn.textContent = authMode === 'login' ? t('auth.login') : (authMode === 'register' ? t('auth.signUp') : t('auth.updatePassword'));
  }
}

// ===== Strategy Functions =====
let strategies = [];
let selectedStrategyId = null;

async function loadStrategies() {
  const container = document.getElementById('strategy-list-container') || document.getElementById('strategy-list');
  if (!container) {
    console.warn('Strategy container not found, skipping load.');
    return;
  }

  if (!authToken) {
    container.innerHTML = `
      <div style="text-align: center; padding: 30px 20px;">
        <div style="font-size: 24px; margin-bottom: 12px;">🔐</div>
        <div style="color: var(--text-muted); font-size: 13px; margin-bottom: 16px;">
          Please login to create and manage your strategies.
        </div>
        <button class="btn btn-primary" onclick="showAuthModal()">Login / Register</button>
      </div>
    `;
    const detailContent = document.getElementById('strategy-detail-content');
    if (detailContent) {
      detailContent.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-muted);">Login to view strategy details</div>';
    }
    return;
  }

  try {
    const res = await apiFetch('/api/strategies');
    // 修正：后端直接返回数组
    strategies = Array.isArray(res) ? res : (res.strategies || []);
    renderStrategyList();
  } catch (e) {
    console.error('Failed to load strategies:', e);
    container.innerHTML = `<div style="color: var(--text-muted); font-size: 13px; padding: 20px; text-align: center;">Failed to load strategies</div>`;
  }
}

function renderStrategyList() {
  const container = document.getElementById('strategy-list-container');
  if (!container) return;

  if (!strategies || strategies.length === 0) {
    container.innerHTML = `
      <div style="color:var(--text-muted); text-align:center; padding:40px; grid-column: 1/-1;">
        <div style="font-size:32px; margin-bottom:12px;">📭</div>
        <p>No strategies found. Create your first one!</p>
      </div>`;
    renderStrategyDetail(null);
    return;
  }

  if (!selectedStrategyId || !strategies.some(s => String(s.id) === String(selectedStrategyId))) {
    selectedStrategyId = strategies[0].id;
  }

  container.innerHTML = strategies.map(s => {
    const isSystem = s.id && String(s.id).startsWith('system_');
    const id = String(s.id);
    const active = String(selectedStrategyId) === id;
    const safeId = id.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
    return `
      <div class="strategy-item ${active ? 'active' : ''}" onclick="selectStrategy('${safeId}')">
        <div>
          <div style="display:flex; justify-content:space-between; gap:12px; margin-bottom:10px;">
            <div class="strategy-item-name">${escapeHtml(s.name)}</div>
            <div style="font-size:10px; padding:2px 6px; background:rgba(0,212,255,0.1); color:var(--accent-blue); border-radius:4px; height:max-content;">${isSystem ? 'SYSTEM' : 'ACTIVE'}</div>
          </div>
          <div class="strategy-item-desc" style="min-height:34px;">
            ${escapeHtml(s.description || 'No description provided.')}
          </div>
        </div>
        <div class="strategy-item-actions">
          <button class="btn btn-ghost" style="padding:4px 8px; font-size:11px;" onclick="event.stopPropagation(); selectedStrategyId='${safeId}'; renderStrategyList(); runBacktestWithStrategy('${safeId}')">Configure Test</button>
          ${isSystem ? '' : `<button class="btn btn-ghost" style="padding:4px 8px; font-size:11px;" onclick="event.stopPropagation(); deleteStrategy(${Number(s.id)})">Delete</button>`}
        </div>
      </div>
    `;
  }).join('');

  renderStrategyDetail(strategies.find(s => String(s.id) === String(selectedStrategyId)));
}

function renderStrategyDetail(strategy) {
  const detailContent = document.getElementById('strategy-detail-content');
  if (!detailContent) return;

  if (!strategy) {
    detailContent.className = 'strategy-detail-card strategy-detail-empty';
    detailContent.innerHTML = 'Select a strategy to review configuration and launch a backtest.';
    return;
  }

  detailContent.className = 'strategy-detail-card';
  const strategyId = String(strategy.id);
  const baseStrategyId = getStrategyBaseId(strategy);
  const buyConds = strategy.buy_conditions || {};
  const sellConds = strategy.sell_conditions || {};
  const params = strategy.params || {};
  const initialCapital = Number(params.initial_capital || (strategy.type === 'option' ? 50000 : 100000));
  const isSystem = strategyId.startsWith('system_');
  const safeId = strategyId.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
  const tags = [
    buyConds.rsi_enabled ? `Buy: RSI < ${buyConds.rsi_below}` : '',
    sellConds.rsi_enabled ? `Sell: RSI > ${sellConds.rsi_above}` : '',
    buyConds.sma_cross_up ? 'Buy: SMA Golden Cross' : '',
    sellConds.sma_cross_down ? 'Sell: SMA Death Cross' : '',
    buyConds.macd_cross_up ? 'Buy: MACD Golden Cross' : '',
    sellConds.macd_cross_down ? 'Sell: MACD Death Cross' : '',
    buyConds.bb_lower ? 'Buy: Lower Bollinger Band' : '',
    sellConds.bb_upper ? 'Sell: Upper Bollinger Band' : '',
    params.stop_loss ? `Stop Loss: ${params.stop_loss}%` : '',
    params.take_profit ? `Take Profit: ${params.take_profit}%` : ''
  ].filter(Boolean);

  detailContent.innerHTML = `
    <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start; margin-bottom:12px;">
      <div>
        <div class="strategy-detail-title">${escapeHtml(strategy.name)}</div>
        <div class="strategy-detail-desc">${escapeHtml(strategy.description || 'No description')}</div>
      </div>
      <span class="indicator-chip">${isSystem ? 'SYSTEM' : 'CUSTOM'}</span>
    </div>

    <div class="strategy-condition-section">
      <div class="strategy-condition-title">Logic</div>
      <div class="strategy-condition-list">
        ${tags.length ? tags.map(tag => `<span class="strategy-condition-tag">${escapeHtml(tag)}</span>`).join('') : '<span style="color:var(--text-muted);font-size:12px">Uses strategy defaults in the backtest engine.</span>'}
      </div>
    </div>

    <div class="strategy-condition-section">
      <div class="strategy-condition-title" style="color:var(--accent-blue)">Quick Test Setup</div>
      <div class="strategy-config-grid">
        <div class="input-group">
          <label>Ticker</label>
          <input id="strategy-test-ticker" value="${escapeHtml(params.saved_ticker || 'QQQ')}" placeholder="QQQ">
        </div>
        <div class="input-group">
          <label>Capital</label>
          <input id="strategy-test-capital" type="number" value="${initialCapital}">
        </div>
        <div class="input-group">
          <label>Period</label>
          <select id="strategy-test-period">
            <option value="1y" ${params.saved_period === '1y' ? 'selected' : ''}>1 Year</option>
            <option value="2y" ${params.saved_period === '2y' ? 'selected' : ''}>2 Years</option>
            <option value="5y" ${params.saved_period === '5y' ? 'selected' : ''}>5 Years</option>
            <option value="10y" ${params.saved_period === '10y' ? 'selected' : ''}>10 Years</option>
            <option value="20y" ${params.saved_period === '20y' ? 'selected' : ''}>20 Years</option>
          </select>
        </div>
        <div class="input-group">
          <label>Next Step</label>
          <select id="strategy-test-mode">
            <option value="configure">Open in Backtest</option>
          </select>
        </div>
      </div>
    </div>

    ${renderStrategyQuickParams(baseStrategyId, params)}

    <div class="strategy-detail-actions">
      <button class="btn btn-primary" onclick="runBacktestWithStrategy('${safeId}')">Open Configured Backtest</button>
      <button class="btn btn-ghost" onclick="saveConfiguredStrategy('${safeId}')">Save as My Strategy</button>
      ${isSystem ? '' : `<button class="btn btn-ghost" onclick="editStrategy(${Number(strategy.id)})">Edit Strategy</button>`}
    </div>
  `;
}

function getStrategyBaseId(strategy) {
  return String((strategy?.params || {}).base_strategy_id || strategy?.id || '');
}

function renderStrategyQuickParams(strategyId, params = {}) {
  if (isBuyHoldStrategy(strategyId)) {
    const assets = params.assets || params.core_assets || [{ ticker: 'QQQ', weight: 1 }];
    return `
      <div class="strategy-condition-section">
        <div class="strategy-condition-title" style="color:var(--accent-blue)">Holdings</div>
        <div class="strategy-config-grid">
          <div class="input-group"><label>Invested %</label><input id="strategy-buyhold-allocation" type="number" value="${Number(params.allocation_pct ?? 1) * 100}"></div>
          <div class="input-group"><label>Rebalance</label><select id="strategy-buyhold-rebalance"><option value="none" ${params.rebalance === 'none' ? 'selected' : ''}>None</option><option value="monthly" ${params.rebalance === 'monthly' ? 'selected' : ''}>Monthly</option><option value="quarterly" ${params.rebalance === 'quarterly' ? 'selected' : ''}>Quarterly</option><option value="annual" ${params.rebalance === 'annual' ? 'selected' : ''}>Annual</option></select></div>
          ${[1, 2, 3, 4, 5].map(i => `
            <div class="input-group"><label>Ticker ${i}</label><input id="strategy-buyhold-ticker-${i}" value="${escapeHtml(assets[i - 1]?.ticker || (i === 1 ? 'QQQ' : ''))}"></div>
            <div class="input-group"><label>Weight ${i} %</label><input id="strategy-buyhold-weight-${i}" type="number" value="${Number(assets[i - 1]?.weight ?? (i === 1 ? 1 : 0)) * 100}"></div>
          `).join('')}
        </div>
      </div>
    `;
  }

  if (isVerticalSpreadStrategy(strategyId)) {
    const bearish = strategyId === 'system_bear_put';
    const creditPut = strategyId === 'system_bull_put';
    return `
      <div class="strategy-condition-section">
        <div class="strategy-condition-title" style="color:var(--accent-blue)">Spread Defaults</div>
        <div class="strategy-config-grid">
          <div class="input-group"><label>DTE</label><input id="strategy-spread-dte" type="number" value="${params.dte_target ?? 40}"></div>
          <div class="input-group"><label>Width</label><input id="strategy-spread-width" type="number" value="${params.spread_width ?? 20}"></div>
          <div class="input-group"><label>Risk %</label><input id="strategy-spread-risk" type="number" value="${Number(params.risk_pct ?? 0.30) * 100}"></div>
          <div class="input-group"><label>Long Delta</label><input id="strategy-spread-long-delta" type="number" step="0.01" value="${params.long_delta_target ?? (bearish ? '-0.60' : creditPut ? '-0.10' : '0.60')}"></div>
          <div class="input-group"><label>Short Delta</label><input id="strategy-spread-short-delta" type="number" step="0.01" value="${params.short_delta_target ?? (bearish || creditPut ? '-0.30' : '0.30')}"></div>
          <div class="input-group"><label>Open Interval</label><input id="strategy-spread-open-interval" type="number" value="${params.open_interval_days ?? 10}"></div>
        </div>
      </div>
    `;
  }

  if (strategyId === 'system_leaps') {
    return `
      <div class="strategy-condition-section">
        <div class="strategy-condition-title" style="color:var(--accent-blue)">LEAPS Defaults</div>
        <div class="strategy-config-grid">
          <div class="input-group"><label>Capital Use %</label><input id="strategy-leaps-capital" type="number" value="${Number(params.capital_utilization ?? 0.30) * 100}"></div>
          <div class="input-group"><label>Target Delta</label><input id="strategy-leaps-delta" type="number" step="0.01" value="${params.delta_target ?? 0.80}"></div>
          <div class="input-group"><label>DTE</label><input id="strategy-leaps-dte" type="number" value="${params.dte_target ?? 365}"></div>
          <div class="input-group"><label>Roll DTE</label><input id="strategy-leaps-roll" type="number" value="${params.roll_dte ?? 60}"></div>
        </div>
      </div>
    `;
  }

  if (strategyId === 'system_portfolio_combo') {
    return `
      <div class="strategy-condition-section">
        <div class="strategy-condition-title" style="color:var(--accent-blue)">Portfolio Defaults</div>
        <div class="strategy-config-grid">
          <div class="input-group"><label>Core %</label><input id="strategy-portfolio-core" type="number" value="${Number(params.core_pct ?? 0.70) * 100}"></div>
          <div class="input-group"><label>Options %</label><input id="strategy-portfolio-options" type="number" value="${Number(params.options_pct ?? 0.30) * 100}"></div>
          <div class="input-group"><label>Core ETF 1</label><input id="strategy-portfolio-core-1" value="${escapeHtml(params.core_assets?.[0]?.ticker || 'QQQ')}"></div>
          <div class="input-group"><label>Core ETF 2</label><input id="strategy-portfolio-core-2" value="${escapeHtml(params.core_assets?.[1]?.ticker || 'VOO')}"></div>
          <div class="input-group"><label>Option Strategy</label><select id="strategy-portfolio-option-strategy"><option value="system_bull_call" ${params.option_strategy_id === 'system_bull_call' ? 'selected' : ''}>Bull Call</option><option value="system_bull_put" ${params.option_strategy_id === 'system_bull_put' ? 'selected' : ''}>Bull Put</option><option value="system_leaps" ${params.option_strategy_id === 'system_leaps' ? 'selected' : ''}>LEAPS</option></select></div>
          <div class="input-group"><label>Option Ticker</label><input id="strategy-portfolio-option-ticker" value="${escapeHtml(params.option_ticker || 'QQQ')}"></div>
        </div>
      </div>
    `;
  }

  return '';
}


function selectStrategy(id) {
  selectedStrategyId = id;
  const strategy = strategies.find(s => String(s.id) === String(id));
  if (!strategy) return;

  renderStrategyList();
}

function readNumberInput(id, fallback) {
  const value = parseFloat(document.getElementById(id)?.value);
  return Number.isFinite(value) ? value : fallback;
}

function collectConfiguredStrategyParams(strategy) {
  const baseStrategyId = getStrategyBaseId(strategy);
  const params = {
    ...(strategy?.params || {}),
    base_strategy_id: baseStrategyId,
    saved_ticker: document.getElementById('strategy-test-ticker')?.value?.trim().toUpperCase() || 'QQQ',
    saved_period: document.getElementById('strategy-test-period')?.value || '1y',
    initial_capital: readNumberInput('strategy-test-capital', Number(strategy?.params?.initial_capital || 100000))
  };

  if (isVerticalSpreadStrategy(baseStrategyId)) {
    params.dte_target = readNumberInput('strategy-spread-dte', 40);
    params.spread_width = readNumberInput('strategy-spread-width', 20);
    params.risk_pct = readNumberInput('strategy-spread-risk', 30) / 100;
    params.long_delta_target = readNumberInput('strategy-spread-long-delta', baseStrategyId === 'system_bear_put' ? -0.60 : 0.60);
    params.short_delta_target = readNumberInput('strategy-spread-short-delta', baseStrategyId === 'system_bear_put' ? -0.30 : 0.30);
    params.open_interval_days = readNumberInput('strategy-spread-open-interval', 10);
  } else if (baseStrategyId === 'system_leaps') {
    params.capital_utilization = readNumberInput('strategy-leaps-capital', 30) / 100;
    params.delta_target = readNumberInput('strategy-leaps-delta', 0.80);
    params.dte_target = readNumberInput('strategy-leaps-dte', 365);
    params.roll_dte = readNumberInput('strategy-leaps-roll', 60);
  } else if (baseStrategyId === 'system_portfolio_combo') {
    params.core_pct = readNumberInput('strategy-portfolio-core', 70) / 100;
    params.options_pct = readNumberInput('strategy-portfolio-options', 30) / 100;
    params.core_assets = [
      { ticker: (document.getElementById('strategy-portfolio-core-1')?.value || 'QQQ').trim().toUpperCase(), weight: 0.5 },
      { ticker: (document.getElementById('strategy-portfolio-core-2')?.value || 'VOO').trim().toUpperCase(), weight: 0.5 }
    ];
    params.option_strategy_id = document.getElementById('strategy-portfolio-option-strategy')?.value || 'system_bull_call';
    params.option_ticker = (document.getElementById('strategy-portfolio-option-ticker')?.value || params.saved_ticker || 'QQQ').trim().toUpperCase();
  } else if (baseStrategyId === 'system_buy_hold') {
    params.allocation_pct = readNumberInput('strategy-buyhold-allocation', 100) / 100;
    params.rebalance = document.getElementById('strategy-buyhold-rebalance')?.value || 'none';
    params.assets = [1, 2, 3, 4, 5].map(i => ({
      ticker: (document.getElementById(`strategy-buyhold-ticker-${i}`)?.value || '').trim().toUpperCase(),
      weight: readNumberInput(`strategy-buyhold-weight-${i}`, 0) / 100
    })).filter(asset => asset.ticker && asset.weight > 0);
  }

  return params;
}

async function saveConfiguredStrategy(strategyId) {
  if (!authToken) {
    showAuthModal();
    return;
  }

  const strategy = strategies.find(s => String(s.id) === String(strategyId || selectedStrategyId));
  if (!strategy) return;

  const params = collectConfiguredStrategyParams(strategy);
  const defaultName = strategy.name.startsWith('My ')
    ? strategy.name
    : `My ${strategy.name.replace(/^System\s+|^Option Strategy:\s+|^Option:\s+|^Portfolio:\s+/i, '')}`;
  const name = prompt('Name this saved strategy:', defaultName);
  if (!name || !name.trim()) return;

  try {
    await apiFetch('/api/strategies', {
      method: 'POST',
      body: JSON.stringify({
        name: name.trim(),
        description: `${strategy.description || 'Saved configured strategy'} · ${params.saved_ticker} · ${params.saved_period}`,
        buy_conditions: strategy.buy_conditions || {},
        sell_conditions: strategy.sell_conditions || {},
        params
      })
    });
    await loadStrategies();
  } catch (e) {
    alert('Failed to save strategy: ' + e.message);
  }
}

function handleNewStrategyClick() {
  if (!authToken) {
    showAuthModal();
    return;
  }
  showCreateStrategyModal();
}

function showCreateStrategyModal() {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'strategy-modal';
  overlay.innerHTML = `
    <div class="modal-content">
      <div class="modal-header">
        <div class="modal-title">Create New Strategy</div>
        <button class="modal-close" onclick="closeStrategyModal()">✕</button>
      </div>
      
      <div class="form-row">
        <label class="form-label">Strategy Name</label>
        <input type="text" id="strategy-name" class="form-input" placeholder="e.g., RSI Reversal Strategy">
      </div>
      
      <div class="form-row">
        <label class="form-label">Description (optional)</label>
        <input type="text" id="strategy-desc" class="form-input" placeholder="Brief description...">
      </div>
      
      <div style="background:var(--bg-primary);padding:16px;border-radius:8px;margin-bottom:16px">
        <div style="font-size:14px;font-weight:600;margin-bottom:12px;color:var(--accent-green)">Buy Conditions</div>
        <div class="checkbox-group">
          <input type="checkbox" id="buy-rsi-enable">
          <label for="buy-rsi-enable">RSI Oversold</label>
          <input type="number" id="buy-rsi-value" placeholder="Below (e.g., 30)" style="width:80px;margin-left:8px;padding:4px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:4px;color:var(--text-primary)">
        </div>
        <div class="checkbox-group">
          <input type="checkbox" id="buy-macd-enable">
          <label for="buy-macd-enable">MACD Golden Cross (MACD crosses above Signal)</label>
        </div>
      </div>
      
      <div style="background:var(--bg-primary);padding:16px;border-radius:8px;margin-bottom:16px">
        <div style="font-size:14px;font-weight:600;margin-bottom:12px;color:var(--accent-red)">Sell Conditions</div>
        <div class="checkbox-group">
          <input type="checkbox" id="sell-rsi-enable">
          <label for="sell-rsi-enable">RSI Overbought</label>
          <input type="number" id="sell-rsi-value" placeholder="Above (e.g., 70)" style="width:80px;margin-left:8px;padding:4px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:4px;color:var(--text-primary)">
        </div>
        <div class="checkbox-group">
          <input type="checkbox" id="sell-macd-enable">
          <label for="sell-macd-enable">MACD Death Cross (MACD crosses below Signal)</label>
        </div>
      </div>
      
      <div class="form-row">
        <label class="form-label">Stop Loss % (0 = disabled)</label>
        <input type="number" id="stop-loss" class="form-input" value="0" min="0" max="50">
      </div>
      
      <div class="form-row">
        <label class="form-label">Take Profit % (0 = disabled)</label>
        <input type="number" id="take-profit" class="form-input" value="0" min="0" max="100">
      </div>
      
      <button class="btn btn-primary" onclick="saveStrategy()" style="width:100%;margin-top:8px">Create Strategy</button>
    </div>
  `;
  document.body.appendChild(overlay);
}

function closeStrategyModal() {
  const modal = document.getElementById('strategy-modal');
  if (modal) modal.remove();
}

async function saveStrategy() {
  const name = document.getElementById('strategy-name').value.trim();
  const desc = document.getElementById('strategy-desc').value.trim();

  if (!name) {
    alert('Please enter a strategy name');
    return;
  }

  const buy_conditions = {
    rsi_enabled: document.getElementById('buy-rsi-enable').checked,
    rsi_below: parseFloat(document.getElementById('buy-rsi-value').value) || 30,
    macd_cross_up: document.getElementById('buy-macd-enable').checked
  };

  const sell_conditions = {
    rsi_enabled: document.getElementById('sell-rsi-enable').checked,
    rsi_above: parseFloat(document.getElementById('sell-rsi-value').value) || 70,
    macd_cross_down: document.getElementById('sell-macd-enable').checked
  };

  const params = {
    stop_loss: parseFloat(document.getElementById('stop-loss').value) || 0,
    take_profit: parseFloat(document.getElementById('take-profit').value) || 0
  };

  try {
    const res = await apiFetch('/api/strategies', {
      method: 'POST',
      body: JSON.stringify({ name, description: desc, buy_conditions, sell_conditions, params })
    });
    closeStrategyModal();
    await loadStrategies();
    alert('Strategy created successfully!');
  } catch (e) {
    alert('Failed to create strategy: ' + e.message);
  }
}

async function deleteStrategy(id) {
  if (!confirm('Are you sure you want to delete this strategy?')) return;
  try {
    await apiFetch(`/api/strategies/${id}`, { method: 'DELETE' });
    if (selectedStrategyId === id) selectedStrategyId = null;
    await loadStrategies();
  } catch (e) {
    alert('Failed to delete strategy: ' + e.message);
  }
}

function editStrategy(id) {
  const strategy = strategies.find(s => s.id === id);
  if (!strategy) return;
  alert('Edit functionality - you can modify the strategy using the same modal');
  showCreateStrategyModal();
}

async function runBacktestWithStrategy(strategyId) {
  const quick = {
    ticker: document.getElementById('strategy-test-ticker')?.value?.trim().toUpperCase() || 'QQQ',
    capital: document.getElementById('strategy-test-capital')?.value || '',
    period: document.getElementById('strategy-test-period')?.value || '1y',
    spreadDte: document.getElementById('strategy-spread-dte')?.value,
    spreadWidth: document.getElementById('strategy-spread-width')?.value,
    spreadRisk: document.getElementById('strategy-spread-risk')?.value,
    spreadLongDelta: document.getElementById('strategy-spread-long-delta')?.value,
    spreadShortDelta: document.getElementById('strategy-spread-short-delta')?.value,
    spreadOpenInterval: document.getElementById('strategy-spread-open-interval')?.value,
    leapsCapital: document.getElementById('strategy-leaps-capital')?.value,
    leapsDelta: document.getElementById('strategy-leaps-delta')?.value,
    leapsDte: document.getElementById('strategy-leaps-dte')?.value,
    leapsRoll: document.getElementById('strategy-leaps-roll')?.value,
    portfolioCore: document.getElementById('strategy-portfolio-core')?.value,
    portfolioOptions: document.getElementById('strategy-portfolio-options')?.value,
    portfolioCore1: document.getElementById('strategy-portfolio-core-1')?.value,
    portfolioCore2: document.getElementById('strategy-portfolio-core-2')?.value,
    portfolioOptionStrategy: document.getElementById('strategy-portfolio-option-strategy')?.value,
    portfolioOptionTicker: document.getElementById('strategy-portfolio-option-ticker')?.value,
    buyHoldAllocation: document.getElementById('strategy-buyhold-allocation')?.value,
    buyHoldRebalance: document.getElementById('strategy-buyhold-rebalance')?.value,
    buyHoldTicker1: document.getElementById('strategy-buyhold-ticker-1')?.value,
    buyHoldWeight1: document.getElementById('strategy-buyhold-weight-1')?.value,
    buyHoldTicker2: document.getElementById('strategy-buyhold-ticker-2')?.value,
    buyHoldWeight2: document.getElementById('strategy-buyhold-weight-2')?.value,
    buyHoldTicker3: document.getElementById('strategy-buyhold-ticker-3')?.value,
    buyHoldWeight3: document.getElementById('strategy-buyhold-weight-3')?.value,
    buyHoldTicker4: document.getElementById('strategy-buyhold-ticker-4')?.value,
    buyHoldWeight4: document.getElementById('strategy-buyhold-weight-4')?.value,
    buyHoldTicker5: document.getElementById('strategy-buyhold-ticker-5')?.value,
    buyHoldWeight5: document.getElementById('strategy-buyhold-weight-5')?.value
  };

  await navigate('backtest');

  const setValue = (id, value) => {
    const el = document.getElementById(id);
    if (el && value !== undefined && value !== null && value !== '') el.value = value;
  };

  setValue('backtest-strategy-select', strategyId);
  setValue('backtest-ticker', quick.ticker);
  setValue('backtest-capital', quick.capital);
  setValue('backtest-period', quick.period);
  updateBacktestParamVisibility();
  updateBacktestDateVisibility();

  const baseStrategyId = resolveStrategyBaseId(strategyId);
  if (isVerticalSpreadStrategy(strategyId)) {
    setValue('spread-dte', quick.spreadDte);
    setValue('spread-width', quick.spreadWidth);
    setValue('spread-risk-pct', quick.spreadRisk);
    setValue('spread-long-delta', quick.spreadLongDelta);
    setValue('spread-short-delta', quick.spreadShortDelta);
    setValue('spread-open-interval', quick.spreadOpenInterval);
  } else if (baseStrategyId === 'system_leaps') {
    setValue('leaps-capital-utilization', quick.leapsCapital);
    setValue('leaps-delta-target', quick.leapsDelta);
    setValue('leaps-dte-target', quick.leapsDte);
    setValue('leaps-roll-dte', quick.leapsRoll);
  } else if (baseStrategyId === 'system_portfolio_combo') {
    setValue('portfolio-core-pct', quick.portfolioCore);
    setValue('portfolio-options-pct', quick.portfolioOptions);
    setValue('portfolio-core-ticker-1', quick.portfolioCore1);
    setValue('portfolio-core-ticker-2', quick.portfolioCore2);
    setValue('portfolio-option-strategy', quick.portfolioOptionStrategy);
    setValue('portfolio-option-ticker', quick.portfolioOptionTicker || quick.ticker);
    updateBacktestParamVisibility();
  } else if (baseStrategyId === 'system_buy_hold') {
    setValue('buyhold-allocation-pct', quick.buyHoldAllocation);
    setValue('buyhold-rebalance', quick.buyHoldRebalance);
    setValue('buyhold-ticker-1', quick.buyHoldTicker1 || quick.ticker);
    setValue('buyhold-weight-1', quick.buyHoldWeight1);
    setValue('buyhold-ticker-2', quick.buyHoldTicker2);
    setValue('buyhold-weight-2', quick.buyHoldWeight2);
    setValue('buyhold-ticker-3', quick.buyHoldTicker3);
    setValue('buyhold-weight-3', quick.buyHoldWeight3);
    setValue('buyhold-ticker-4', quick.buyHoldTicker4);
    setValue('buyhold-weight-4', quick.buyHoldWeight4);
    setValue('buyhold-ticker-5', quick.buyHoldTicker5);
    setValue('buyhold-weight-5', quick.buyHoldWeight5);
  }
}

// ===== Backtesting Functions =====
let backtestHistory = [];
let currentBacktestResult = null;
let backtestStrategies = [];

async function loadBacktestPage() {
  // Set default dates
  const today = new Date();
  const oneYearAgo = new Date();
  oneYearAgo.setFullYear(today.getFullYear() - 1);

  const startInput = document.getElementById('backtest-start-date');
  const endInput = document.getElementById('backtest-end-date');

  if (startInput && endInput) {
    startInput.value = oneYearAgo.toISOString().split('T')[0];
    endInput.value = today.toISOString().split('T')[0];
  }
  updateBacktestDateVisibility();
  setupPortfolioTickerSync();

  if (!authToken) {
    const placeholder = document.getElementById('backtest-placeholder');
    if (placeholder) {
      placeholder.innerHTML = `
        <div style="text-align: center; padding: 60px 20px; color: var(--text-muted);">
          <div style="font-size: 48px; margin-bottom: 16px;">🔐</div>
          <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Login Required</div>
          <div style="font-size: 13px; line-height: 1.6; margin-bottom: 20px;">
            Please login to run backtests and view history.
          </div>
          <button class="btn btn-primary" onclick="showAuthModal()">Login / Register</button>
        </div>
      `;
      placeholder.style.display = 'block';
    }
    const resultCard = document.getElementById('backtest-result-card');
    if (resultCard) resultCard.style.display = 'none';
    return;
  }

  // Load strategies for dropdown
  await loadStrategiesForBacktest();

  // Load backtest history
  await loadBacktestHistory();
}

async function loadStrategiesForBacktest() {
  try {
    const res = await apiFetch('/api/strategies');
    const select = document.getElementById('backtest-strategy-select');
    if (!select) return;

    select.innerHTML = '<option value="">-- Select a strategy --</option>';
    const strats = Array.isArray(res) ? res : (res.strategies || []);
    backtestStrategies = strats;
    strats.forEach(s => {
      select.innerHTML += `<option value="${s.id}">${s.name}</option>`;
    });
    updateBacktestParamVisibility();
  } catch (e) {
    console.error('Failed to load strategies:', e);
  }
}

function isVerticalSpreadStrategy(strategyId) {
  return ['system_bull_call', 'system_bear_put', 'system_bull_put'].includes(resolveStrategyBaseId(strategyId));
}

function isPortfolioStrategy(strategyId) {
  return resolveStrategyBaseId(strategyId) === 'system_portfolio_combo';
}

function isBuyHoldStrategy(strategyId) {
  return resolveStrategyBaseId(strategyId) === 'system_buy_hold';
}

function resolveStrategyBaseId(strategyId) {
  const id = String(strategyId || '');
  const source = [...(strategies || []), ...(backtestStrategies || [])];
  const found = source.find(s => String(s.id) === id);
  return String(found?.params?.base_strategy_id || id);
}

function updateBacktestParamVisibility() {
  const select = document.getElementById('backtest-strategy-select');
  const panel = document.getElementById('vertical-spread-params');
  const leapsPanel = document.getElementById('leaps-params');
  const portfolioPanel = document.getElementById('portfolio-params');
  const buyHoldPanel = document.getElementById('buy-hold-params');
  if (!select || !panel || !leapsPanel || !portfolioPanel || !buyHoldPanel) return;

  const strategyId = select.value;
  const baseStrategyId = resolveStrategyBaseId(strategyId);
  const portfolioMode = isPortfolioStrategy(strategyId);
  const buyHoldMode = isBuyHoldStrategy(strategyId);
  const optionStrategyId = portfolioMode
    ? (document.getElementById('portfolio-option-strategy')?.value || 'system_bull_call')
    : baseStrategyId;
  const show = isVerticalSpreadStrategy(optionStrategyId);
  const showLeaps = optionStrategyId === 'system_leaps';
  portfolioPanel.style.display = portfolioMode ? 'block' : 'none';
  buyHoldPanel.style.display = buyHoldMode ? 'block' : 'none';
  panel.style.display = show ? 'block' : 'none';
  leapsPanel.style.display = showLeaps ? 'block' : 'none';
  if (!show) return;

  const longDelta = document.getElementById('spread-long-delta');
  const shortDelta = document.getElementById('spread-short-delta');
  const rsiMinWrap = document.getElementById('spread-rsi-min-wrap');
  const rsiMaxWrap = document.getElementById('spread-rsi-max-wrap');

  if (optionStrategyId === 'system_bull_call') {
    if (longDelta) longDelta.value = '0.60';
    if (shortDelta) shortDelta.value = '0.30';
    if (rsiMinWrap) rsiMinWrap.style.display = 'block';
    if (rsiMaxWrap) rsiMaxWrap.style.display = 'none';
  } else if (optionStrategyId === 'system_bear_put') {
    if (longDelta) longDelta.value = '-0.60';
    if (shortDelta) shortDelta.value = '-0.30';
    if (rsiMinWrap) rsiMinWrap.style.display = 'none';
    if (rsiMaxWrap) rsiMaxWrap.style.display = 'block';
  } else if (optionStrategyId === 'system_bull_put') {
    if (longDelta) longDelta.value = '-0.10';
    if (shortDelta) shortDelta.value = '-0.30';
    if (rsiMinWrap) rsiMinWrap.style.display = 'none';
    if (rsiMaxWrap) rsiMaxWrap.style.display = 'none';
  }
}

function updateBacktestDateVisibility() {
  const period = document.getElementById('backtest-period')?.value || '1y';
  const customDates = document.getElementById('backtest-custom-dates');
  if (customDates) {
    customDates.style.display = period === 'custom' ? 'flex' : 'none';
  }
}

function syncPortfolioOptionTickerDefault() {
  const topTickerEl = document.getElementById('backtest-ticker');
  const optionTickerEl = document.getElementById('portfolio-option-ticker');
  if (!topTickerEl || !optionTickerEl) return;

  const topTicker = (topTickerEl.value || 'QQQ').trim().toUpperCase();
  if (!optionTickerEl.value.trim() || optionTickerEl.dataset.autoDefault === 'true') {
    optionTickerEl.value = topTicker;
    optionTickerEl.dataset.autoDefault = 'true';
  }
}

function setupPortfolioTickerSync() {
  const topTickerEl = document.getElementById('backtest-ticker');
  const optionTickerEl = document.getElementById('portfolio-option-ticker');
  if (!topTickerEl || !optionTickerEl || optionTickerEl.dataset.syncBound === 'true') return;

  topTickerEl.addEventListener('input', syncPortfolioOptionTickerDefault);
  optionTickerEl.addEventListener('input', () => {
    optionTickerEl.dataset.autoDefault = 'false';
    if (!optionTickerEl.value.trim()) {
      optionTickerEl.dataset.autoDefault = 'true';
      syncPortfolioOptionTickerDefault();
    }
  });
  optionTickerEl.dataset.syncBound = 'true';
  syncPortfolioOptionTickerDefault();
}

function getVerticalSpreadParams(strategyId) {
  if (!isVerticalSpreadStrategy(strategyId)) return {};
  const baseStrategyId = resolveStrategyBaseId(strategyId);

  const numberValue = (id, fallback) => {
    const el = document.getElementById(id);
    const value = el ? parseFloat(el.value) : NaN;
    return Number.isFinite(value) ? value : fallback;
  };

  const params = {
    dte_target: numberValue('spread-dte', 40),
    spread_width: numberValue('spread-width', 20),
    risk_pct: numberValue('spread-risk-pct', 30) / 100,
    long_delta_target: numberValue('spread-long-delta', baseStrategyId === 'system_bear_put' ? -0.60 : 0.60),
    short_delta_target: numberValue('spread-short-delta', baseStrategyId === 'system_bear_put' ? -0.30 : 0.30),
    delta_tolerance: numberValue('spread-delta-tolerance', 0.15),
    fill_slippage: numberValue('spread-fill-slippage', 0.10),
    max_open_positions: numberValue('spread-max-open', 4),
    open_interval_days: numberValue('spread-open-interval', 10)
  };

  if (baseStrategyId === 'system_bull_call') {
    params.entry_rsi_min = numberValue('spread-entry-rsi-min', 50);
  } else if (baseStrategyId === 'system_bear_put') {
    params.entry_rsi_max = numberValue('spread-entry-rsi-max', 50);
  }

  return params;
}

function getLeapsParams(strategyId) {
  if (resolveStrategyBaseId(strategyId) !== 'system_leaps') return {};

  const numberValue = (id, fallback) => {
    const el = document.getElementById(id);
    const value = el ? parseFloat(el.value) : NaN;
    return Number.isFinite(value) ? value : fallback;
  };

  return {
    capital_utilization: numberValue('leaps-capital-utilization', 30) / 100,
    delta_target: numberValue('leaps-delta-target', 0.80),
    dte_target: numberValue('leaps-dte-target', 365),
    roll_dte: numberValue('leaps-roll-dte', 60),
    fill_slippage: numberValue('leaps-fill-slippage', 0.10)
  };
}

function getBacktestParams(strategyId) {
  if (isBuyHoldStrategy(strategyId)) {
    const numberValue = (id, fallback) => {
      const el = document.getElementById(id);
      const value = el ? parseFloat(el.value) : NaN;
      return Number.isFinite(value) ? value : fallback;
    };
    const textValue = (id, fallback = '') => {
      const value = document.getElementById(id)?.value?.trim();
      return value || fallback;
    };
    const allocationPct = numberValue('buyhold-allocation-pct', 100);
    const assets = [1, 2, 3, 4, 5].map(i => ({
      ticker: textValue(`buyhold-ticker-${i}`).toUpperCase(),
      weight_pct: numberValue(`buyhold-weight-${i}`, 0)
    })).filter(asset => asset.ticker && asset.weight_pct > 0);
    const totalWeightPct = assets.reduce((sum, asset) => sum + asset.weight_pct, 0);
    if (allocationPct > 100) throw new Error('Invested capital cannot exceed 100%.');
    if (totalWeightPct > 100) throw new Error(`Buy & Hold weights total ${totalWeightPct.toFixed(1)}%. Please keep holdings at or below 100%.`);

    return {
      allocation_pct: allocationPct / 100,
      rebalance: document.getElementById('buyhold-rebalance')?.value || 'none',
      assets: assets.map(asset => ({ ticker: asset.ticker, weight: asset.weight_pct / 100 }))
    };
  }

  if (isPortfolioStrategy(strategyId)) {
    const numberValue = (id, fallback) => {
      const el = document.getElementById(id);
      const value = el ? parseFloat(el.value) : NaN;
      return Number.isFinite(value) ? value : fallback;
    };
    const textValue = (id, fallback) => {
      const value = document.getElementById(id)?.value?.trim();
      return value || fallback;
    };
    const optionStrategyId = document.getElementById('portfolio-option-strategy')?.value || 'system_bull_call';
    syncPortfolioOptionTickerDefault();
    const optionTicker = textValue('portfolio-option-ticker', textValue('backtest-ticker', 'QQQ')).toUpperCase();
    const corePct = numberValue('portfolio-core-pct', 70);
    const optionsPct = numberValue('portfolio-options-pct', 30);
    const coreWeight1 = numberValue('portfolio-core-weight-1', 50);
    const coreWeight2 = numberValue('portfolio-core-weight-2', 50);
    if (corePct + optionsPct > 100) throw new Error(`Portfolio sleeves total ${(corePct + optionsPct).toFixed(1)}%. Please keep Core + Options at or below 100%.`);
    if (coreWeight1 + coreWeight2 > 100) throw new Error(`Core ETF weights total ${(coreWeight1 + coreWeight2).toFixed(1)}%. Please keep holdings at or below 100%.`);
    return {
      core_pct: corePct / 100,
      options_pct: optionsPct / 100,
      rebalance: document.getElementById('portfolio-rebalance')?.value || 'quarterly',
      core_assets: [
        {
          ticker: textValue('portfolio-core-ticker-1', 'QQQ').toUpperCase(),
          weight: coreWeight1 / 100
        },
        {
          ticker: textValue('portfolio-core-ticker-2', 'VOO').toUpperCase(),
          weight: coreWeight2 / 100
        }
      ],
      option_ticker: optionTicker,
      option_strategy_id: optionStrategyId,
      option_params: {
        ...getVerticalSpreadParams(optionStrategyId),
        ...getLeapsParams(optionStrategyId)
      }
    };
  }
  return {
    ...getVerticalSpreadParams(strategyId),
    ...getLeapsParams(strategyId)
  };
}

async function loadBacktestHistory() {
  try {
    const res = await apiFetch('/api/backtest/history');
    backtestHistory = res.history || [];
    renderBacktestHistory();
  } catch (e) {
    console.error('Failed to load backtest history:', e);
  }
}

function renderBacktestHistory() {
  const container = document.getElementById('backtest-history-list');
  if (!container) return;

  if (backtestHistory.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); font-size: 13px; padding: 20px; text-align: center;">No backtest history yet.</div>`;
    return;
  }

  container.innerHTML = backtestHistory.map(h => `
    <div class="backtest-history-item" onclick="viewBacktestResult(${h.id})">
      <div class="backtest-history-info">
        <div class="backtest-history-ticker">${h.ticker}</div>
        <div class="backtest-history-dates">${h.start_date} ~ ${h.end_date}</div>
      </div>
      <div class="backtest-history-return ${h.total_return >= 0 ? 'backtest-result-positive' : 'backtest-result-negative'}">
        ${h.total_return >= 0 ? '+' : ''}${h.total_return.toFixed(2)}%
      </div>
    </div>
  `).join('');
}


function displayBacktestResult(result) {
  document.getElementById('backtest-placeholder').style.display = 'none';
  document.getElementById('backtest-result-card').style.display = 'block';

  const returnEl = document.getElementById('bt-total-return');
  returnEl.textContent = (result.total_return >= 0 ? '+' : '') + result.total_return.toFixed(2) + '%';
  returnEl.className = result.total_return >= 0 ? 'backtest-result-positive' : 'backtest-result-negative';

  document.getElementById('bt-annual-return').textContent = (result.annual_return >= 0 ? '+' : '') + result.annual_return.toFixed(2) + '%';
  document.getElementById('bt-annual-return').className = result.annual_return >= 0 ? 'backtest-result-positive' : 'backtest-result-negative';

  document.getElementById('bt-max-drawdown').textContent = '-' + result.max_drawdown.toFixed(2) + '%';
  document.getElementById('bt-win-rate').textContent = result.win_rate.toFixed(1) + '%';
  document.getElementById('bt-trades-count').textContent = result.total_trades + ' trades';

  // Render trades
  const tradesContainer = document.getElementById('bt-trades-list');
  if (result.trades && result.trades.length > 0) {
    tradesContainer.innerHTML = result.trades.map(t => `
      <div class="trade-item ${t.type.toLowerCase()}">
        <div>
          <div style="font-weight:600">${t.type}</div>
          <div class="trade-date">${t.date}</div>
        </div>
        <div style="text-align:right">
          <div class="trade-price">$${t.price}</div>
          ${t.profit !== undefined ? `<div class="trade-profit ${t.profit >= 0 ? 'positive' : 'negative'}">${t.profit >= 0 ? '+' : ''}$${t.profit.toFixed(2)}</div>` : ''}
        </div>
      </div>
    `).join('');
  } else {
    tradesContainer.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted)">No trades executed</div>';
  }

  // Render equity curve chart
  if (result.equity_curve && result.equity_curve.length > 0) {
    renderEquityCurve(result.equity_curve);
  }
}

function renderEquityCurve(equityData) {
  const container = document.getElementById('bt-equity-chart');
  if (!container) return;

  // Simple text-based visualization for now
  const maxEquity = Math.max(...equityData.map(e => e.equity));
  const minEquity = Math.min(...equityData.map(e => e.equity));
  const range = maxEquity - minEquity || 1;

  // Create a simple HTML chart
  const chartHtml = `
    <div style="display:flex;align-items:flex-end;height:100%;gap:2px;padding:10px">
      ${equityData.map((e, i) => {
    const height = ((e.equity - minEquity) / range) * 100;
    const color = e.equity >= equityData[0].equity ? 'var(--accent-green)' : 'var(--accent-red)';
    return `<div style="flex:1;background:${color};height:${Math.max(height, 2)}%;min-height:2px" title="${e.date}: $${e.equity}"></div>`;
  }).join('')}
    </div>
  `;
  container.innerHTML = chartHtml;
}

// ===== Strategy Actions =====
function showNewStrategyModal() {
  document.getElementById('strategy-modal-title').textContent = 'Create Strategy';
  document.getElementById('strat-id').value = '';
  document.getElementById('strat-name').value = '';
  document.getElementById('strat-desc').value = '';
  document.getElementById('strat-rsi-buy').value = '30';
  document.getElementById('strat-rsi-sell').value = '70';
  document.getElementById('strategy-modal').style.display = 'flex';
}

function hideStrategyModal() {
  document.getElementById('strategy-modal').style.display = 'none';
}

async function saveStrategy() {
  const name = document.getElementById('strat-name').value;
  const desc = document.getElementById('strat-desc').value;
  const rsiBuy = parseFloat(document.getElementById('strat-rsi-buy').value);
  const rsiSell = parseFloat(document.getElementById('strat-rsi-sell').value);

  if (!name) return alert('Please enter a strategy name');

  // 适配后端 schema: 
  // buy_conditions: { rsi_enabled: true, rsi_below: 30 }
  // sell_conditions: { rsi_enabled: true, rsi_above: 70 }
  const payload = {
    name: name,
    description: desc,
    buy_conditions: {
      rsi_enabled: true,
      rsi_below: rsiBuy
    },
    sell_conditions: {
      rsi_enabled: true,
      rsi_above: rsiSell
    },
    params: {
      initial_capital: 10000,
      stop_loss: 5,
      take_profit: 10
    }
  };

  try {
    await apiFetch('/api/strategies', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    hideStrategyModal();
    loadStrategies();
  } catch (e) {
    alert('Failed to save strategy: ' + e.message);
  }
}

// ===== Backtest Actions =====
let backtestProgressTimer = null;

function startBacktestProgress({ strategyId, ticker, startDate, endDate }) {
  const panel = document.getElementById('backtest-progress-panel');
  const titleEl = document.getElementById('backtest-progress-title');
  const elapsedEl = document.getElementById('backtest-progress-elapsed');
  const detailEl = document.getElementById('backtest-progress-detail');
  const stepsEl = document.getElementById('backtest-progress-steps');
  if (!panel || !titleEl || !elapsedEl || !detailEl || !stepsEl) return;

  const baseStrategyId = resolveStrategyBaseId(strategyId);
  const isPortfolioLike = isPortfolioStrategy(strategyId) || isBuyHoldStrategy(strategyId);
  const steps = [
    {
      label: 'Validate',
      title: 'Validating backtest inputs...',
      detail: `Checking ${ticker.toUpperCase()} strategy settings for ${startDate} to ${endDate}.`
    },
    {
      label: 'Data',
      title: 'Checking market data coverage...',
      detail: 'If the selected range is not fully cached, the backend may download missing daily bars first.'
    },
    {
      label: 'Strategy',
      title: 'Running strategy simulation...',
      detail: baseStrategyId?.includes('system_') ? 'Applying strategy rules, fills, position sizing, and capital rules.' : 'Applying saved strategy rules and capital assumptions.'
    },
    {
      label: 'Benchmarks',
      title: 'Calculating benchmark comparison...',
      detail: isPortfolioLike
        ? 'Comparing against QQQ, VOO, and QQQ/VOO 50/50 buy-and-hold.'
        : `Comparing against ${ticker.toUpperCase()} buy-and-hold over the same dates.`
    },
    {
      label: 'Report',
      title: 'Building credibility report...',
      detail: 'Preparing assumptions, summary metrics, trade log, and equity curve for display.'
    }
  ];

  const startedAt = Date.now();
  panel.style.display = 'block';
  stepsEl.innerHTML = steps.map((step, idx) => `<span class="backtest-progress-step" data-step="${idx}">${step.label}</span>`).join('');

  const render = () => {
    const elapsed = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
    const index = Math.min(steps.length - 1, Math.floor(elapsed / 4));
    const current = steps[index];
    titleEl.textContent = current.title;
    elapsedEl.textContent = `${elapsed}s`;
    detailEl.textContent = elapsed > 18
      ? `${current.detail} Longer tests can take extra time while missing history and benchmarks are prepared.`
      : current.detail;
    stepsEl.querySelectorAll('.backtest-progress-step').forEach((el, idx) => {
      el.classList.toggle('done', idx < index);
      el.classList.toggle('active', idx === index);
    });
  };

  render();
  clearInterval(backtestProgressTimer);
  backtestProgressTimer = setInterval(render, 1000);
}

function finishBacktestProgress(status = 'done', message = '') {
  clearInterval(backtestProgressTimer);
  backtestProgressTimer = null;
  const panel = document.getElementById('backtest-progress-panel');
  const titleEl = document.getElementById('backtest-progress-title');
  const detailEl = document.getElementById('backtest-progress-detail');
  const stepsEl = document.getElementById('backtest-progress-steps');
  if (!panel || !titleEl || !detailEl || !stepsEl) return;

  stepsEl.querySelectorAll('.backtest-progress-step').forEach(el => {
    el.classList.remove('active');
    if (status === 'done') el.classList.add('done');
  });
  titleEl.textContent = status === 'done' ? 'Backtest completed.' : 'Backtest failed.';
  detailEl.textContent = message || (status === 'done' ? 'Results are ready below.' : 'Please review the error message and try again.');
  setTimeout(() => {
    if (!backtestProgressTimer && status === 'done') panel.style.display = 'none';
  }, 2200);
}

async function runBacktest() {
  const strategyId = document.getElementById('backtest-strategy-select').value;
  const ticker = document.getElementById('backtest-ticker').value;
  const capital = parseFloat(document.getElementById('backtest-capital').value);
  const period = document.getElementById('backtest-period').value;

  if (!strategyId) return alert('Please select a strategy');
  if (!ticker) return alert('Please enter a ticker');

  const formatDate = (d) => d.toISOString().split('T')[0];
  let startDate;
  let endDate;

  if (period === 'custom') {
    startDate = document.getElementById('backtest-start-date')?.value;
    endDate = document.getElementById('backtest-end-date')?.value;
    if (!startDate || !endDate) return alert('Please select both start and end dates');
    if (startDate >= endDate) return alert('Start date must be before end date');
  } else {
    const end = new Date();
    const start = new Date();
    if (period === '1y') start.setFullYear(end.getFullYear() - 1);
    else if (period === '2y') start.setFullYear(end.getFullYear() - 2);
    else if (period === '5y') start.setFullYear(end.getFullYear() - 5);
    else if (period === '10y') start.setFullYear(end.getFullYear() - 10);
    else if (period === '20y') start.setFullYear(end.getFullYear() - 20);
    startDate = formatDate(start);
    endDate = formatDate(end);
  }

  let params;
  try {
    params = getBacktestParams(strategyId);
  } catch (e) {
    alert(e.message);
    return;
  }

  const btn = document.getElementById('btn-run-backtest');
  btn.disabled = true;
  btn.classList.add('running');
  btn.textContent = '⏳ Calculating...';
  startBacktestProgress({ strategyId, ticker, startDate, endDate });

  try {
    const res = await apiFetch('/api/backtest', {
      method: 'POST',
      body: JSON.stringify({
        strategy_id: strategyId,
        ticker: ticker.toUpperCase(),
        start_date: startDate,
        end_date: endDate,
        initial_capital: capital,
        params
      })
    });

    if (!res) throw new Error(apiFetch.lastError?.message || 'Server returned an empty error response. Check backend logs for details.');
    if (res.error) throw new Error(res.error);
    displayBacktestResults(res);
    finishBacktestProgress('done');
  } catch (e) {
    finishBacktestProgress('failed', e.message);
    alert('Backtest failed: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.classList.remove('running');
    btn.textContent = '🚀 Run Backtest Simulation';
  }
}


function displayBacktestResults(res) {
  document.getElementById('backtest-results-panel').style.display = 'block';
  document.getElementById('backtest-log-panel').style.display = 'block';

  const summary = res.summary;
  const isPositive = summary.total_return >= 0;
  const money = (v) => {
    const n = Number(v || 0);
    return `${n < 0 ? '-' : ''}$${Math.abs(n).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  };
  const signedMoney = (v) => {
    const n = Number(v || 0);
    return `${n >= 0 ? '+' : '-'}$${Math.abs(n).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  };
  const pctText = (v) => {
    const n = Number(v || 0);
    return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
  };
  const compactJson = (value) => {
    if (!value || typeof value !== 'object') return '-';
    return escapeHtml(JSON.stringify(value, null, 2));
  };
  const hasOptionDetails = (res.trades || []).some(t => t.pos_id || t.long_leg || t.short_leg || t.max_loss !== undefined);
  const hasSleeves = Boolean(res.sleeves?.core || res.sleeves?.options);
  const sleeveHtml = hasSleeves ? (() => {
    const core = res.sleeves.core || {};
    const options = res.sleeves.options || {};
    const rebalanceEvents = res.params?.portfolio_rebalance_events || [];
    const rebalanceText = rebalanceEvents.length
      ? ` · Rebalanced ${rebalanceEvents.length}x`
      : '';
    const assetRows = (core.assets || []).map(asset => `
      <div style="display:grid; grid-template-columns: 70px 1fr 1fr 1fr; gap:8px; align-items:center; font-size:13px; padding:5px 0; border-top:1px solid rgba(255,255,255,0.05);">
        <b>${asset.ticker}</b>
        <span>${money(asset.final_value)}</span>
        <span style="color:${asset.profit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}">${signedMoney(asset.profit)}</span>
        <span>${asset.return_pct}%</span>
      </div>
    `).join('');
    return `
      <div class="portfolio-attribution-grid" style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-bottom:12px;">
        <div class="stat-card" style="padding:12px;">
          <div class="stat-label">${t('backtest.coreSleeve')}</div>
          <div class="stat-value" style="font-size:20px;">${money(core.final_value)}</div>
          <div style="font-size:13px; margin-top:4px; color:${core.profit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}">${signedMoney(core.profit)} · ${core.return_pct}% · Contribution ${core.contribution_pct}%${rebalanceText}</div>
          <div style="margin-top:8px;">${assetRows}</div>
        </div>
        <div class="stat-card" style="padding:12px;">
          <div class="stat-label">${t('backtest.optionsSleeve')}</div>
          <div class="stat-value" style="font-size:20px;">${money(options.final_value)}</div>
          <div style="font-size:13px; margin-top:4px; color:${options.profit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}">${signedMoney(options.profit)} · ${options.return_pct}% · Contribution ${options.contribution_pct}%</div>
          <div style="font-size:12px; color:var(--text-secondary); margin-top:8px;">${options.ticker || '-'} · ${options.strategy_id || '-'}</div>
        </div>
      </div>
    `;
  })() : '';
  const benchmarks = Array.isArray(res.benchmarks) ? res.benchmarks : [];
  const benchmarkHtml = benchmarks.length ? (() => {
    const strategyReturn = Number(summary.total_return || 0);
    const rows = benchmarks.map(b => {
      if (b.error) {
        return `
          <div class="stat-card" style="padding:12px; border-color:rgba(255,91,122,0.28);">
            <div class="stat-label">${escapeHtml(b.name || 'Benchmark')}</div>
            <div style="font-size:13px; color:var(--accent-red); margin-top:6px;">${escapeHtml(b.error)}</div>
          </div>
        `;
      }
      const benchReturn = Number(b.return_pct || 0);
      const alpha = strategyReturn - benchReturn;
      return `
        <div class="stat-card" style="padding:12px;">
          <div class="stat-label">${escapeHtml(b.name || 'Benchmark')}</div>
          <div class="stat-value" style="font-size:20px; color:${benchReturn >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'};">${pctText(benchReturn)}</div>
          <div style="font-size:12px; color:var(--text-secondary); margin-top:4px;">Final ${money(b.final_value)} · Alpha <b style="color:${alpha >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}">${pctText(alpha)}</b></div>
        </div>
      `;
    }).join('');
    return `
      <div style="margin-bottom:16px;">
        <div style="font-size:13px; font-weight:800; color:var(--accent-cyan); text-transform:uppercase; letter-spacing:.04em; margin-bottom:8px;">Benchmark Comparison</div>
        <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap:10px;">${rows}</div>
      </div>
    `;
  })() : '';
  const assumptions = res.assumptions || {};
  const assumptionHtml = assumptions.data_source ? `
    <div style="margin-bottom:16px;">
      <div style="font-size:13px; font-weight:800; color:var(--accent-cyan); text-transform:uppercase; letter-spacing:.04em; margin-bottom:8px;">Backtest Assumptions</div>
      <div class="stat-card" style="padding:14px;">
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap:12px;">
          <div>
            <div class="stat-label">Data Source</div>
            <div style="font-size:13px; line-height:1.55;">${escapeHtml(assumptions.data_source)}</div>
          </div>
          <div>
            <div class="stat-label">Data Range</div>
            <div style="font-size:13px; line-height:1.55;">${escapeHtml(assumptions.data_range?.requested_start || '-')} → ${escapeHtml(assumptions.data_range?.requested_end || '-')}</div>
          </div>
          <div>
            <div class="stat-label">Fill Model</div>
            <div style="font-size:13px; line-height:1.55;">${escapeHtml(assumptions.fill_model || '-')}</div>
          </div>
          <div>
            <div class="stat-label">Capital Basis</div>
            <div style="font-size:13px; line-height:1.55;">${escapeHtml(assumptions.capital_utilization_basis || '-')}</div>
          </div>
          <div>
            <div class="stat-label">Chain Source</div>
            <div style="font-size:13px; line-height:1.55;">${escapeHtml(assumptions.option_chain_source || '-')}</div>
          </div>
          <div>
            <div class="stat-label">Benchmark Method</div>
            <div style="font-size:13px; line-height:1.55;">${escapeHtml(assumptions.benchmark_method || '-')}</div>
          </div>
        </div>
        <details style="margin-top:12px;">
          <summary style="cursor:pointer; color:var(--text-secondary); font-size:12px; font-weight:700;">Strategy Parameters</summary>
          <pre style="margin-top:8px; white-space:pre-wrap; word-break:break-word; font-size:11px; line-height:1.5; color:var(--text-secondary); background:rgba(0,0,0,0.18); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:10px;">${compactJson(assumptions.strategy_parameters)}</pre>
        </details>
      </div>
    </div>
  ` : '';
  const buildPositionRows = (trades) => {
    const positions = new Map();
    (trades || []).forEach(trade => {
      const id = trade.pos_id || `NO_POS_${positions.size}`;
      if (!positions.has(id)) positions.set(id, { pos_id: id });
      const position = positions.get(id);
      if (trade.event === 'OPEN' || String(trade.type || '').includes('OPEN')) {
        position.open = trade;
      } else if (trade.event === 'CLOSE' || String(trade.type || '').includes('CLOSE')) {
        position.close = trade;
      }
    });
    return [...positions.values()].sort((a, b) => {
      const pa = String(a.pos_id || '');
      const pb = String(b.pos_id || '');
      return pa.localeCompare(pb, undefined, { numeric: true });
    });
  };

  document.getElementById('bt-summary-content').innerHTML = `
    <div class="stats-grid" style="grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 20px;">
      <div class="stat-card" style="padding: 16px;">
        <div class="stat-label">${t('backtest.totalReturn')}</div>
        <div class="stat-value ${isPositive ? 'up' : 'down'}" style="font-size: 20px;">${isPositive ? '▲' : '▼'} ${summary.total_return}%</div>
      </div>
      <div class="stat-card" style="padding: 16px;">
        <div class="stat-label">${t('backtest.winRate')}</div>
        <div class="stat-value" style="font-size: 20px; color: var(--accent-purple);">${summary.win_rate}%</div>
      </div>
      <div class="stat-card" style="padding: 16px;">
        <div class="stat-label">${t('backtest.finalValue')}</div>
        <div class="stat-value" style="font-size: 28px; color: var(--accent-green); font-weight: 800;">$${(summary.final_value || 0).toLocaleString()}</div>
      </div>
      <div class="stat-card" style="padding: 16px;">
        <div class="stat-label">${t('backtest.totalTrades')}</div>
        <div class="stat-value" style="font-size: 20px;">${summary.total_trades}</div>
      </div>
    </div>
    ${sleeveHtml}
    ${benchmarkHtml}
    ${assumptionHtml}
    ${hasOptionDetails ? `
      <div style="font-size:12px; color:var(--text-muted); line-height:1.6; margin-bottom:10px;">
        Params: DTE ${res.params?.dte_target ?? '-'} · Long Δ ${res.params?.long_delta_target ?? '-'} ± ${res.params?.delta_tolerance ?? '-'} · Short Δ ${res.params?.short_delta_target ?? '-'} · Width $${res.params?.spread_width ?? '-'} · Fill Slip ${res.params?.fill_slippage ?? '-'} · Capital Use ${(Number(res.params?.capital_utilization_pct ?? res.params?.risk_pct ?? 0) * 100).toFixed(1)}%
      </div>
      <div class="stats-grid" style="grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 12px;">
        <div class="stat-card" style="padding: 12px;">
          <div class="stat-label">${t('backtest.cashBalance')}</div>
          <div class="stat-value" style="font-size: 16px;">${money(summary.ending_cash)}</div>
        </div>
        <div class="stat-card" style="padding: 12px;">
          <div class="stat-label">${t('backtest.riskAtWork')}</div>
          <div class="stat-value" style="font-size: 16px; color: var(--accent-red);">${money(summary.ending_locked_risk)}</div>
        </div>
        <div class="stat-card" style="padding: 12px;">
          <div class="stat-label">${t('backtest.availableCash')}</div>
          <div class="stat-value" style="font-size: 16px; color: var(--accent-blue);">${money(summary.ending_available_cash)}</div>
        </div>
      </div>
    ` : ''}
  `;

  // Render Trades - with scrollable container
  const logPanel = document.getElementById('backtest-log-panel');
  if (logPanel) {
    logPanel.style.maxHeight = '500px';
    logPanel.style.overflowY = 'auto';
  }
  
  const logBody = document.getElementById('backtest-log-body');
  const headerRow = document.querySelector('#backtest-log-panel thead tr');
  if (hasOptionDetails && headerRow) {
    headerRow.style.position = 'sticky';
    headerRow.style.top = '0';
    headerRow.style.zIndex = '5';
    headerRow.style.background = 'var(--bg-secondary)';
    headerRow.style.boxShadow = '0 1px 0 var(--border)';
    headerRow.innerHTML = `
      <th style="padding: 12px;">${t('backtest.position')}</th>
      <th style="padding: 12px;">${t('backtest.openDate')}</th>
      <th style="padding: 12px;">${t('backtest.closeDate')}</th>
      <th style="padding: 12px;">${t('backtest.underlying')}</th>
      <th style="padding: 12px;">${t('backtest.legs')}</th>
      <th style="padding: 12px;">${t('backtest.entryCost')}</th>
      <th style="padding: 12px;">${t('backtest.settlement')}</th>
      <th style="padding: 12px;">${t('backtest.netPl')}</th>
      <th style="padding: 12px;">${t('backtest.riskBalance')}</th>
    `;
    const positionRows = buildPositionRows(res.trades);
    logBody.innerHTML = positionRows.map(position => {
      const open = position.open || {};
      const close = position.close || {};
      const display = close.event ? close : open;
      const netPl = close.event ? Number(close.pl || 0) : 0;
      const isWin = netPl > 0;
      const isLoss = netPl < 0;
      const entryCost = Number(open.cash_flow || 0);
      const settlement = close.event ? Number(close.cash_flow || 0) : null;
      const maxProfit = display.max_profit === null || display.max_profit === undefined ? 'Unlimited' : money(display.max_profit);
      const legs = `
        <div style="font-family: var(--font-mono); line-height: 1.55;">
          <div style="color: var(--accent-green);">${display.long_leg || '-'}</div>
          <div style="color: var(--accent-red);">${display.short_leg || '-'}</div>
          <div style="color: var(--text-muted);">DTE ${display.dte || '-'} · Width $${display.spread_width || '-'} · Δ ${display.long_delta ?? '-'} / ${display.short_delta ?? '-'}</div>
        </div>
      `;
      return `
        <tr style="border-bottom: 1px solid rgba(255,255,255,0.04);">
          <td style="padding: 12px; font-family: var(--font-mono); font-weight: 700;">${position.pos_id || '-'}</td>
          <td style="padding: 12px; color: var(--text-secondary); white-space: nowrap;">${open.date || '-'}</td>
          <td style="padding: 12px; color: var(--text-secondary); white-space: nowrap;">${close.date || '-'}</td>
          <td style="padding: 12px; font-family: var(--font-mono);">
            <div>${money(open.underlying_price || open.price)}</div>
            ${close.event ? `<div style="color: var(--text-muted);">${money(close.underlying_price || close.price)}</div>` : ''}
          </td>
          <td style="padding: 12px; min-width: 240px;">${legs}</td>
          <td style="padding: 12px; font-weight: 600; color:var(--text-primary);">${money(Math.abs(entryCost))}</td>
          <td style="padding: 12px; font-weight: 600; color:${settlement !== null ? 'var(--text-primary)' : 'var(--text-muted)'}">${settlement !== null ? money(settlement) : '-'}</td>
          <td style="padding: 12px; font-weight: 800; color: ${isWin ? 'var(--accent-green)' : isLoss ? 'var(--accent-red)' : 'var(--text-muted)'}">
            ${close.event ? signedMoney(netPl) : '-'}
          </td>
          <td style="padding: 12px; min-width: 220px; font-size: 11px; color: var(--text-muted); line-height: 1.55;">
            <div>Max loss: <b style="color: var(--accent-red);">${money(display.max_loss)}</b> · Max profit: <b style="color: var(--accent-green);">${maxProfit}</b></div>
            <div>Cash: ${money(display.cash_balance)} · Risk: ${money(display.locked_risk)}${display.locked_collateral !== undefined ? ` · Collateral: ${money(display.locked_collateral)}` : ''}</div>
            <div>Available: ${money(display.available_cash)}</div>
          </td>
        </tr>
      `;
    }).join('');
  } else {
    if (headerRow) {
      headerRow.innerHTML = `
        <th style="padding: 12px;">${t('fields.type')}</th>
        <th style="padding: 12px;">${t('fields.date')}</th>
        <th style="padding: 12px;">${t('backtest.price')}</th>
        <th style="padding: 12px;">${t('backtest.shares')}</th>
        <th style="padding: 12px;">${t('backtest.netPl')}</th>
        <th style="padding: 12px;">${t('backtest.details')}</th>
      `;
    }
    logBody.innerHTML = res.trades.map(t => {
      const isWin = t.pl > 0;
      const isLoss = t.pl < 0;
      const tagClass = t.type.includes('OPEN') ? 'bullish' : (t.type.includes('EXPIRY') ? (isWin ? 'bullish' : (isLoss ? 'bearish' : 'neutral')) : 'neutral');
      
      return `
        <tr style="border-bottom: 1px solid rgba(255,255,255,0.02);">
          <td style="padding: 12px;"><span class="sentiment-tag sentiment-${tagClass}" style="padding:2px 6px; font-size:10px;">${t.type}</span></td>
          <td style="padding: 12px; color: var(--text-secondary);">${t.date}</td>
          <td style="padding: 12px; font-family: var(--font-mono);">${money(t.price)}</td>
          <td style="padding: 12px;">${t.qty || t.shares || 100}</td>
          <td style="padding: 12px; font-weight: 600; color: ${isWin ? 'var(--accent-green)' : isLoss ? 'var(--accent-red)' : 'inherit'}">
            ${t.pl !== 0 ? signedMoney(t.pl) : '-'}
          </td>
          <td style="padding: 12px; font-size: 11px; color: var(--text-muted);">${t.memo || t.pos_id || '-'}</td>
        </tr>
      `;
    }).reverse().join('');
  }

  // Equity Chart
  renderEquityCurve(res.equity_curve, res);
}

function getBacktestPriceLineLabel(result) {
  const rawTicker = String(
    result?.sleeves?.options?.ticker ||
    result?.params?.portfolio?.option_ticker ||
    result?.summary?.ticker ||
    ''
  ).toUpperCase();
  const ticker = rawTicker === 'PORTFOLIO' ? '' : rawTicker;
  const labels = {
    SPY: 'S&P 500 (SPY) Price',
    VOO: 'S&P 500 (VOO) Price',
    '^GSPC': 'S&P 500 Index',
    QQQ: 'QQQ Price'
  };
  return labels[ticker] || (ticker ? `${ticker} Price` : 'Reference Price');
}

function renderEquityCurve(data, result = null) {
  const container = document.getElementById('backtest-equity-chart');
  if (!container || !data || data.length === 0) return;

  container.innerHTML = ''; // Clear previous
  container.style.position = 'relative';
  const underlyingData = data
    .filter(d => Number.isFinite(Number(d.underlying_price)))
    .map(d => ({
      time: d.time,
      value: Number(d.underlying_price)
    }));
  const priceLineLabel = getBacktestPriceLineLabel(result);
  const legend = document.createElement('div');
  legend.style.cssText = 'position:absolute;top:6px;left:8px;z-index:2;display:flex;gap:12px;font-size:12px;font-weight:700;color:var(--text-secondary);background:rgba(9,14,26,0.72);border:1px solid var(--border);border-radius:6px;padding:4px 7px;';
  legend.innerHTML = `
    <span><span style="color:var(--accent-green);">■</span> Portfolio Value</span>
    ${underlyingData.length ? `<span><span style="color:var(--accent-blue);">■</span> ${escapeHtml(priceLineLabel)}</span>` : ''}
  `;
  container.appendChild(legend);
  
  const chart = LightweightCharts.createChart(container, {
    width: container.offsetWidth,
    height: container.offsetHeight || 200,
    layout: {
      background: { color: 'transparent' },
      textColor: '#7a8aab',
    },
    grid: {
      vertLines: { visible: false },
      horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
    },
    timeScale: {
      borderColor: 'rgba(255, 255, 255, 0.1)',
    },
    rightPriceScale: {
      borderColor: 'rgba(255, 255, 255, 0.1)',
    },
    leftPriceScale: {
      visible: true,
      borderColor: 'rgba(255, 255, 255, 0.1)',
    }
  });

  const lineSeries = chart.addLineSeries({
    color: 'rgba(0, 230, 118, 0.8)',
    lineWidth: 2,
    areaTopColor: 'rgba(0, 230, 118, 0.2)',
    areaBottomColor: 'rgba(0, 230, 118, 0.0)',
  });
  const underlyingSeries = chart.addLineSeries({
    color: 'rgba(0, 212, 255, 0.9)',
    lineWidth: 2,
    priceScaleId: 'left',
  });

  // Backend provides {time: timestamp, value: equity}
  lineSeries.setData(data.map(d => ({
    time: d.time,
    value: d.value
  })));
  if (underlyingData.length) {
    underlyingSeries.setData(underlyingData);
  }

  chart.timeScale().fitContent();
}
