import os
import shutil

base_dir = "scripts"

folders = {
    "01_pipeline": [
        "01_parse_all_universe.py",
        "02_quantconnect_export_by_year.py",
        "03_process_qc_zips_by_year.py",
        "generate_qc_export_script.py",
    ],
    "02_validation_universe": [
        "step1_check_universe.py",
        "test1_universe_structure.py",
        "test3_universe_pit_turnover.py",
        "test4_security_identity.py",
        "test5_historical_survivorship.py",
        "test6_crosscheck_archive.py",
        "test7_ticker_format_mapping.py",
        "test8_final_audit_mismatches.py",
    ],
    "03_validation_ohlcv": [
        "step2_check_market_data.py",
        "test_m1_ohlcv_structure.py",
        "test_m2_time_coverage.py",
        "test_m3_corporate_actions.py",
        "test_m4_russell_ohlcv_compatibility.py",
        "test_m5_m6_market_value.py",
    ],
    "04_deep_audit": [
        "deep_audit_survivorship.py",
        "deep_audit_phase2.py",
    ]
}

for folder, files in folders.items():
    target_dir = os.path.join(base_dir, folder)
    os.makedirs(target_dir, exist_ok=True)
    for f in files:
        src_path = os.path.join(base_dir, f)
        dst_path = os.path.join(target_dir, f)
        if os.path.exists(src_path):
            shutil.move(src_path, dst_path)
            print(f"Moved {f} -> {folder}/")

print("Scripts organization complete!")
