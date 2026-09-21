"""Reproduce the Docker symlink layout without touching real listener data."""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).parents[2]


def load_store(name, service):
    path = ROOT / service / "src" / service.replace("-", "_") / "services/listen_store.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ListenStorePersistenceTests(unittest.TestCase):
    def setUp(self):
        self.server = load_store("server_store_test_subject", "true-love-server")
        self.base = load_store("base_store_test_subject", "true-love-base")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.shared = root / "shared" / "true-love-base"
        self.shared.mkdir(parents=True)
        self.app = root / "app"
        self.app.mkdir()
        self.target = self.shared / "listen_chats.json"
        self.target.write_text(json.dumps(["删除的群", "保留的群"]), encoding="utf-8")
        self.link = self.app / "listen_chats.json"
        self.link.symlink_to(os.path.relpath(self.target, self.app))
        self.store = self.server.ListenStore(str(self.link))

    def test_removal_updates_shared_file_without_replacing_symlink(self):
        self.assertTrue(self.store.remove("删除的群"))

        self.assertTrue(self.link.is_symlink())
        self.assertEqual(json.loads(self.target.read_text(encoding="utf-8")), ["保留的群"])
        self.assertEqual(self.base.ListenStore(str(self.target)).load(), ["保留的群"])

    def test_deleted_listener_stays_deleted_after_container_and_base_restart(self):
        self.assertTrue(self.store.remove("删除的群"))
        # The compose command recreates /app/listen_chats.json on every start.
        self.link.unlink()
        self.link.symlink_to(self.target)
        self.server.ListenStore._instance = None

        restarted_server = self.server.ListenStore(str(self.link))
        restarted_base = self.base.ListenStore(str(self.target))
        self.assertEqual(restarted_server.load(), ["保留的群"])
        self.assertEqual(restarted_base.load(), ["保留的群"])

    def test_addition_also_updates_shared_file(self):
        self.assertTrue(self.store.add("新增的群"))

        self.assertTrue(self.link.is_symlink())
        self.assertEqual(self.base.ListenStore(str(self.target)).load(), ["删除的群", "保留的群", "新增的群"])

    def test_save_follows_dangling_symlink_and_creates_target(self):
        self.target.unlink()

        self.assertTrue(self.store.save(["新列表"]))

        self.assertTrue(self.link.is_symlink())
        self.assertTrue(self.target.is_file())
        self.assertEqual(self.base.ListenStore(str(self.target)).load(), ["新列表"])

    def test_regular_file_storage_still_persists(self):
        self.server.ListenStore._instance = None
        store = self.server.ListenStore(str(self.target))

        self.assertTrue(store.remove("删除的群"))
        self.assertTrue(store.add("新增的群"))

        self.assertEqual(self.base.ListenStore(str(self.target)).load(), ["保留的群", "新增的群"])

    def test_failed_replace_preserves_target_and_cache_and_removes_temp_file(self):
        self.store.load()
        with patch.object(self.server.os, "replace", side_effect=OSError("share unavailable")):
            with self.assertLogs("ListenStore", level="ERROR"):
                self.assertFalse(self.store.remove("删除的群"))

        self.assertTrue(self.link.is_symlink())
        self.assertCountEqual(self.store.list_all(), ["删除的群", "保留的群"])
        self.assertEqual(self.base.ListenStore(str(self.target)).load(), ["删除的群", "保留的群"])
        self.assertEqual(list(Path(self.temp.name).rglob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
