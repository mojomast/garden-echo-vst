import unittest
from sanitize_ci_evidence import sanitize


class EvidencePathChecks(unittest.TestCase):
    def test_linux_paths_and_test_values(self):
        home = "/" + "home/build-owner"
        root = home + "/work/garden-echo-vst"
        text = f"Test project {root}/build/native\n100% tests passed, 0 failed\nTotal 191.74 sec\n{home}/cache\n"
        actual = sanitize(text, root, home)
        self.assertIn("/workspace/garden-echo-vst/build/native", actual)
        self.assertIn("/runner-home/cache", actual)
        self.assertIn("100% tests passed, 0 failed\nTotal 191.74 sec", actual)

    def test_windows_separator_variants(self):
        home = "C:" + "\\" + "Users" + "\\" + "build-owner"
        root = home + "\\work\\garden-echo-vst"
        text = root + "\\build\n" + root.replace("\\", "/") + "/build\n"
        actual = sanitize(text, root, home)
        self.assertNotIn("build-owner", actual)
        self.assertEqual(actual.count("/workspace/garden-echo-vst"), 2)

    def test_unrelated_values_and_hashes_are_unchanged(self):
        self.assertEqual(sanitize("SHA-256 " + "a" * 64, "/workspace/project"), "SHA-256 " + "a" * 64)


if __name__ == "__main__":
    unittest.main()
