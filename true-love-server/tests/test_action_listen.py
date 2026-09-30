"""AI adds and removes WeChat listeners through the server."""

import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch


SOURCE = Path(__file__).parents[1] / "src/true_love_server"


def module(name, path=None, **attributes):
    result = types.ModuleType(name)
    if path is not None:
        result.__path__ = [str(path)]
    result.__dict__.update(attributes)
    return result


class ActionListenTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.manager = types.SimpleNamespace(add_listen=AsyncMock(), remove_listen=AsyncMock())
        dependencies = {
            "true_love_server": module("true_love_server", SOURCE, Config=Mock()),
            "true_love_server.api": module("true_love_server.api", SOURCE / "api"),
            "true_love_server.api.deps": module("true_love_server.api.deps", verify_token=Mock()),
            "true_love_server.services": module(
                "true_love_server.services", SOURCE / "services", base_client=Mock(), reminder_service=Mock()),
            "true_love_server.services.listen_manager": module(
                "true_love_server.services.listen_manager", get_listen_manager=lambda: self.manager),
        }
        modules = patch.dict(sys.modules, dependencies)
        modules.start()
        self.addCleanup(modules.stop)
        self.routes = importlib.import_module("true_love_server.api.action_routes")

    async def test_listener_is_added_and_the_result_returned(self):
        self.manager.add_listen.return_value = {"success": True, "message": "ok"}

        response = await self.routes.action_listen_add({"token": "token", "chat_name": "委员会"})

        self.manager.add_listen.assert_awaited_once_with("委员会")
        self.assertEqual(response.data, {"success": True, "message": "ok"})

    async def test_failed_removal_tells_the_ai_why(self):
        self.manager.remove_listen.return_value = {"success": False, "message": "not listening"}

        with self.assertRaisesRegex(self.routes.ValidationException, "not listening"):
            await self.routes.action_listen_remove({"token": "token", "chat_name": "委员会"})

        self.manager.remove_listen.assert_awaited_once_with("委员会")


if __name__ == "__main__":
    unittest.main()
