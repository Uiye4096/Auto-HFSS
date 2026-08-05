import json
import tempfile
import unittest
from pathlib import Path

from hfss_automation.config import load_config


class ConfigTests(unittest.TestCase):
    def test_loads_relative_paths_and_environment_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "hfss": {
                            "aedt_root": "default/aedt",
                            "ironpython": "default/ipy.exe",
                            "max_parallel": 1,
                        },
                        "project": {
                            "project_file": "models/base.aedt",
                            "design": "D1",
                            "setup": "Setup1",
                            "sweep": "Sweep1",
                            "ports": 3,
                            "output_root": "runs",
                            "variables": {"L": "1mm"},
                        },
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(
                config_path,
                env={
                    "HFSS_AEDT_ROOT": str(root / "custom_aedt"),
                    "HFSS_IRONPYTHON": str(root / "custom_ipy.exe"),
                    "HFSS_MAX_PARALLEL": "4",
                },
            )

            self.assertEqual(config.hfss.max_parallel, 4)
            self.assertEqual(config.hfss.aedt_root, root / "custom_aedt")
            self.assertEqual(config.project.project_file, root / "models" / "base.aedt")
            self.assertEqual(config.project.variables["L"], "1mm")

    def test_rejects_non_positive_port_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "hfss": {"aedt_root": "a", "ironpython": "b"},
                        "project": {
                            "project_file": "base.aedt",
                            "design": "D",
                            "setup": "S",
                            "sweep": "W",
                            "ports": 0,
                        },
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_config(path, env={})


if __name__ == "__main__":
    unittest.main()
