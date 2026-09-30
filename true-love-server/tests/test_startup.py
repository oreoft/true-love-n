"""What the server does before it starts serving."""

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


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.config = types.SimpleNamespace(HTTP={"host": "127.0.0.1", "port": 8088})
        self.send_to_master = AsyncMock(
            side_effect=lambda content: self.events.append(("master", content)) or (True, ""))
        self.send_text = AsyncMock(return_value=(True, ""))
        dependencies = {
            "true_love_server": module("true_love_server", SOURCE),
            "true_love_server.api": module("true_love_server.api", create_app=Mock()),
            "true_love_server.core": module("true_love_server.core", SOURCE / "core", Config=lambda: self.config),
            "true_love_server.core.db_engine": module(
                "true_love_server.core.db_engine", init_db=lambda: self.events.append(("db", None))),
            "true_love_server.services": module(
                "true_love_server.services", SOURCE / "services",
                base_client=types.SimpleNamespace(send_to_master=self.send_to_master, send_text=self.send_text)),
            "true_love_server.services.scheduler_service": module(
                "true_love_server.services.scheduler_service",
                start_scheduler=lambda: self.events.append(("scheduler", None))),
        }
        modules = patch.dict(sys.modules, dependencies)
        modules.start()
        self.addCleanup(modules.stop)
        self.main = importlib.import_module("true_love_server.main")
        for patcher in (patch.object(self.main.uvicorn, "run"), patch.object(self.main.signal, "signal")):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_master_is_told_the_server_started_without_the_server_knowing_who_that_is(self):
        self.main.main()

        self.assertEqual(self.events[-1], ("master", "真爱粉server启动成功..."))
        self.send_text.assert_not_awaited()
        self.main.uvicorn.run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
