# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.exceptions import ValidationError

from odoo.addons.queue_job.tests.common import trap_jobs

from .common import TestExportAsyncScheduleGroupBase


class TestExportAsyncScheduleGroup(TestExportAsyncScheduleGroupBase):
    def test_compute_next_date(self):
        next_date = self.group._compute_next_date()
        self.assertGreater(next_date, datetime.now())

    def test_get_export_filename(self):
        filename = self.group._get_export_filename(self.schedule)
        self.assertEqual(filename, "Test Partner Export.xlsx")

    def test_action_export_group(self):
        with patch.object(
            type(self.group),
            "_get_export_file_content",
            return_value=b"test content",
        ):
            with patch.object(
                type(self.env["mail.template"]),
                "send_mail",
                return_value=True,
            ) as mock_send:
                self.group.action_export_group()
                mock_send.assert_called_once()
                # Verify email_values contain attachment_ids
                call_args = mock_send.call_args
                self.assertIn("email_values", call_args[1])
                email_values = call_args[1]["email_values"]
                self.assertIn("attachment_ids", email_values)
                # Attachments should have been created and passed
                self.assertTrue(email_values["attachment_ids"])

        # Verify attachments were cleaned up after sending
        attachments = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "export.async.schedule.group"),
                ("res_id", "=", self.group.id),
            ]
        )
        self.assertEqual(len(attachments), 0)

    def test_cron_run_scheduled_groups(self):
        self.group.next_execution = datetime.now() - timedelta(hours=1)
        old_next_execution = self.group.next_execution
        with trap_jobs() as trap:
            self.env["export.async.schedule.group"]._cron_run_scheduled_groups()
            trap.assert_jobs_count(1)
            trap.assert_enqueued_job(
                self.group._run_scheduled_groups_batch,
            )
        # next_execution is updated in _run_scheduled_groups_batch, not in cron
        self.assertEqual(self.group.next_execution, old_next_execution)

    def test_check_users_have_email(self):
        user_no_email = self.env["res.users"].create(
            {
                "name": "Test User No Email",
                "login": "test_no_email",
                "email": False,
            }
        )
        with self.assertRaises(ValidationError):
            self.group.user_ids = [(4, user_no_email.id)]

    def test_action_test_export(self):
        with patch.object(
            type(self.group),
            "_get_export_file_content",
            return_value=b"test content",
        ):
            with patch.object(
                type(self.env["mail.template"]),
                "send_mail",
                return_value=True,
            ) as mock_send:
                self.group.action_test_export()
                mock_send.assert_called_once()

    def test_compute_display_name(self):
        self.assertIn("Test Partner Export", self.group.display_name)
        # Add another schedule
        schedule2 = self._create_standalone_schedule()
        self.group.export_schedule_ids = [(4, schedule2.id)]
        self.assertIn("...", self.group.display_name)
