# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo.addons.queue_job.tests.common import trap_jobs

from .common import TestExportAsyncScheduleGroupBase


class TestExportAsyncScheduleGroupRelation(TestExportAsyncScheduleGroupBase):
    def test_export_group_id(self):
        self.assertEqual(self.export.group_id, self.group)

    def test_export_not_part_of_group(self):
        export_alone = self._create_standalone_export()
        self.assertFalse(export_alone.group_id)

    def test_export_individual_export_allowed_when_not_in_group(self):
        export_alone = self._create_standalone_export()
        with trap_jobs() as trap:
            export_alone.action_export()
            trap.assert_jobs_count(1)

    def test_export_run_schedule_skips_grouped(self):
        self.export.next_execution = datetime.now() - timedelta(hours=1)
        with trap_jobs() as trap:
            self.export.run_schedule()
            trap.assert_jobs_count(0)

    def test_action_view_group(self):
        action = self.export.action_view_group()
        self.assertEqual(action["res_id"], self.group.id)

    def test_onchange_propagate_to_exports(self):
        self.group.active = False
        self.group.user_ids = [(6, 0, [])]
        self.group.next_execution = datetime.now() + timedelta(days=2)
        self.group.interval = 2
        self.group.interval_unit = "weeks"
        self.group.end_of_month = True
        self.group.lang = "fr_FR"
        self.group._onchange_propagate_to_exports()
        self.assertFalse(self.export.active)
        self.assertEqual(self.export.user_ids, self.env["res.users"])
        self.assertEqual(self.export.next_execution, self.group.next_execution)
        self.assertEqual(self.export.interval, 2)
        self.assertEqual(self.export.interval_unit, "weeks")
        self.assertTrue(self.export.end_of_month)
        self.assertEqual(self.export.lang, "fr_FR")
