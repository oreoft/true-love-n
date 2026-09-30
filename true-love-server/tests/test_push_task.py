"""A push task sends today's pictures, downloading them first when the scheduled run finds them missing."""

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


class PushTaskTests(unittest.TestCase):
    def setUp(self):
        config = types.SimpleNamespace(ALAPI={"token": "token"}, AI_SERVICE={}, HTTP_TOKEN=["token"])
        dependencies = {
            "true_love_server": module("true_love_server", SOURCE),
            "true_love_server.core": module("true_love_server.core", SOURCE / "core", Config=lambda: config),
            "true_love_server.jobs": module("true_love_server.jobs", SOURCE / "jobs"),
            "true_love_server.services": module("true_love_server.services", SOURCE / "services", base_client=Mock()),
        }
        modules = patch.dict(sys.modules, dependencies)
        modules.start()
        self.addCleanup(modules.stop)
        self.jobs = importlib.import_module("true_love_server.jobs.job_process")
        self.sent = Mock()
        self.pictures = set()
        self.downloaded = []
        for patcher in (
            patch.object(self.jobs, "send_daily_notice", self.sent),
            patch.object(self.jobs.time, "sleep"),
            patch.object(self.jobs, "check_image_openable", lambda path: path.split("/")[0] in self.pictures),
            patch.object(self.jobs, "download_moyu_file", lambda: self.download("moyu-jpg")),
            patch.object(self.jobs, "download_zao_bao_file", lambda: self.download("zaobao-jpg")),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def download(self, folder):
        self.downloaded.append(folder)
        self.pictures.add(folder)

    def test_push_goes_to_every_receiver_in_order(self):
        self.jobs.run_task("notice_moyu_schedule", ["委员会", "家人群"])

        self.assertEqual([call.args[0] for call in self.sent.call_args_list], ["委员会", "家人群"])

    def test_us_push_uses_its_own_greeting(self):
        self.jobs.run_task("notice_usa_moyu_schedule", ["湾区群"])

        self.assertIn("阿美莉卡", self.sent.call_args.args[1])

    def test_missing_pictures_are_downloaded_once_before_the_first_receiver(self):
        self.jobs.run_task("notice_moyu_schedule", ["委员会", "家人群"])
        self.jobs.run_task("notice_usa_moyu_schedule", ["湾区群"])

        self.assertEqual(self.downloaded, ["moyu-jpg", "zaobao-jpg"])

    def test_failed_download_still_sends_the_text(self):
        with patch.object(self.jobs, "download_moyu_file", Mock(side_effect=RuntimeError("offline"))):
            self.jobs.run_task("notice_moyu_schedule", ["委员会"])

        self.sent.assert_called_once()

    def test_one_failing_receiver_does_not_stop_the_rest(self):
        self.sent.side_effect = [RuntimeError("wechat busy"), None]

        self.jobs.run_task("notice_moyu_schedule", ["委员会", "家人群"])

        self.assertEqual(self.sent.call_count, 2)


if __name__ == "__main__":
    unittest.main()
