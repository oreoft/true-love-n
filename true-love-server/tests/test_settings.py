"""Settings that differ per bot live in this server's database and are changed from the admin console."""

import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

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


class SettingsCase(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        # Import the real settings code against a throwaway database, without loading config or the app.
        dependencies = {
            "true_love_server": module("true_love_server", SOURCE),
            "true_love_server.core": module("true_love_server.core", SOURCE / "core"),
            "true_love_server.models": module("true_love_server.models", SOURCE / "models"),
            "true_love_server.services": module("true_love_server.services", SOURCE / "services"),
            "true_love_server.core.db_engine": module(
                "true_love_server.core.db_engine", SessionLocal=sessionmaker(bind=engine)),
        }
        modules = patch.dict(sys.modules, dependencies)
        modules.start()
        self.addCleanup(modules.stop)
        self.settings = importlib.import_module("true_love_server.services.settings_service")
        importlib.import_module("true_love_server.models.setting").Base.metadata.create_all(bind=engine)



class SettingsTests(SettingsCase):
    def test_server_that_was_never_configured_has_no_reply_address(self):
        self.assertEqual(self.settings.get("reply_to"), "")

    def test_reply_address_is_stored_without_a_trailing_slash(self):
        self.settings.update("reply_to", " http://win10-m8s:8088/ ")

        self.assertEqual(self.settings.get("reply_to"), "http://win10-m8s:8088")

    def test_reply_address_must_be_a_web_address(self):
        for value in ("win10-m8s:8088", "ftp://win10-m8s", ["http://win10-m8s:8088"]):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.settings.update("reply_to", value)

        self.assertEqual(self.settings.get("reply_to"), "")

    def test_reply_address_can_be_cleared(self):
        self.settings.update("reply_to", "http://win10-m8s:8088")
        self.settings.update("reply_to", "")

        self.assertEqual(self.settings.get("reply_to"), "")

    def test_unknown_setting_is_rejected(self):
        with self.assertRaises(ValueError):
            self.settings.update("master", "alice")
        with self.assertRaises(ValueError):
            self.settings.get("master")

    def test_console_lists_every_setting_with_its_current_value(self):
        self.settings.update("reply_to", "http://win10-m8s:8088")

        listed = {item["key"]: item for item in self.settings.list_all()}

        self.assertEqual(sorted(listed), ["reply_to"])
        self.assertEqual(listed["reply_to"]["value"], "http://win10-m8s:8088")
        self.assertEqual(listed["reply_to"]["type"], "text")
        self.assertTrue(listed["reply_to"]["label"])


if __name__ == "__main__":
    unittest.main()
