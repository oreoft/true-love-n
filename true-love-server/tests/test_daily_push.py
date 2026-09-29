"""The daily pushes go to the groups chosen in the admin console, read again on every run."""

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


class DailyPushTests(unittest.TestCase):
    def setUp(self):
        self.settings = {"moyu_groups": [], "usa_moyu_groups": []}
        config = types.SimpleNamespace(ALAPI={"token": "token"}, AI_SERVICE={}, HTTP_TOKEN=["token"])
        dependencies = {
            "true_love_server": module("true_love_server", SOURCE),
            "true_love_server.core": module("true_love_server.core", SOURCE / "core", Config=lambda: config),
            "true_love_server.jobs": module("true_love_server.jobs", SOURCE / "jobs"),
            "true_love_server.services": module(
                "true_love_server.services", SOURCE / "services", base_client=Mock(),
                settings_service=types.SimpleNamespace(get=lambda key: list(self.settings[key]))),
        }
        modules = patch.dict(sys.modules, dependencies)
        modules.start()
        self.addCleanup(modules.stop)
        self.jobs = importlib.import_module("true_love_server.jobs.job_process")
        self.sent = Mock()
        for patcher in (
            patch.object(self.jobs, "send_daily_notice", self.sent),
            patch.object(self.jobs.time, "sleep"),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def receivers(self):
        return [call.args[0] for call in self.sent.call_args_list]

    def test_daily_push_goes_to_every_group_chosen_in_the_console(self):
        self.settings["moyu_groups"] = ["委员会", "家人群"]
        self.settings["usa_moyu_groups"] = ["湾区群"]

        self.jobs.notice_moyu_schedule()

        self.assertEqual(self.receivers(), ["委员会", "家人群"])

    def test_groups_changed_in_the_console_apply_to_the_next_run_without_a_restart(self):
        self.settings["moyu_groups"] = ["委员会"]
        self.jobs.notice_moyu_schedule()
        self.settings["moyu_groups"] = ["家人群"]

        self.jobs.notice_moyu_schedule()

        self.assertEqual(self.receivers(), ["委员会", "家人群"])

    def test_us_push_goes_to_its_own_groups_on_us_central_time(self):
        self.settings["moyu_groups"] = ["委员会"]
        self.settings["usa_moyu_groups"] = ["湾区群"]

        self.jobs.notice_usa_moyu_schedule()

        self.assertEqual(self.receivers(), ["湾区群"])
        self.assertEqual(self.sent.call_args.kwargs["tz"], "America/Chicago")

    def test_nothing_is_pushed_when_no_group_is_chosen(self):
        self.jobs.notice_moyu_schedule()
        self.jobs.notice_usa_moyu_schedule()

        self.sent.assert_not_called()


if __name__ == "__main__":
    unittest.main()
