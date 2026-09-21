"""Shared dirs are Docker symlinks whose targets may not exist yet on a fresh host."""

import importlib.util
import tempfile
import unittest
from pathlib import Path


FS_PATH = Path(__file__).parents[1] / "src" / "true_love_server" / "core" / "fs.py"


def load_fs():
    spec = importlib.util.spec_from_file_location("fs_test_subject", FS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EnsureDirTests(unittest.TestCase):
    def setUp(self):
        self.fs = load_fs()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.shared = root / "shared" / "true-love-base"
        self.shared.mkdir(parents=True)
        self.app = root / "app"
        self.app.mkdir()

    def dangling_link(self, name):
        link = self.app / name
        link.symlink_to(self.shared / name)
        return link

    def test_creates_missing_target_behind_symlink(self):
        link = self.dangling_link("gen-img")

        self.fs.ensure_dir(link)

        self.assertTrue((self.shared / "gen-img").is_dir())
        self.assertTrue(link.is_symlink())

    def test_accepts_trailing_slash(self):
        link = self.dangling_link("moyu-jpg")

        self.fs.ensure_dir(f"{link}/")

        self.assertTrue((self.shared / "moyu-jpg").is_dir())

    def test_plain_dir_is_created_once_and_reused(self):
        plain = self.app / "files-save"

        self.fs.ensure_dir(plain)
        self.fs.ensure_dir(plain)

        self.assertTrue(plain.is_dir())
        self.assertFalse(plain.is_symlink())


if __name__ == "__main__":
    unittest.main()
