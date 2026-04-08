SECTOR_ETFS = [
    "XLP",   # Consumer Staples
    "XLK",   # Technology
    "XLF",   # Financials
    "XLE",   # Energy
    "XLV",   # Health Care
    "XLI",   # Industrials
    "XLY",   # Consumer Discretionary
    "XLB",   # Materials
    "XLU",   # Utilities
    "XLRE",  # Real Estate
    "XLC",   # Communication Services
    "XOP",   # Oil & Gas Exploration
    "GLD",   # Gold
    "SLV",   # Silver
    "TLT",   # 20+ Year Treasury Bond
    "HYG",   # High Yield Corporate Bond
    "LQD",   # Investment Grade Corporate Bond
]

MARKET_ETFS = [
    "IWM",   # Russell 2000
    "QQQ",   # Nasdaq-100
    "SPY",   # S&P 500
    "DIA",   # Dow Jones Industrial
    "VTI",   # Total Stock Market
    "EFA",   # MSCI EAFE (International)
    "EEM",   # MSCI Emerging Markets
    "ARKK",  # ARK Innovation
    "TQQQ",  # Nasdaq-100 3x Leveraged
    "SQQQ",  # Nasdaq-100 3x Inverse
]

TOP_STOCKS = [
    # Mega-cap tech
    "NVDA", "AAPL", "MSFT", "GOOGL", "META", "AMZN", "TSLA",
    # Semiconductors
    "AMD", "INTC", "MU", "QCOM", "AVGO", "TSM",
    # Software
    "CRM", "ORCL", "SNOW", "CRWD", "PLTR",
    # Finance
    "JPM", "BAC", "GS", "MS", "C", "V", "MA", "COIN",
    # Consumer
    "WMT", "COST", "TGT", "HD", "DIS", "NFLX",
    # Energy
    "XOM", "CVX",
    # Healthcare / Biotech
    "JNJ", "PFE", "AMGN", "MRNA",
    # EV / Automotive
    "RIVN", "NIO", "F", "GM",
    # Fintech / Payments
    "SQ", "PYPL", "SOFI", "HOOD",
    # Other high-volume options stocks
    "UBER", "SNAP", "RBLX", "DKNG", "BA",
]

ALL_TICKERS = SECTOR_ETFS + MARKET_ETFS + TOP_STOCKS

TICKER_CATEGORIES = {}
for t in SECTOR_ETFS:
    TICKER_CATEGORIES[t] = "Sector ETF"
for t in MARKET_ETFS:
    TICKER_CATEGORIES[t] = "Market ETF"
for t in TOP_STOCKS:
    TICKER_CATEGORIES[t] = "Stock"
