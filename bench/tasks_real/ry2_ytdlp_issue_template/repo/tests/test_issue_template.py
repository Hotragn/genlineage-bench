import os
import unittest

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestBugReportForm(unittest.TestCase):
    def test_bug_report_requires_verbose_log(self):
        with open(os.path.join(ROOT, ".github", "ISSUE_TEMPLATE", "4_bug_report.yml")) as f:
            form = yaml.safe_load(f)
        body = {item.get("id"): item for item in form["body"] if item.get("id")}
        self.assertTrue(body["log"]["validations"]["required"])
        first = body["verbose"]["attributes"]["options"][0]
        self.assertTrue(first["required"])
