"""Listener removal must report whether the restart source was actually saved."""

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


SOURCE = Path(__file__).parents[1] / "src/true_love_server/services"


def load_source(name, filename):
    spec = importlib.util.spec_from_file_location(name, SOURCE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ListenManagerPersistenceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "listen_chats.json"
        self.path.write_text('["deleted chat", "kept chat"]', encoding="utf-8")

        # Load the real manager and store without importing the application,
        # which initializes configuration and HTTP routes at package import.
        package = types.ModuleType("listen_manager_persistence")
        package.__path__ = []
        self.sdk = types.SimpleNamespace(execute_wx=AsyncMock())
        base_client = types.ModuleType("listen_manager_persistence.base_client")
        base_client.get_wechat_client = lambda: self.sdk
        self.store_module = load_source(
            "listen_manager_persistence.listen_store", "listen_store.py"
        )
        self.store = self.store_module.ListenStore(str(self.path))
        self.store.load()
        dependencies = {
            package.__name__: package,
            base_client.__name__: base_client,
            self.store_module.__name__: self.store_module,
        }
        with patch.dict(sys.modules, dependencies):
            manager_module = load_source(
                "listen_manager_persistence.listen_manager", "listen_manager.py"
            )
        self.manager = manager_module.ListenManager()

    def set_sdk_result(self, success):
        self.sdk.execute_wx.return_value = {
            "success": success,
            "data": None,
            "message": "ok" if success else "listener was not running",
        }

    def assert_saved_chats(self, expected):
        self.assertEqual(expected, json.loads(self.path.read_text(encoding="utf-8")))
        self.assertEqual(expected, self.store.load())

    async def test_sdk_success_removes_restart_record(self):
        self.set_sdk_result(True)

        result = await self.manager.remove_listen("deleted chat")

        self.assertTrue(result["success"])
        self.assert_saved_chats(["kept chat"])
        self.sdk.execute_wx.assert_awaited_once_with(
            "RemoveListenChat", {"nickname": "deleted chat"}
        )

    async def test_sdk_failure_still_removes_restart_record(self):
        self.set_sdk_result(False)

        result = await self.manager.remove_listen("deleted chat")

        self.assertTrue(result["success"])
        self.assert_saved_chats(["kept chat"])

    async def test_failed_persistence_is_reported_after_sdk_success(self):
        await self.assert_failed_persistence(sdk_success=True)

    async def test_failed_persistence_is_reported_after_sdk_failure(self):
        await self.assert_failed_persistence(sdk_success=False)

    async def assert_failed_persistence(self, sdk_success):
        self.set_sdk_result(sdk_success)
        with patch.object(
            self.store_module.os, "replace", side_effect=PermissionError("read only")
        ):
            result = await self.manager.remove_listen("deleted chat")

        self.assertFalse(result["success"])
        self.assertIn("persist", result["message"].lower())
        self.assertIn("deleted chat", result["message"])
        self.assertTrue(self.store.exists("deleted chat"))
        self.assert_saved_chats(["deleted chat", "kept chat"])

    async def test_missing_record_is_idempotent_for_either_sdk_result(self):
        for sdk_success in (True, False):
            with self.subTest(sdk_success=sdk_success):
                self.set_sdk_result(sdk_success)

                result = await self.manager.remove_listen("already absent")

                self.assertTrue(result["success"])
                self.assert_saved_chats(["deleted chat", "kept chat"])

    async def test_reset_keeps_restart_record_for_either_sdk_result(self):
        for sdk_success in (True, False):
            with self.subTest(sdk_success=sdk_success):
                self.set_sdk_result(sdk_success)

                result = await self.manager.remove_listen("deleted chat", skip_store=True)

                self.assertTrue(result["success"])
                self.assert_saved_chats(["deleted chat", "kept chat"])


if __name__ == "__main__":
    unittest.main()
