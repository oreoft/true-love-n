"""The admin console reads and changes the settings of this server."""

import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


SOURCE = Path(__file__).parents[1] / "src/true_love_server"


def module(name, path=None, **attributes):
    result = types.ModuleType(name)
    if path is not None:
        result.__path__ = [str(path)]
    result.__dict__.update(attributes)
    return result


class FakeSettings:
    """Stands in for the settings service: one text setting, validated like the real one."""

    def __init__(self):
        self.values = {"reply_to": "http://h-m8s:8088"}

    def list_all(self):
        return [{"key": "reply_to", "label": "本机回调地址", "type": "text", "hint": "", "value": self.values["reply_to"]}]

    def update(self, key, value):
        if key not in self.values:
            raise ValueError(f"未知的设置项: {key}")
        self.values[key] = value
        return value


class AdminSettingsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = FakeSettings()
        config = types.SimpleNamespace(AI_SERVICE={}, HTTP_TOKEN=["token"])
        dependencies = {
            "true_love_server": module("true_love_server", SOURCE, Config=lambda: config),
            "true_love_server.api": module("true_love_server.api", SOURCE / "api"),
            "true_love_server.core": module("true_love_server.core", SOURCE / "core", Config=lambda: config),
            "true_love_server.services": module(
                "true_love_server.services", SOURCE / "services", base_client=Mock(), settings_service=self.settings),
            "true_love_server.api.deps": module("true_love_server.api.deps", verify_token=Mock()),
            "true_love_server.core.db_engine": module("true_love_server.core.db_engine", SessionLocal=Mock()),
            "true_love_server.services.group_message_repository": module(
                "true_love_server.services.group_message_repository", GroupMessageRepository=Mock()),
            "true_love_server.services.listen_manager": module(
                "true_love_server.services.listen_manager", get_listen_manager=Mock()),
            "true_love_server.services.loki_client": module(
                "true_love_server.services.loki_client", get_loki_client=Mock()),
            "true_love_server.services.reminder_service": module("true_love_server.services.reminder_service"),
            "true_love_server.services.task_service": module("true_love_server.services.task_service"),
            "true_love_server.services.ai_skill_client": module("true_love_server.services.ai_skill_client"),
        }
        modules = patch.dict(sys.modules, dependencies)
        modules.start()
        self.addCleanup(modules.stop)
        self.routes = importlib.import_module("true_love_server.api.routes")

    async def test_console_gets_every_setting_with_its_value(self):
        response = await self.routes.list_settings()

        self.assertEqual(response.data, {"settings": [{
            "key": "reply_to", "label": "本机回调地址", "type": "text", "hint": "", "value": "http://h-m8s:8088",
        }]})

    async def test_change_made_in_the_console_is_saved(self):
        response = await self.routes.update_setting({"key": "reply_to", "value": "http://win10-m8s:8088"})

        self.assertEqual(self.settings.values["reply_to"], "http://win10-m8s:8088")
        self.assertEqual(response.data, {"key": "reply_to", "value": "http://win10-m8s:8088"})

    async def test_rejected_change_tells_the_console_why(self):
        with self.assertRaisesRegex(self.routes.ValidationException, "未知的设置项: master"):
            await self.routes.update_setting({"key": "master", "value": "alice"})

    async def test_change_without_a_setting_name_is_refused(self):
        with self.assertRaises(self.routes.ValidationException):
            await self.routes.update_setting({"value": "http://win10-m8s:8088"})

        self.assertEqual(self.settings.values["reply_to"], "http://h-m8s:8088")


if __name__ == "__main__":
    unittest.main()
