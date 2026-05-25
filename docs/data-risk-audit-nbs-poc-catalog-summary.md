# NBS Project Preparation POC — catalog-side summary (ON-5679)

This file satisfies the ON-5679 requirement for a **copy or summary** of catalog-side findings in the **`Open-Earth-Foundation/geospatial-data`** repository.

**Primary audit document (full inventory + risk analysis):**  
[`NBS-Project-Preparation/docs/data-risk-audit.md`](../../NBS-Project-Preparation/docs/data-risk-audit.md) — **§2.1** is a single master inventory table (shared columns + `Origin` tag). For rows whose **Origin** is `OEF catalog S3`, **License**, **Resolution**, **Location / access** (catalog `assets.visual_tiles` URL), **Vintage**, **`dataset_id`**, and **offline transformation notebook** paths under [`transformation/`](../transformation) (where present) are reflected in the **Processing** column, with catalog fields from [`catalog/datasets.yaml`](../catalog/datasets.yaml).

**Authoritative metadata for tiled products:**  
`catalog/datasets.yaml`, `collections/layers.yaml`, and transformations under `transformation/` in this repo.

---

## Scope

Document here, per **S3 path / collection** used by the POC tile proxy, the fields needed for the POC audit:

- Product name and **license**
- **Native resolution** and **temporal coverage** (vintage)
- Link to **transformation** or recipe that produced the layer
- Any **known caveats** called out in this catalog

The POC resolves tiles via `https://geo-test-api.s3.us-east-1.amazonaws.com/...` (see `NBS-Project-Preparation/server/routes/tileProxyRoutes.ts` and `shared/geospatial-layers.ts`).

---

## Layer → catalog mapping

Per-layer **license**, **native resolution**, **temporal coverage**, **S3 URL template**, **`dataset_id`**, and **transformation** notebook (under [`transformation/`](../transformation) when checked in) for all `OEF catalog S3` inventory rows are maintained in the POC audit **§2.1** table (authoritative for the audit deliverable). This file stays the **catalog-side** anchor: definitions and provenance live in [`catalog/datasets.yaml`](../catalog/datasets.yaml) and related `collections/` / `transformation/` assets.

**Quick index (POC proxy segment → `dataset_id` in `datasets.yaml`):** use §2.1 “Processing” column, or match the proxy path in `NBS-Project-Preparation/shared/geospatial-layers.ts` to the `assets.visual_tiles.url_template` in the catalog entry. **CHIRPS / FRI** notebooks: [`CCRADiscovery/floods`](../../CCRADiscovery/floods). **ERA5-Land temperature / HWM**: [`CCRADiscovery/heatwaves`](../../CCRADiscovery/heatwaves). See POC §2.1 Processing. Notable mismatches called out in §2.1 Notes: POC `solar_pvout` proxy still points at JRC GSW transition tiles while catalog/audit use [`global_solar_atlas`](../catalog/datasets.yaml) ([`transformation/global_solar_atlas/release/v2/transformation.ipynb`](../transformation/global_solar_atlas/release/v2/transformation.ipynb)); `hwm_2050s_585` URL segment vs `era5land_hwm_2050s_85` description.

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-05-13 | | OEF catalog S3 rows in POC §2.1 from `catalog/datasets.yaml` (companion points to master table); Processing adds `transformation/` notebook paths where they exist in this repo. |
| | | Initial scaffold for ON-5679 |
