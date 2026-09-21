"""Lifecycle regression tests; isolate Windows UI, HTTP and local configuration."""

import importlib.util
import sys
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


SOURCE = Path(__file__).parents[1] / "src/true_love_base"


def module(name, **attributes):
    result = types.ModuleType(name)
    result.__dict__.update(attributes)
    return result


def load_source(name, path):
    spec = importlib.util.spec_from_file_location(name, SOURCE / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class ListenerLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.sdk = Mock(nickname="test account")
        self.sdk.AddListenChat.return_value = True
        self.sdk.StopListening.side_effect = lambda **kwargs: self.events.append("stop-sdk")
        self.sdk.GetSubWindow.return_value = None
        self.sdk.SendMsg.return_value = True
        http = module("true_love_base.api.server", enable_http=lambda robot: self.events.append("http"))
        dependencies = {
            "true_love_base": module("true_love_base", __path__=[]),
            "true_love_base.api": module("true_love_base.api", server=http),
            "true_love_base.wxautox4x.wxautox4x": module(
                "true_love_base.wxautox4x.wxautox4x", WeChat=lambda **kwargs: self.sdk
            ),
            "wxautox4.param": module("wxautox4.param", WxParam=type("WxParam", (), {})),
            "true_love_common.chat_msg": module("true_love_common.chat_msg", ChatMsg=object),
            "true_love_common.observability.trace": module(
                "true_love_common.observability.trace", set_trace_id=lambda value: None
            ),
            "true_love_base.models.message_converter": module(
                "true_love_base.models.message_converter", convert_message=Mock()
            ),
            "true_love_base.utils.path_resolver": module(
                "true_love_base.utils.path_resolver", get_wx_imgs_dir=lambda: None
            ),
            "true_love_base.configuration": module(
                "true_love_base.configuration", Config=lambda: types.SimpleNamespace(master_wix="owner")
            ),
            "true_love_base.services": module(
                "true_love_base.services", __path__=[], server_client=types.SimpleNamespace(get_chat=Mock())
            ),
            "true_love_base.services.listen_store": module(
                "true_love_base.services.listen_store", ListenStore=object
            ),
        }
        modules = patch.dict(sys.modules, dependencies)
        modules.start()
        self.addCleanup(modules.stop)
        self.client_module = load_source("lifecycle_client", "core/wxauto_client.py")
        sys.modules["true_love_base.core"] = module(
            "true_love_base.core", WxAutoClient=self.client_module.WxAutoClient
        )
        self.robot_module = load_source("lifecycle_robot", "services/robot.py")
        sys.modules["true_love_base.services.robot"] = self.robot_module
        self.main_module = load_source("lifecycle_main", "main.py")
        self.client = self.client_module.WxAutoClient()

    def test_cleanup_stops_sdk_once_and_preserves_open_chat_windows(self):
        self.client.cleanup()
        self.client.cleanup()

        self.sdk.StopListening.assert_called_once_with(remove=False)
        self.assertFalse(self.client.is_running())

    def test_shutdown_rejects_new_listener_registrations(self):
        self.client.cleanup()

        self.assertFalse(self.client.add_message_listener("group", Mock()))
        self.sdk.AddListenChat.assert_not_called()

    def test_late_sdk_callback_does_not_convert_or_forward_after_cleanup(self):
        callback = Mock()
        internal = self.client._create_internal_callback("group", callback)
        self.client.cleanup()

        internal(types.SimpleNamespace(attr="friend"), object())

        self.client_module.convert_message.assert_not_called()
        callback.assert_not_called()
        self.sdk.SendMsg.assert_not_called()

    def test_cleanup_waits_for_inflight_registration_before_stopping_sdk(self):
        entered = threading.Event()
        release = threading.Event()
        stopping = threading.Event()

        def register(*args):
            entered.set()
            if not release.wait(2):
                raise TimeoutError("test registration was not released")
            self.events.append("registered")
            return True

        self.sdk.AddListenChat.side_effect = register
        registering = threading.Thread(target=self.client.add_message_listener, args=("group", Mock()))

        def stop():
            stopping.set()
            self.client.cleanup()

        closing = threading.Thread(target=stop)
        registering.start()
        try:
            self.assertTrue(entered.wait(2))
            closing.start()
            self.assertTrue(stopping.wait(2))
        finally:
            release.set()
            registering.join(2)
            if closing.ident is not None:
                closing.join(2)
        self.assertFalse(registering.is_alive())
        self.assertFalse(closing.is_alive())
        self.assertEqual(self.events, ["registered", "stop-sdk"])

    def test_robot_drains_accepted_messages_and_ignores_late_callbacks(self):
        robot = self.robot_module.Robot(self.client, Mock())
        delivered = []
        robot.forward_msg = delivered.append
        first = types.SimpleNamespace(msg_hash="1", msg_id="1")
        late = types.SimpleNamespace(msg_hash="2", msg_id="2")
        self.addCleanup(robot.cleanup)

        robot.on_message(first, "group")
        robot.cleanup()
        with self.assertNoLogs("Robot", level="ERROR"):
            robot.on_message(late, "group")

        self.assertEqual(delivered, [first])

    def test_startup_cancellation_skips_remaining_chats(self):
        store = Mock()
        store.load.return_value = ["first", "second"]
        robot = self.robot_module.Robot(self.client, store)
        self.addCleanup(robot.cleanup)
        stopped = threading.Event()

        def register(*args):
            stopped.set()
            return True

        self.sdk.AddListenChat.side_effect = register
        result = robot.load_listen_chats(stop_event=stopped)

        self.assertEqual(result, {"success": ["first"], "failed": []})
        self.assertEqual([call.args[0] for call in self.sdk.AddListenChat.call_args_list], ["first"])

    def test_startup_cancellation_stops_registration_retries(self):
        robot = self.robot_module.Robot(self.client, Mock())
        self.addCleanup(robot.cleanup)
        stopped = threading.Event()

        def register(*args):
            stopped.set()
            return False

        self.sdk.AddListenChat.side_effect = register
        with self.assertLogs("WxAutoClient", level="ERROR"):
            self.assertFalse(robot.add_listen_chat("group", stop_event=stopped))

        self.assertEqual(self.sdk.AddListenChat.call_count, 1)

    def run_main(self, *, fail_loading=False, fail_stopping=False, cancel_loading=False):
        robot = Mock()

        def load(**kwargs):
            self.events.append("load")
            if fail_loading:
                raise RuntimeError("startup failed")
            if cancel_loading:
                shutdown.is_set.return_value = True
            return {"success": ["group"], "failed": []}

        robot.load_listen_chats.side_effect = load
        robot.start_listening.side_effect = lambda: self.events.append("keep-running")
        robot.cleanup.side_effect = lambda: self.events.append("drain")
        if fail_stopping:
            def stop(**kwargs):
                self.events.append("stop-sdk")
                raise RuntimeError("SDK stop failed")
            self.sdk.StopListening.side_effect = stop

        class ImmediateThread:
            def __init__(self, target, **kwargs):
                self.target = target

            def start(self):
                self.target()

        shutdown = Mock()
        shutdown.is_set.return_value = False
        shutdown.wait.return_value = True
        with (
            patch.object(self.main_module, "init_wx", return_value=(self.client, robot)),
            patch.object(self.main_module, "disable_quick_edit"),
            patch.object(self.main_module.signal, "signal"),
            patch.object(self.main_module, "Thread", ImmediateThread, create=True),
            patch.object(self.main_module, "Event", return_value=shutdown),
        ):
            self.main_module.main()
        self.sdk.KeepRunning.assert_not_called()
        return robot

    def test_main_initializes_once_without_keep_running_and_stops_before_draining(self):
        self.run_main()

        self.assertEqual(self.events, ["http", "load", "stop-sdk", "drain"])

    def test_cancelled_startup_does_not_announce_success(self):
        robot = self.run_main(cancel_loading=True)

        robot.send_text_msg.assert_not_called()
        self.assertEqual(self.events, ["http", "load", "stop-sdk", "drain"])

    def test_startup_failure_still_stops_sdk_and_drains_workers(self):
        with self.assertRaisesRegex(RuntimeError, "startup failed"):
            self.run_main(fail_loading=True)

        self.assertEqual(self.events, ["http", "load", "stop-sdk", "drain"])

    def test_sdk_stop_failure_is_visible_and_workers_still_drain(self):
        with self.assertLogs("WxAutoClient", level="ERROR"):
            with self.assertRaisesRegex(RuntimeError, "SDK stop failed"):
                self.run_main(fail_stopping=True)

        self.assertEqual(self.events, ["http", "load", "stop-sdk", "drain"])


if __name__ == "__main__":
    unittest.main()
