import os

replacements = {
    # Pipeline scripts
    "scripts/01_parse_all_universe.py": "scripts/01_pipeline/01_parse_all_universe.py",
    "scripts/02_quantconnect_export_by_year.py": "scripts/01_pipeline/02_quantconnect_export_by_year.py",
    "scripts/03_process_qc_zips_by_year.py": "scripts/01_pipeline/03_process_qc_zips_by_year.py",
    "scripts/generate_qc_export_script.py": "scripts/01_pipeline/generate_qc_export_script.py",

    # Universe validation scripts
    "scripts/step1_check_universe.py": "scripts/02_validation_universe/step1_check_universe.py",
    "scripts/test1_universe_structure.py": "scripts/02_validation_universe/test1_universe_structure.py",
    "scripts/test3_universe_pit_turnover.py": "scripts/02_validation_universe/test3_universe_pit_turnover.py",
    "scripts/test4_security_identity.py": "scripts/02_validation_universe/test4_security_identity.py",
    "scripts/test5_historical_survivorship.py": "scripts/02_validation_universe/test5_historical_survivorship.py",
    "scripts/test6_crosscheck_archive.py": "scripts/02_validation_universe/test6_crosscheck_archive.py",
    "scripts/test7_ticker_format_mapping.py": "scripts/02_validation_universe/test7_ticker_format_mapping.py",
    "scripts/test8_final_audit_mismatches.py": "scripts/02_validation_universe/test8_final_audit_mismatches.py",

    # OHLCV validation scripts
    "scripts/step2_check_market_data.py": "scripts/03_validation_ohlcv/step2_check_market_data.py",
    "scripts/test_m1_ohlcv_structure.py": "scripts/03_validation_ohlcv/test_m1_ohlcv_structure.py",
    "scripts/test_m2_time_coverage.py": "scripts/03_validation_ohlcv/test_m2_time_coverage.py",
    "scripts/test_m3_corporate_actions.py": "scripts/03_validation_ohlcv/test_m3_corporate_actions.py",
    "scripts/test_m4_russell_ohlcv_compatibility.py": "scripts/03_validation_ohlcv/test_m4_russell_ohlcv_compatibility.py",
    "scripts/test_m5_m6_market_value.py": "scripts/03_validation_ohlcv/test_m5_m6_market_value.py",

    # Deep audit scripts
    "scripts/deep_audit_survivorship.py": "scripts/04_deep_audit/deep_audit_survivorship.py",
    "scripts/deep_audit_phase2.py": "scripts/04_deep_audit/deep_audit_phase2.py",
}

docs = [
    "docs/Data report/data_exploration_report.md",
    "docs/Data report/data_exploration_report.html",
]

for doc_path in docs:
    if os.path.exists(doc_path):
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()
        for old_ref, new_ref in replacements.items():
            content = content.replace(old_ref, new_ref)
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated references in {doc_path}")

