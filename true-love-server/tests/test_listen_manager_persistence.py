"""The listen list lives in this server's database; base fetches it instead of reading a shared file."""

import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


SOURCE = Path(__file__).parents[1] / "src/true_love_server"


def module(name, path=None, **attributes):
    result = types.ModuleType(name)
    if path is not None:
        result.__path__ = [str(path)]
    result.__dict__.update(attributes)
    return result


class ListenCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sdk = types.SimpleNamespace(execute_wx=AsyncMock(), add_listen_chat=AsyncMock())
        # Import the real store and manager against a throwaway database, without loading config or the app.
        dependencies = {
            "true_love_server": module("true_love_server", SOURCE),
            "true_love_server.core": module("true_love_server.core", SOURCE / "core"),
            "true_love_server.models": module("true_love_server.models", SOURCE / "models"),
            "true_love_server.services": module("true_love_server.services", SOURCE / "services"),
            "true_love_server.core.db_engine": module(
                "true_love_server.core.db_engine", SessionLocal=sessionmaker(bind=engine)),
            "true_love_server.services.base_client": module(
                "true_love_server.services.base_client", get_wechat_client=lambda: self.sdk),
        }
        modules = patch.dict(sys.modules, dependencies)
        modules.start()
        self.addCleanup(modules.stop)
        importlib.import_module("true_love_server.models.listen_chat").Base.metadata.create_all(bind=engine)
        self.store = importlib.import_module("true_love_server.services.listen_store")
        self.manager = importlib.import_module("true_love_server.services.listen_manager").ListenManager()

    def set_sdk_result(self, success):
        result = {"success": success, "data": None, "message": "ok" if success else "listener was not running"}
        self.sdk.execute_wx.return_value = result
        self.sdk.add_listen_chat.return_value = result


class ListenStoreTests(ListenCase):
    def test_chats_are_listed_in_the_order_they_were_added(self):
        for chat in ("群A", "好友B", "群C"):
            self.assertTrue(self.store.add(chat))

        self.assertEqual(self.store.list_all(), ["群A", "好友B", "群C"])

    def test_adding_twice_keeps_one_entry(self):
        self.assertTrue(self.store.add("群A"))
        self.assertFalse(self.store.add("群A"))

        self.assertEqual(self.store.list_all(), ["群A"])

    def test_removing_an_absent_chat_is_harmless(self):
        self.store.add("群A")

        self.assertFalse(self.store.remove("群B"))
        self.assertTrue(self.store.remove("群A"))
        self.assertFalse(self.store.exists("群A"))


class ListenManagerTests(ListenCase):
    def setUp(self):
        super().setUp()
        self.store.add("deleted chat")
        self.store.add("kept chat")

    async def test_chat_is_saved_only_after_base_starts_listening(self):
        self.set_sdk_result(False)
        self.assertFalse((await self.manager.add_listen("new chat"))["success"])
        self.assertFalse(self.store.exists("new chat"))

        self.set_sdk_result(True)
        self.assertTrue((await self.manager.add_listen("new chat"))["success"])
        self.assertEqual(self.store.list_all(), ["deleted chat", "kept chat", "new chat"])

    async def test_removal_is_saved_whether_or_not_base_was_listening(self):
        for sdk_success in (True, False):
            with self.subTest(sdk_success=sdk_success):
                self.store.add("deleted chat")
                self.set_sdk_result(sdk_success)

                result = await self.manager.remove_listen("deleted chat")

                self.assertTrue(result["success"])
                self.assertEqual(self.store.list_all(), ["kept chat"])
        self.sdk.execute_wx.assert_awaited_with("RemoveListenChat", {"nickname": "deleted chat"})

    async def test_reset_keeps_the_saved_chat(self):
        self.set_sdk_result(False)

        result = await self.manager.remove_listen("deleted chat", skip_store=True)

        self.assertTrue(result["success"])
        self.assertEqual(self.store.list_all(), ["deleted chat", "kept chat"])


class ListenRoutesTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.manager = types.SimpleNamespace(refresh_listen=AsyncMock())
        self.store = types.SimpleNamespace(list_all=Mock(return_value=["群A"]))
        self.verify_token = Mock()
        dependencies = {
            "true_love_server": module("true_love_server", SOURCE),
            "true_love_server.api": module("true_love_server.api", SOURCE / "api"),
            "true_love_server.api.deps": module("true_love_server.api.deps", verify_token=self.verify_token),
            "true_love_server.core": module("true_love_server.core", Config=Mock()),
            "true_love_server.services": module(
                "true_love_server.services", SOURCE / "services", base_client=Mock(), settings_service=Mock(),
                listen_store=self.store,
                reminder_service=Mock(), task_service=Mock(), ai_skill_client=Mock()),
            "true_love_server.services.listen_manager": module(
                "true_love_server.services.listen_manager", get_listen_manager=lambda: self.manager),
            "true_love_server.services.loki_client": module(
                "true_love_server.services.loki_client", get_loki_client=Mock()),
            "true_love_server.services.group_message_repository": module(
                "true_love_server.services.group_message_repository", GroupMessageRepository=Mock()),
        }
        modules = patch.dict(sys.modules, dependencies)
        modules.start()
        self.addCleanup(modules.stop)
        self.routes = importlib.import_module("true_love_server.api.routes")

    async def test_base_gets_the_list_with_its_token(self):
        response = await self.routes.listen_list({"token": "token"})

        self.verify_token.assert_called_once_with("token")
        self.assertEqual(response.data, {"chats": ["群A"]})


if __name__ == "__main__":
    unittest.main()
