"""
Script: scripts/03_process_qc_zips_by_year.py
Purpose: Unpack QuantConnect ZIP files year-by-year and save separate Parquet files per year
         into data/processed/by_year/ (e.g. russell1000_2000.parquet).
         Also aggregates all audit_russell1000_{year}.csv logs into a master audit file.
"""
import os, sys, io, zipfile, csv
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ZIP_DIR_PRIMARY   = os.path.join(BASE, "data", "raw", "market_data")
ZIP_DIR_SECONDARY = os.path.join(BASE, "data", "raw", "quantconnect")
ZIP_DIR = ZIP_DIR_PRIMARY if os.path.exists(ZIP_DIR_PRIMARY) and len(os.listdir(ZIP_DIR_PRIMARY)) > 0 else ZIP_DIR_SECONDARY

OUT_DIR = os.path.join(BASE, "data", "processed", "by_year")
AUDIT_DIR = os.path.join(BASE, "data", "processed", "audit")
AUDIT_BY_YEAR_DIR = os.path.join(AUDIT_DIR, "by_year")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(AUDIT_DIR, exist_ok=True)
os.makedirs(AUDIT_BY_YEAR_DIR, exist_ok=True)

def process_all_zips():
    print("=" * 80)
    print("PROCESSING QUANTCONNECT AUDIT-GRADE ZIP FILES BY YEAR")
    print(f"Source Directory : {ZIP_DIR}")
    print(f"Target Directory : {OUT_DIR}")
    print("=" * 80)

    if not os.path.exists(ZIP_DIR):
        print(f"⚠️ Directory {ZIP_DIR} does not exist yet. Please place downloaded ZIP files there.")
        return

    zip_files = sorted([f for f in os.listdir(ZIP_DIR) if f.startswith("russell1000_") and f.endswith(".zip")])
    if not zip_files:
        print(f"⚠️ No ZIP files found in {ZIP_DIR}. Download them from QuantConnect and place them in data/raw/market_data/.")
        return

    all_audit_frames = []

    for z_name in zip_files:
        year_str = z_name.replace("russell1000_", "").replace(".zip", "")
        z_path = os.path.join(ZIP_DIR, z_name)
        print(f"\nProcessing Year {year_str} from {z_name}...")

        daily_dfs = []
        audit_df = None

        with zipfile.ZipFile(z_path, "r") as z:
            namelist = z.namelist()
            for fname in namelist:
                if fname.startswith("audit_") and fname.endswith(".csv"):
                    with z.open(fname) as f_audit:
                        audit_df = pd.read_csv(f_audit)
                        all_audit_frames.append(audit_df)
                        # Save yearly audit file
                        yearly_audit_path = os.path.join(AUDIT_BY_YEAR_DIR, f"audit_{year_str}.csv")
                        audit_df.to_csv(yearly_audit_path, index=False)
                elif fname.endswith(".csv"):
                    # Stock data CSV
                    ticker = fname.split("_")[0]
                    with z.open(fname) as f_stock:
                        df_stock = pd.read_csv(f_stock)
                        df_stock["ticker"] = ticker
                        df_stock["year"] = int(year_str)
                        daily_dfs.append(df_stock)

        if daily_dfs:
            combined_year_df = pd.concat(daily_dfs, ignore_index=True)
            # Ensure standard date parsing
            if "time" in combined_year_df.columns:
                combined_year_df.rename(columns={"time": "date"}, inplace=True)
            if "date" in combined_year_df.columns:
                combined_year_df["date"] = pd.to_datetime(combined_year_df["date"])

            out_parquet = os.path.join(OUT_DIR, f"russell1000_{year_str}.parquet")
            combined_year_df.to_parquet(out_parquet, index=False, compression="snappy")
            print(f"  ✅ Saved Year {year_str} Parquet: {out_parquet} ({len(combined_year_df):,} rows, {len(daily_dfs)} tickers)")
            if audit_df is not None:
                print(f"  ✅ Saved Year {year_str} Audit CSV: {os.path.join(AUDIT_BY_YEAR_DIR, f'audit_{year_str}.csv')} ({len(audit_df)} records)")
        else:
            print(f"  ⚠️ No stock CSVs found in {z_name}")

    if all_audit_frames:
        master_audit = pd.concat(all_audit_frames, ignore_index=True)
        master_audit_path = os.path.join(AUDIT_DIR, "master_audit_2000_2026.csv")
        master_audit.to_csv(master_audit_path, index=False)
        print(f"\n✅ MASTER AUDIT LOG SAVED: {master_audit_path} ({len(master_audit):,} total stock-year records)")

if __name__ == "__main__":
    process_all_zips()
