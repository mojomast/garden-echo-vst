#!/usr/bin/env python3
"""Exercise fail-closed canonical inventory validation without changing source assets."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import verify_ship_inventory as inv


class InventoryTests(unittest.TestCase):
    def test_real_inventory_and_mutations(self):
        inv.check()
        original = inv.ROOT
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in ("CMakeLists.txt", "submission/INVENTORY.json",
                             "fixtures/recorded-v1/spaces.json", "effects-bank/manifest.json",
                             "src/EffectCore.h", "src/StudyCatalog.h",
                             "src/PluginProcessor.cpp", "src/PluginEditor.cpp"):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original / relative, target)
            for name in inv.KERNELS:
                shutil.copy2(original / f"fixtures/recorded-v1/{name}.wav",
                             root / f"fixtures/recorded-v1/{name}.wav")
            inv.ROOT = root
            try:
                inv.check()
                inventory_path = root / "submission/INVENTORY.json"
                saved = inventory_path.read_bytes()
                for mutation in (lambda d: d["choices"].pop(6),
                                 lambda d: d["choices"].__setitem__(slice(4, 6), d["choices"][4:6][::-1]),
                                 lambda d: d["parameters"]["study"].__setitem__("default", 2)):
                    document = json.loads(saved)
                    mutation(document)
                    inventory_path.write_text(json.dumps(document))
                    with self.assertRaisesRegex(ValueError, "drift"):
                        inv.check()
                inventory_path.write_bytes(saved)
                source = root / "src/EffectCore.h"
                source.write_text(source.read_text().replace('"Terrace Multitap"', '"Renamed"', 1))
                with self.assertRaisesRegex(ValueError, "EffectCore order/name drift"):
                    inv.check()
            finally:
                inv.ROOT = original


if __name__ == "__main__":
    unittest.main()
