"""When several servers share this AI, every reply goes back through the server that delivered the message."""

import asyncio
import types
import unittest
from unittest.mock import patch

from fastapi import BackgroundTasks

from true_love_common.chat_msg import ChatMsg
from true_love_common.http.client import HttpResult

from true_love_ai.agent import server_client
from true_love_ai.api import trigger_routes


class AnsweringAgent:
    """Stands in for the agent loop: answers the sender with one text."""

    async def run(self, msg):
        await asyncio.sleep(0)
        await server_client.send_text(msg.sender_id, "hi")


class CrashingAgent:
    async def run(self, msg):
        raise RuntimeError("llm exploded")


def accepted(url):
    return HttpResult(
        method="POST", url=url, ok=True, status_code=200, headers={}, text="", content=b"",
        data={"code": 0}, cost_ms=1,
    )


class ReplyRoutingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        config = types.SimpleNamespace(
            base_server=types.SimpleNamespace(host="http://default.test:8088/"),
            http=types.SimpleNamespace(token=["token"]),
        )
        self.posted = []
        self.agent = AnsweringAgent()

        async def post(url, payload, timeout=None):
            self.posted.append((url, payload.get("receiver")))
            return accepted(url)

        for patcher in (
            patch.object(server_client, "get_config", return_value=config),
            patch.object(server_client, "async_post_json", post),
            patch.object(trigger_routes, "verify_token", return_value=True),
            patch("true_love_ai.agent.skills.ensure_skills_loaded"),
            patch("true_love_ai.agent.agent_loop.get_agent_loop", side_effect=lambda: self.agent),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    async def trigger(self, sender, **extra):
        tasks = BackgroundTasks()
        response = await trigger_routes.trigger(
            {"token": "token", "msg": ChatMsg(sender_id=sender).to_dict(), **extra}, tasks,
        )
        await tasks()
        return response

    async def test_reply_goes_back_through_the_server_named_by_the_trigger(self):
        await self.trigger("alice", reply_to="http://server-b.test:8088")

        self.assertEqual(self.posted, [("http://server-b.test:8088/action/send", "alice")])

    async def test_trigger_without_a_reply_address_is_answered_through_the_default_server(self):
        await self.trigger("alice")

        self.assertEqual(self.posted, [("http://default.test:8088/action/send", "alice")])

    async def test_triggers_handled_at_the_same_time_keep_their_own_servers(self):
        await asyncio.gather(
            asyncio.create_task(self.trigger("alice", reply_to="http://server-a.test:8088")),
            asyncio.create_task(self.trigger("bob", reply_to="http://server-b.test:8088")),
            asyncio.create_task(self.trigger("carol")),
        )

        self.assertEqual(sorted(self.posted), [
            ("http://default.test:8088/action/send", "carol"),
            ("http://server-a.test:8088/action/send", "alice"),
            ("http://server-b.test:8088/action/send", "bob"),
        ])

    async def test_reply_address_that_is_not_a_web_address_is_ignored(self):
        for reply_to in ("server-b.test:8088", "ftp://server-b.test", "", None, 8088):
            with self.subTest(reply_to=reply_to):
                self.posted.clear()

                with self.assertNoLogs("ServerClient", level="ERROR"):
                    await self.trigger("alice", reply_to=reply_to)

                self.assertEqual(self.posted, [("http://default.test:8088/action/send", "alice")])

    async def test_failure_notice_also_goes_back_through_the_same_server(self):
        self.agent = CrashingAgent()

        with self.assertLogs("TriggerRoutes", level="ERROR"):
            await self.trigger("alice", reply_to="http://server-b.test:8088")

        self.assertEqual(self.posted, [("http://server-b.test:8088/action/send", "alice")])


if __name__ == "__main__":
    unittest.main()
