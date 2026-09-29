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
    def test_server_that_was_never_configured_has_no_groups_and_no_reply_address(self):
        self.assertEqual(self.settings.get("moyu_groups"), [])
        self.assertEqual(self.settings.get("usa_moyu_groups"), [])
        self.assertEqual(self.settings.get("reply_to"), "")

    def test_saved_groups_are_what_the_next_reader_gets(self):
        self.settings.update("moyu_groups", ["委员会", "家人群"])

        self.assertEqual(self.settings.get("moyu_groups"), ["委员会", "家人群"])
        self.assertEqual(self.settings.get("usa_moyu_groups"), [])

    def test_saving_again_replaces_the_previous_value(self):
        self.settings.update("moyu_groups", ["委员会", "家人群"])
        self.settings.update("moyu_groups", ["家人群"])

        self.assertEqual(self.settings.get("moyu_groups"), ["家人群"])

    def test_group_names_are_trimmed_and_blank_or_repeated_ones_dropped(self):
        self.settings.update("moyu_groups", [" 委员会 ", "", "家人群", "委员会", "   "])

        self.assertEqual(self.settings.get("moyu_groups"), ["委员会", "家人群"])

    def test_groups_must_be_given_as_a_list(self):
        with self.assertRaises(ValueError):
            self.settings.update("moyu_groups", "委员会")

        self.assertEqual(self.settings.get("moyu_groups"), [])

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
        self.settings.update("usa_moyu_groups", ["湾区群"])

        listed = {item["key"]: item for item in self.settings.list_all()}

        self.assertEqual(sorted(listed), ["moyu_groups", "reply_to", "usa_moyu_groups"])
        self.assertEqual(listed["usa_moyu_groups"]["value"], ["湾区群"])
        self.assertEqual(listed["usa_moyu_groups"]["type"], "list")
        self.assertEqual(listed["reply_to"]["value"], "")
        self.assertEqual(listed["reply_to"]["type"], "text")
        self.assertTrue(all(item["label"] for item in listed.values()))


class ImportFromConfigTests(SettingsCase):
    """What used to be written in config.yaml is carried over once, so an upgrade changes nothing by itself."""

    def test_groups_from_the_configuration_file_are_carried_over(self):
        self.settings.import_from_config(
            {"notice_moyu_schedule": ["委员会", "家人群"], "notice_usa_moyu_schedule": ["湾区群"], "test": ["x"]},
        )

        self.assertEqual(self.settings.get("moyu_groups"), ["委员会", "家人群"])
        self.assertEqual(self.settings.get("usa_moyu_groups"), ["湾区群"])

    def test_value_changed_in_the_console_is_not_overwritten_by_the_next_start(self):
        legacy = {"notice_moyu_schedule": ["委员会", "家人群"]}
        self.settings.import_from_config(legacy)
        self.settings.update("moyu_groups", ["家人群"])

        self.settings.import_from_config(legacy)

        self.assertEqual(self.settings.get("moyu_groups"), ["家人群"])

    def test_groups_emptied_in_the_console_stay_empty_after_the_next_start(self):
        legacy = {"notice_moyu_schedule": ["委员会"]}
        self.settings.import_from_config(legacy)
        self.settings.update("moyu_groups", [])

        self.settings.import_from_config(legacy)

        self.assertEqual(self.settings.get("moyu_groups"), [])

    def test_server_without_the_old_configuration_starts_with_nothing(self):
        for legacy in (None, {}, {"notice_moyu_schedule": None}):
            with self.subTest(legacy=legacy):
                self.settings.import_from_config(legacy)

                self.assertEqual(self.settings.get("moyu_groups"), [])


if __name__ == "__main__":
    unittest.main()
