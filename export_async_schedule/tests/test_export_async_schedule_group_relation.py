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

    def test_write_propagate_to_exports(self):
        # Update group fields and verify propagation to exports
        new_execution = datetime.now() + timedelta(days=2)
        self.group.write(
            {
                "active": False,
                "user_ids": [(6, 0, [])],
                "next_execution": new_execution,
                "interval": 2,
                "interval_unit": "weeks",
                "end_of_month": True,
                "lang": "fr_FR",
            }
        )
        # Verify changes were propagated to the export
        self.assertFalse(self.export.active)
        self.assertEqual(self.export.user_ids, self.env["res.users"])
        self.assertEqual(self.export.next_execution, new_execution)
        self.assertEqual(self.export.interval, 2)
        self.assertEqual(self.export.interval_unit, "weeks")
        self.assertTrue(self.export.end_of_month)
        self.assertEqual(self.export.lang, "fr_FR")

    def test_adding_export_to_group_inherits_values(self):
        # Create a standalone export with different values
        export_alone = self._create_standalone_export()
        export_alone.write(
            {
                "active": True,
                "interval": 7,
                "interval_unit": "days",
                "end_of_month": False,
            }
        )
        # Add it to the group by setting group_id
        export_alone.group_id = self.group
        # Trigger onchange to inherit group values
        export_alone._onchange_group_id()
        # Verify the export inherited group values
        self.assertEqual(export_alone.active, self.group.active)
        self.assertEqual(export_alone.user_ids, self.group.user_ids)
        self.assertEqual(export_alone.next_execution, self.group.next_execution)
        self.assertEqual(export_alone.interval, self.group.interval)
        self.assertEqual(export_alone.interval_unit, self.group.interval_unit)
        self.assertEqual(export_alone.end_of_month, self.group.end_of_month)
        self.assertEqual(export_alone.lang, self.group.lang)
