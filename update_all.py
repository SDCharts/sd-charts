"""
update_all.py — Run all chart data scripts and report results.

Called by GitHub Actions on a schedule. Each script is independent;
a failure in one does not stop the others.
"""

import importlib.util
import sys
import traceback
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
CHART_SCRIPTS = sorted(SCRIPTS_DIR.glob("chart_*.py"))


def run_script(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.build_json()


results = {}
for script in CHART_SCRIPTS:
    print(f"\n{'='*60}")
    print(f"Running {script.name}")
    print("=" * 60)
    try:
        run_script(script)
        results[script.name] = "✅ OK"
    except Exception as e:
        results[script.name] = f"❌ FAILED: {e}"
        traceback.print_exc()

print(f"\n{'='*60}")
print("SUMMARY")
print("=" * 60)
for name, status in results.items():
    print(f"  {status}  {name}")

failed = [k for k, v in results.items() if v.startswith("❌")]
if failed:
    print(f"\n{len(failed)} script(s) failed.")
    sys.exit(1)
else:
    print("\nAll scripts completed successfully.")
