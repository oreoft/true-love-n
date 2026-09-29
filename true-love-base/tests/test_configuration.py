"""Aliases are the only names a bot cannot read from WeChat, so they come from its configuration."""

import os
import tempfile
import unittest
from unittest.mock import patch

from true_love_base import configuration


class MentionAliasesTests(unittest.TestCase):
    def load(self, extra=""):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        with open(os.path.join(directory.name, "config.yaml"), "w", encoding="utf-8") as fp:
            fp.write('master_wix: "owner"\nhttp_token: "token"\n' + extra)
        previous = os.getcwd()
        os.chdir(directory.name)
        self.addCleanup(os.chdir, previous)
        with (
            patch.object(configuration.LoggingConfig, "setup"),
            patch.object(configuration.Config, "_instance", None),
            patch.object(configuration.Config, "_initialized", False),
        ):
            return configuration.Config()

    def test_aliases_are_read_from_the_configuration(self):
        config = self.load('mention_aliases: ["zaf", "小真"]\n')

        self.assertEqual(config.mention_aliases, ["zaf", "小真"])

    def test_bot_without_configured_aliases_has_none(self):
        self.assertEqual(self.load().mention_aliases, [])

    def test_alias_written_as_plain_text_is_one_alias_not_one_per_letter(self):
        config = self.load("mention_aliases: zaf\n")

        self.assertEqual(config.mention_aliases, ["zaf"])

    def test_blank_aliases_are_dropped_because_they_would_match_every_message(self):
        config = self.load('mention_aliases: ["", "  ", "zaf"]\n')

        self.assertEqual(config.mention_aliases, ["zaf"])


if __name__ == "__main__":
    unittest.main()
