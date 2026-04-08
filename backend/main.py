"""
SpreadHunter — FastAPI backend
"""

import asyncio
import logging
import time
from typing import Optional

from cachetools import TTLCache
from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import CACHE_TTL
from tickers import ALL_TICKERS, SECTOR_ETFS, MARKET_ETFS, TOP_STOCKS, TICKER_CATEGORIES
from data_service import scan_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SpreadHunter API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── In-memory cache ───────────────────────────────────────────────────────────
_cache: TTLCache = TTLCache(maxsize=5, ttl=CACHE_TTL)
_scan_lock = asyncio.Lock()
_last_update: float | None = None
_is_scanning: bool = False


# ─── Background scan ───────────────────────────────────────────────────────────

async def _run_scan(tickers: list[str]):
    global _is_scanning, _last_update
    async with _scan_lock:
        if "spreads" in _cache:
            return  # another coroutine already refreshed while we waited
        _is_scanning = True
        try:
            logger.info(f"Starting scan of {len(tickers)} tickers …")
            spreads = await scan_all(tickers)
            _cache["spreads"] = spreads
            _last_update = time.time()
            logger.info(f"Scan complete — {len(spreads)} spreads found")
        except Exception as e:
            logger.error(f"Scan failed: {e}")
        finally:
            _is_scanning = False


# ─── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "last_update": _last_update,
        "is_scanning": _is_scanning,
        "cached_spreads": len(_cache.get("spreads", [])),
    }


@app.get("/api/tickers")
def get_tickers():
    return {
        "sector_etfs": SECTOR_ETFS,
        "market_etfs": MARKET_ETFS,
        "top_stocks": TOP_STOCKS,
        "total": len(ALL_TICKERS),
    }


@app.get("/api/spreads")
async def get_spreads(
    background_tasks: BackgroundTasks,
    # ── Filters ──
    min_ror: float = Query(10.0, description="Min return on risk (%)"),
    max_prob: float = Query(35.0, description="Max probability of assignment (%)"),
    min_credit: float = Query(0.10, description="Min net credit ($)"),
    min_distance: float = Query(2.0, description="Min distance from danger (%)"),
    category: Optional[str] = Query(None, description="sector_etfs | market_etfs | top_stocks"),
    ticker: Optional[str] = Query(None, description="Single ticker symbol"),
    # ── Sorting ──
    sort_by: str = Query("return_on_risk", description="Column to sort by"),
    sort_dir: str = Query("desc", description="asc | desc"),
):
    global _is_scanning

    # Kick off a background scan if the cache is cold
    if "spreads" not in _cache and not _is_scanning:
        background_tasks.add_task(_run_scan, ALL_TICKERS)

    all_spreads = _cache.get("spreads", [])

    # ── Category filter ──
    if ticker:
        all_spreads = [s for s in all_spreads if s["ticker"].upper() == ticker.upper()]
    elif category:
        allowed = {
            "sector_etfs": set(SECTOR_ETFS),
            "market_etfs": set(MARKET_ETFS),
            "top_stocks": set(TOP_STOCKS),
        }.get(category, set(ALL_TICKERS))
        all_spreads = [s for s in all_spreads if s["ticker"] in allowed]

    # ── Numeric filters ──
    filtered = [
        s for s in all_spreads
        if s["return_on_risk"] >= min_ror
        and s["prob_assignment"] <= max_prob
        and s["net_credit"] >= min_credit
        and s["distance_from_danger"] >= min_distance
    ]

    # ── Sort ──
    reverse = sort_dir.lower() != "asc"
    try:
        filtered.sort(key=lambda s: s.get(sort_by, 0), reverse=reverse)
    except TypeError:
        pass

    return {
        "spreads": filtered,
        "total": len(filtered),
        "is_scanning": _is_scanning,
        "last_update": _last_update,
        "cache_age_seconds": (
            round(time.time() - _last_update) if _last_update else None
        ),
    }


@app.post("/api/refresh")
async def refresh(background_tasks: BackgroundTasks):
    """Force a fresh scan (clears cache)."""
    _cache.clear()
    background_tasks.add_task(_run_scan, ALL_TICKERS)
    return {"message": "Refresh started"}


# ─── Serve React frontend (production) ─────────────────────────────────────────
import os

_frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        index = os.path.join(_frontend_dist, "index.html")
        return FileResponse(index)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
