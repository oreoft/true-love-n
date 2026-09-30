"""Scheduled tasks push a chosen job to a list of receivers, once or every day, and survive in this server's database."""

import importlib
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytz
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger  # noqa: F401  loaded before sys.modules is patched, so pickling finds the same class
from apscheduler.triggers.date import DateTrigger  # noqa: F401
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool


SOURCE = Path(__file__).parents[1] / "src/true_love_server"


def module(name, path=None, **attributes):
    result = types.ModuleType(name)
    if path is not None:
        result.__path__ = [str(path)]
    result.__dict__.update(attributes)
    return result


class TaskServiceCase(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.scheduler = BackgroundScheduler(
            jobstores={"default": SQLAlchemyJobStore(engine=engine), "memory": MemoryJobStore()}, timezone="UTC")
        # A stand-in job_process: its own functions can be run by name, imported helpers and private ones cannot.
        self.calls = []
        job_process = module("true_love_server.jobs.job_process", Mock=Mock)

        def notice_moyu_schedule(room_id):
            self.calls.append(("notice_moyu_schedule", room_id))
            if room_id == "坏群":
                raise RuntimeError("wechat busy")

        def notice_usa_moyu_schedule(room_id):
            self.calls.append(("notice_usa_moyu_schedule", room_id))

        def download_moyu_file():
            self.calls.append(("download_moyu_file", None))

        def _private(room_id):
            self.calls.append(("_private", room_id))

        for func in (notice_moyu_schedule, notice_usa_moyu_schedule, download_moyu_file, _private):
            func.__module__ = job_process.__name__
            setattr(job_process, func.__name__, func)
        # Real task code against a throwaway database and a paused scheduler: jobs are stored, nothing fires.
        dependencies = {
            "true_love_server": module("true_love_server", SOURCE),
            "true_love_server.core": module("true_love_server.core", SOURCE / "core"),
            "true_love_server.services": module("true_love_server.services", SOURCE / "services"),
            "true_love_server.services.scheduler_service": module(
                "true_love_server.services.scheduler_service", scheduler=self.scheduler),
            "true_love_server.jobs": module("true_love_server.jobs", SOURCE / "jobs"),
            "true_love_server.jobs.job_process": job_process,
        }
        modules = patch.dict(sys.modules, dependencies)
        modules.start()
        self.addCleanup(modules.stop)
        self.tasks = importlib.import_module("true_love_server.services.task_service")
        sleep = patch.object(self.tasks.time, "sleep")
        sleep.start()
        self.addCleanup(sleep.stop)
        self.scheduler.start(paused=True)
        self.addCleanup(self.scheduler.shutdown, wait=False)

    def daily(self, at="09:05", tz="Asia/Shanghai"):
        return {"mode": "daily", "time": at, "timezone": tz}

    def next_run(self, task):
        return datetime.fromisoformat(task["next_run_time"])


class TaskTests(TaskServiceCase):
    def test_daily_task_runs_next_at_that_time_in_its_timezone(self):
        for at, tz in (("09:05", "Asia/Shanghai"), ("08:00", "America/Chicago")):
            with self.subTest(tz=tz):
                task = self.tasks.add_task("notice_moyu_schedule", ["委员会"], self.daily(at, tz))

                local = self.next_run(task).astimezone(pytz.timezone(tz))
                self.assertEqual(local.strftime("%H:%M"), at)
                self.assertLess(self.next_run(task) - datetime.now(timezone.utc), timedelta(days=1))

    def test_once_task_runs_at_the_chosen_moment(self):
        run_at = (datetime.now(timezone.utc) + timedelta(hours=3)).replace(microsecond=0)

        task = self.tasks.add_task("notice_moyu_schedule", ["委员会"], {"mode": "once", "run_at": run_at.isoformat()})

        self.assertEqual(self.next_run(task), run_at)
        self.assertEqual(task["schedule"]["mode"], "once")

    def test_console_lists_tasks_with_receivers_and_the_job_method_name(self):
        self.tasks.add_task("notice_usa_moyu_schedule", [" 湾区群 ", "", "委员会", "湾区群"], self.daily("08:00", "America/Chicago"))

        [task] = self.tasks.list_tasks()

        self.assertEqual(task["job_name"], "notice_usa_moyu_schedule")
        self.assertEqual(task["receivers"], ["湾区群", "委员会"])
        self.assertEqual(task["schedule"], {"mode": "daily", "time": "08:00", "timezone": "America/Chicago"})

    def test_reminders_are_not_listed_as_tasks(self):
        self.scheduler.add_job(print, "date", run_date=datetime.now(timezone.utc) + timedelta(hours=1),
                               id="reminder_委员会_1")

        self.assertEqual(self.tasks.list_tasks(), [])

    def test_invalid_forms_are_refused(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        cases = {
            "unknown job": ("no_such_job", ["委员会"], self.daily()),
            "private function": ("_private", ["委员会"], self.daily()),
            "imported helper": ("Mock", ["委员会"], self.daily()),
            "no receiver": ("notice_moyu_schedule", ["", " "], self.daily()),
            "receivers not a list": ("notice_moyu_schedule", "委员会", self.daily()),
            "bad time": ("notice_moyu_schedule", ["委员会"], self.daily("25:00")),
            "bad timezone": ("notice_moyu_schedule", ["委员会"], self.daily("09:05", "Mars/Olympus")),
            "past moment": ("notice_moyu_schedule", ["委员会"], {"mode": "once", "run_at": past}),
            "moment without timezone": ("notice_moyu_schedule", ["委员会"], {"mode": "once", "run_at": future[:19]}),
            "no mode": ("notice_moyu_schedule", ["委员会"], {}),
        }
        for name, args in cases.items():
            with self.subTest(name):
                with self.assertRaises(ValueError):
                    self.tasks.add_task(*args)

        self.assertEqual(self.tasks.list_tasks(), [])

    def test_console_offers_every_function_of_job_process(self):
        self.assertEqual(self.tasks.job_names(), ["notice_moyu_schedule", "notice_usa_moyu_schedule", "download_moyu_file"])

    def test_function_without_a_parameter_needs_no_receiver(self):
        task = self.tasks.add_task("download_moyu_file", [], self.daily("08:30"))
        job = self.scheduler.get_job(task["task_id"])

        job.func(**job.kwargs)

        self.assertEqual(self.calls, [("download_moyu_file", None)])

    def test_job_name_is_trimmed_before_it_is_looked_up(self):
        task = self.tasks.add_task(" notice_moyu_schedule ", ["委员会"], self.daily())

        self.assertEqual(task["job_name"], "notice_moyu_schedule")

    def test_changing_a_task_keeps_its_id_and_replaces_everything_else(self):
        task = self.tasks.add_task("notice_moyu_schedule", ["委员会"], self.daily())

        self.tasks.update_task(task["task_id"], "notice_usa_moyu_schedule", ["湾区群"], self.daily("08:00", "America/Chicago"))

        [changed] = self.tasks.list_tasks()
        self.assertEqual(changed["task_id"], task["task_id"])
        self.assertEqual((changed["job_name"], changed["receivers"]), ("notice_usa_moyu_schedule", ["湾区群"]))

    def test_deleted_task_is_gone(self):
        task = self.tasks.add_task("notice_moyu_schedule", ["委员会"], self.daily())

        self.tasks.delete_task(task["task_id"])

        self.assertEqual(self.tasks.list_tasks(), [])
        with self.assertRaises(ValueError):
            self.tasks.delete_task(task["task_id"])

    def test_reminder_cannot_be_changed_through_the_task_page(self):
        self.scheduler.add_job(print, "date", run_date=datetime.now(timezone.utc) + timedelta(hours=1),
                               id="reminder_委员会_1")

        for call in (lambda: self.tasks.delete_task("reminder_委员会_1"), lambda: self.tasks.run_now("reminder_委员会_1")):
            with self.assertRaises(ValueError):
                call()

    def test_running_now_starts_an_extra_run_and_keeps_the_schedule(self):
        task = self.tasks.add_task("notice_moyu_schedule", ["委员会"], self.daily())
        extra = []
        with patch.object(self.tasks, "_start", extra.append):
            self.tasks.run_now(task["task_id"])

        self.assertEqual([(run["job_name"], run["receivers"]) for run in extra], [("notice_moyu_schedule", ["委员会"])])
        self.assertEqual(self.tasks.list_tasks()[0]["next_run_time"], task["next_run_time"])

    def test_ai_trigger_runs_every_task_of_that_job(self):
        self.tasks.add_task("notice_moyu_schedule", ["委员会"], self.daily())
        self.tasks.add_task("notice_moyu_schedule", ["家人群"], self.daily("12:00"))
        self.tasks.add_task("notice_usa_moyu_schedule", ["湾区群"], self.daily("08:00", "America/Chicago"))
        extra = []
        with patch.object(self.tasks, "_start", extra.append):
            started = self.tasks.run_by_job_name("notice_moyu_schedule")

        self.assertEqual(len(started), 2)
        self.assertEqual(sorted(run["receivers"][0] for run in extra), ["委员会", "家人群"])
        with self.assertRaises(ValueError):
            self.tasks.run_by_job_name("no_such_job")

    def test_scheduled_run_calls_the_function_once_per_receiver_in_order(self):
        task = self.tasks.add_task("notice_moyu_schedule", ["委员会", "家人群"], self.daily())
        job = self.scheduler.get_job(task["task_id"])

        job.func(**job.kwargs)

        self.assertEqual(self.calls, [("notice_moyu_schedule", "委员会"), ("notice_moyu_schedule", "家人群")])

    def test_one_failing_receiver_does_not_stop_the_rest(self):
        task = self.tasks.add_task("notice_moyu_schedule", ["坏群", "家人群"], self.daily())
        job = self.scheduler.get_job(task["task_id"])

        job.func(**job.kwargs)

        self.assertEqual(self.calls[-1], ("notice_moyu_schedule", "家人群"))


class ReminderEditTests(TaskServiceCase):
    """The console edits every field of a reminder, and AI still finds it by its receiver afterwards."""

    def setUp(self):
        super().setUp()
        self.reminders = importlib.import_module("true_love_server.services.reminder_service")
        self.later = (datetime.now(timezone.utc) + timedelta(hours=2)).replace(microsecond=0).isoformat()
        self.reminders.add_reminder("reminder_委员会_1", self.later, "委员会", "去开会", "alice")

    def test_every_field_can_be_changed(self):
        even_later = (datetime.now(timezone.utc) + timedelta(hours=5)).replace(microsecond=0).isoformat()

        self.reminders.edit_reminder("reminder_委员会_1", "委员会", "去吃饭", even_later, "bob", "lark")

        [reminder] = self.reminders.list_all_reminders()
        self.assertEqual((reminder["job_id"], reminder["content"], reminder["at_user"], reminder["platform"]),
                         ("reminder_委员会_1", "去吃饭", "bob", "lark"))
        self.assertEqual(datetime.fromisoformat(reminder["next_run_time"]), datetime.fromisoformat(even_later))

    def test_new_receiver_is_where_ai_looks_for_it(self):
        self.reminders.edit_reminder("reminder_委员会_1", "家人群", "去开会", self.later)

        self.assertEqual(self.reminders.query_reminders("委员会"), [])
        [moved] = self.reminders.query_reminders("家人群")
        self.assertEqual(moved["content"], "去开会")
        self.assertEqual(len(self.reminders.list_all_reminders()), 1)

    def test_missing_reminder_or_task_id_is_refused(self):
        task = self.tasks.add_task("notice_moyu_schedule", ["委员会"], self.daily())

        for job_id in ("reminder_nobody_1", task["task_id"]):
            with self.subTest(job_id=job_id):
                with self.assertRaises(ValueError):
                    self.reminders.edit_reminder(job_id, "委员会", "去开会", self.later)


if __name__ == "__main__":
    unittest.main()
