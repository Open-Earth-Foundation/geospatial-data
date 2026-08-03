# CHIRPS Daily Extreme Indices

Site-scoped export of CHIRPS daily extreme precipitation indices for NBS flood pluvial screening.

## Source

**Dataset:** UCSB-CHG/CHIRPS/DAILY  
**GEE band:** `precipitation` (mm)  
**Resolution:** ~0.05° (~5 km export scale)

## CLI (D8)

Export to paths referenced in `nbs_screening/config/sites/{city}.yaml`:

```bash
# Single MN city (rx1day + rx5day + r90p for 2024)
python transformation/chirps_daily/extract_chirps_daily.py --site richfield

# All Minnesota cities
python transformation/chirps_daily/extract_chirps_daily.py --country "United States"

# Pluvial proxies only (used in nbs_rules _heavy_rain_signal)
python transformation/chirps_daily/extract_chirps_daily.py --site richfield --only rx1day,rx5day

# Dry-run
python transformation/chirps_daily/extract_chirps_daily.py --site richfield --dry-run
```

**Outputs (default year 2024)**

| Layer | NBS catalog key | Index |
|-------|-----------------|-------|
| rx1day | `chirps_rx1day_2024` | Annual max 1-day precipitation (mm) |
| rx5day | `chirps_rx5day_2024` | Annual max 5-day rolling sum (mm) |
| r90p | `chirps_r90p_2024` | 90th percentile of daily precipitation (mm) |

**QA SVGs:** `sites/{site}/data/intermediate/qa_inputs/`

## NBS usage

Flood pluvial mechanism uses `rx1day_2024_mean` (≥ 50 mm) and `rx5day_2024_mean` (≥ 100 mm) in `_heavy_rain_signal`.

## Related

Seasonal R90p climatology for landslide: `transformation/chirps_r90p/extract_chirps_r90p.py`
