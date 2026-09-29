"""One configuration file serves every machine; the only per-machine entry is who its master is."""

import os
import tempfile
import unittest
from unittest.mock import patch

from true_love_base import configuration


class MasterTests(unittest.TestCase):
    def load(self, master, hostname="WIN10-M8S"):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        with open(os.path.join(directory.name, "config.yaml"), "w", encoding="utf-8") as fp:
            fp.write('http_token: "token"\n' + master)
        previous = os.getcwd()
        os.chdir(directory.name)
        self.addCleanup(os.chdir, previous)
        with (
            patch.object(configuration.LoggingConfig, "setup"),
            patch.object(configuration.Config, "_instance", None),
            patch.object(configuration.Config, "_initialized", False),
            patch.object(configuration.socket, "gethostname", return_value=hostname),
        ):
            return configuration.Config()

    def test_machine_is_known_by_its_own_name_in_lower_case(self):
        self.assertEqual(self.load("").machine_name, "win10-m8s")

    def test_each_machine_finds_its_own_master(self):
        masters = 'master_wix:\n  win10-m8s: "alice"\n  win11-ser: "bob"\n'

        self.assertEqual(self.load(masters, hostname="WIN10-M8S").master_wix, "alice")
        self.assertEqual(self.load(masters, hostname="win11-ser").master_wix, "bob")

    def test_machine_names_in_the_file_match_in_any_letter_case(self):
        self.assertEqual(self.load('master_wix:\n  WIN10-M8S: "alice"\n', hostname="win10-m8s").master_wix, "alice")

    def test_machine_missing_from_the_map_has_no_master(self):
        with self.assertLogs("Config", level="WARNING"):
            config = self.load('master_wix:\n  win11-ser: "bob"\n', hostname="win10-m8s")

        self.assertEqual(config.master_wix, "")

    def test_single_master_written_the_old_way_serves_every_machine(self):
        self.assertEqual(self.load('master_wix: "alice"\n', hostname="any-machine").master_wix, "alice")

    def test_file_without_any_master_still_loads(self):
        with self.assertLogs("Config", level="WARNING"):
            config = self.load("")

        self.assertEqual(config.master_wix, "")


if __name__ == "__main__":
    unittest.main()
