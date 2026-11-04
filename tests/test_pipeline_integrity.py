"""
Unit and Integration Test Suite: Pipeline Static Integrity & Contract Verification
===================================================================================
Authoritative test suite covering Requirement R6 (Pipeline Verification & Static Integrity Check)
- Tests 1-13 scripts static syntax (py_compile) and zero hardcoded drive paths
- Tests clean imports and cloud-only documentation markings
- Tests Step 01 Universe extraction output contracts
- Tests Step 03 / Step 04 Parquet path contract synchronization
- Tests Step 04b vs Step 05 distinct audit table ownership and distinct schemas
- Tests 2D matrices dimensions and calendar partition (630 warmup, 5911 dev, 711 OOS)
- Tests configs/base_config.yaml and src/ modern vs src/archive_v1/ layout
- Tests README.md and docs/pipeline_dag.md accuracy and realism
"""

import os
import glob
import json
import ast
import py_compile
import unittest
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent

class TestPipelineIntegrity(unittest.TestCase):

    def test_01_static_compilation_all_pipeline_scripts(self):
        """Verify all 13 pipeline scripts compile with zero syntax errors."""
        scripts = sorted(glob.glob(str(ROOT / "scripts/01_pipeline/*.py")))
        self.assertEqual(len(scripts), 13, f"Expected exactly 13 scripts, found {len(scripts)}")
        for script_path in scripts:
            try:
                py_compile.compile(script_path, doraise=True)
            except Exception as e:
                self.fail(f"Syntax error compiling {os.path.basename(script_path)}: {e}")

    def test_02_zero_hardcoded_drive_paths(self):
        """Verify zero hardcoded drive paths in scripts/01_pipeline/."""
        scripts = sorted(glob.glob(str(ROOT / "scripts/01_pipeline/*.py")))
        forbidden = ["d:/a_learning", "d:\\a_learning", "d:/learning", "d:\\learning"]
        for script_path in scripts:
            content = Path(script_path).read_text(encoding="utf-8", errors="ignore").lower()
            for needle in forbidden:
                self.assertNotIn(
                    needle, content,
                    f"Found hardcoded drive path '{needle}' in {os.path.basename(script_path)}"
                )

    def test_03_cloud_only_scripts_documented(self):
        """Verify cloud-only scripts (02_scan, 02_export, 05_export) are explicitly documented."""
        cloud_scripts = [
            "02_quantconnect_availability_scan.py",
            "02_quantconnect_export_10_batches.py",
            "05_quantconnect_export_corporate_actions.py",
        ]
        for name in cloud_scripts:
            path = ROOT / "scripts/01_pipeline" / name
            self.assertTrue(path.exists(), f"Missing cloud script: {name}")
            content = path.read_text(encoding="utf-8", errors="ignore")
            self.assertTrue(
                "cloud-only" in content.lower() or "quantconnect research notebook" in content.lower(),
                f"Script {name} is not documented as Cloud-Only"
            )

    def test_04_universe_extraction_output_contracts(self):
        """Verify universe parser outputs: PIT JSON, Constituents CSV (2884), and Quality Report."""
        json_path = ROOT / "data/raw/universe/russell1000_pit_by_year.json"
        csv_path = ROOT / "data/raw/universe/russell1000_constituents.csv"
        rpt_path = ROOT / "data/raw/universe/extraction_quality_report.csv"

        self.assertTrue(json_path.exists(), "russell1000_pit_by_year.json missing")
        self.assertTrue(csv_path.exists(), "russell1000_constituents.csv missing")
        self.assertTrue(rpt_path.exists(), "extraction_quality_report.csv missing")

        with open(json_path, "r", encoding="utf-8") as f:
            pit_data = json.load(f)
        self.assertEqual(len(pit_data), 27, f"Expected 27 years in PIT JSON, got {len(pit_data)}")

        df_const = pd.read_csv(csv_path)
        self.assertEqual(len(df_const), 2884, f"Expected 2884 tickers, got {len(df_const)}")
        self.assertEqual(list(df_const.columns), ["Ticker"], "Columns should be strictly ['Ticker']")

        df_rpt = pd.read_csv(rpt_path)
        self.assertEqual(len(df_rpt), 27, f"Expected 27 rows in quality report, got {len(df_rpt)}")
        self.assertTrue(
            all(df_rpt["reconstitution_window"].str.contains(r"\[01/07/\d{4} to 30/06/\d{4}\]")),
            "Reconstitution window convention [01/07/Y to 30/06/Y+1] violated"
        )

    def test_05_step03_step04_path_parity(self):
        """Verify Step 03 output and Step 04 input reference identical standard path."""
        s03 = (ROOT / "scripts/01_pipeline/03_process_10_batches_to_parquet.py").read_text(encoding="utf-8")
        s04 = (ROOT / "scripts/01_pipeline/04_audit_identity_and_build_canonical_mapping.py").read_text(encoding="utf-8")
        target_name = "russell1000_constituents_daily_ohlcv_1998_2026.parquet"
        target_dir = "constituents_market_data"
        self.assertIn(target_dir, s03)
        self.assertIn(target_name, s03)
        self.assertIn(target_dir, s04)
        self.assertIn(target_name, s04)

    def test_06_step04b_step05_distinct_audit_tables_and_schemas(self):
        """Verify Step 04b and Step 05 write distinct audit tables with distinct schemas."""
        s04b = (ROOT / "scripts/01_pipeline/04b_generate_comprehensive_step3_audits.py").read_text(encoding="utf-8")
        s05 = (ROOT / "scripts/01_pipeline/05_rigorous_pit_membership_reconstruction.py").read_text(encoding="utf-8")
        self.assertIn("temporal_mapping_heuristic_audit.csv", s04b)
        self.assertIn("universe_constituent_temporal_mapping.csv", s05)

        t_04b = ROOT / "docs/Data report/market_data_audit/tables/temporal_mapping_heuristic_audit.csv"
        t_05 = ROOT / "docs/Data report/market_data_audit/tables/universe_constituent_temporal_mapping.csv"
        self.assertTrue(t_04b.exists(), f"Table {t_04b.name} missing")
        self.assertTrue(t_05.exists(), f"Table {t_05.name} missing")

        df04b = pd.read_csv(t_04b)
        df05 = pd.read_csv(t_05)
        self.assertEqual(len(df04b), 26919, "Expected 26919 rows in 04b")
        self.assertEqual(len(df05), 26919, "Expected 26919 rows in 05")
        self.assertNotEqual(list(df04b.columns), list(df05.columns), "Schemas must be distinct")
        self.assertIn("resolution_category", df04b.columns)
        self.assertIn("evidence_level", df05.columns)

    def test_07_coordinate_grid_and_trading_sessions(self):
        """Verify 2D matrices shape (7252, 3711) and exact session breakdown (630 + 5911 + 711 = 7252)."""
        dates_path = ROOT / "data/processed/matrices/matrix_dates_index.parquet"
        sids_path = ROOT / "data/processed/matrices/matrix_columns_sids.parquet"
        self.assertTrue(dates_path.exists())
        self.assertTrue(sids_path.exists())

        df_dates = pd.read_parquet(dates_path)
        df_sids = pd.read_parquet(sids_path)
        self.assertEqual(len(df_dates), 7252)
        self.assertEqual(len(df_sids), 3711)

        dates = pd.to_datetime(df_dates["date"])
        n_warmup = (dates < "2000-07-01").sum()
        n_dev = ((dates >= "2000-07-01") & (dates <= "2023-12-29")).sum()
        n_oos = (dates >= "2024-01-01").sum()
        self.assertEqual(n_warmup, 630)
        self.assertEqual(n_dev, 5911)
        self.assertEqual(n_oos, 711)
        self.assertEqual(n_warmup + n_dev + n_oos, 7252)

    def test_08_configs_base_config_yaml(self):
        """Verify base_config.yaml points to modern Tier 2 warehouse and 2D matrices without legacy paths."""
        cfg_path = ROOT / "configs/base_config.yaml"
        self.assertTrue(cfg_path.exists())
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        data_sec = cfg.get("data", {})
        self.assertIn("adjusted_warehouse", data_sec)
        self.assertIn("matrices_dir", data_sec)
        self.assertNotIn("in_sample_dir", data_sec)
        self.assertNotIn("out_sample_dir", data_sec)
        self.assertEqual(data_sec.get("start_date"), "1998-01-02")
        self.assertEqual(data_sec.get("warmup_end_date"), "2000-06-30")
        self.assertEqual(data_sec.get("dev_start_date"), "2000-07-01")
        self.assertEqual(data_sec.get("dev_end_date"), "2023-12-29")
        self.assertEqual(data_sec.get("oos_start_date"), "2024-01-02")
        self.assertEqual(data_sec.get("oos_end_date"), "2026-10-30")
        self.assertTrue(data_sec.get("oos_strictly_frozen"))

    def test_09_src_archive_v1_and_modern_modules(self):
        """Verify legacy code archived in src/archive_v1/ and modern modules organized in src/."""
        archive_dir = ROOT / "src/archive_v1"
        self.assertTrue(archive_dir.is_dir())
        self.assertTrue((archive_dir / "README.md").exists())
        self.assertTrue((archive_dir / "features/feature_engineer.py").exists())
        self.assertTrue((archive_dir / "data/pit_universe.py").exists())

        modern_dirs = ["data", "features", "quality", "utils"]
        for md in modern_dirs:
            p = ROOT / "src" / md
            self.assertTrue(p.is_dir(), f"src/{md} missing")
            self.assertTrue((p / "__init__.py").exists(), f"src/{md}/__init__.py missing")

    def test_10_documentation_accuracy(self):
        """Verify README.md reflects 711 OOS sessions, hedged terminology, and docs/pipeline_dag.md exists."""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("711", readme)
        self.assertNotIn("1,339", readme)
        self.assertNotIn("1339", readme)

        forbidden_phrases = ["loại bỏ hoàn toàn", "loại bỏ bias hoàn toàn", "triệt tiêu 100% rò rỉ"]
        for fp in forbidden_phrases:
            self.assertNotIn(fp.lower(), readme.lower())

        dag_file = ROOT / "docs/pipeline_dag.md"
        self.assertTrue(dag_file.exists())
        dag_content = dag_file.read_text(encoding="utf-8")
        self.assertIn("Cloud-Only", dag_content)
        self.assertIn("temporal_mapping_heuristic_audit.csv", dag_content)
        self.assertIn("universe_constituent_temporal_mapping.csv", dag_content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
