# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo.addons.queue_job.tests.common import trap_jobs

from .common import TestExportAsyncScheduleGroupBase


class TestExportAsyncScheduleGroupRelation(TestExportAsyncScheduleGroupBase):
    def test_schedule_group_id(self):
        self.assertEqual(self.schedule.group_id, self.group)

    def test_schedule_not_part_of_group(self):
        schedule_alone = self._create_standalone_schedule()
        self.assertFalse(schedule_alone.group_id)

    def test_schedule_individual_export_allowed_when_not_in_group(self):
        schedule_alone = self._create_standalone_schedule()
        with trap_jobs() as trap:
            schedule_alone.action_export()
            trap.assert_jobs_count(1)

    def test_schedule_run_schedule_skips_grouped(self):
        # run_schedule calls action_export which silently skips grouped schedules
        self.schedule.next_execution = datetime.now() - timedelta(hours=1)
        with trap_jobs() as trap:
            self.schedule.run_schedule()
            # No job enqueued because action_export skips grouped schedules
            trap.assert_jobs_count(0)

    def test_action_view_groups(self):
        action = self.schedule.action_view_groups()
        self.assertEqual(action["res_id"], self.group.id)

    def test_onchange_export_schedule_propagation(self):
        # Change group fields and check propagation to schedules
        self.group.active = False
        self.group.user_ids = [(6, 0, [])]
        self.group.next_execution = datetime.now() + timedelta(days=2)
        self.group.interval = 2
        self.group.interval_unit = "weeks"
        self.group.end_of_month = True
        self.group.lang = "fr_FR"
        # Trigger onchange
        self.group._onchange_export_schedule_propagation()
        self.assertFalse(self.schedule.active)
        self.assertEqual(self.schedule.user_ids, self.env["res.users"])
        self.assertEqual(self.schedule.next_execution, self.group.next_execution)
        self.assertEqual(self.schedule.interval, 2)
        self.assertEqual(self.schedule.interval_unit, "weeks")
        self.assertTrue(self.schedule.end_of_month)
        self.assertEqual(self.schedule.lang, "fr_FR")
