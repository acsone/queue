# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.exceptions import ValidationError

from odoo.addons.queue_job.tests.common import trap_jobs

from .common import TestExportAsyncScheduleGroupBase


class TestExportAsyncScheduleGroup(TestExportAsyncScheduleGroupBase):
    def test_compute_next_date(self):
        """Test computation of next execution date."""
        next_date = self.group._compute_next_date()
        self.assertGreater(next_date, datetime.now())

    def test_get_export_filename(self):
        """Test export filename generation with format extension."""
        self.export.export_format = "excel"
        filename = self.group._get_export_filename(self.export)
        self.assertEqual(filename, "Test Partner Export.xlsx")

    def test_action_export_group(self):
        """Test export group action creates attachments and sends mail."""
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
                call_args = mock_send.call_args
                self.assertIn("email_values", call_args[1])
                email_values = call_args[1]["email_values"]
                self.assertIn("attachment_ids", email_values)
                self.assertTrue(email_values["attachment_ids"])

    def test_cron_run_scheduled_groups(self):
        """Test cron job enqueues scheduled groups."""
        self.group.next_execution = datetime.now() - timedelta(hours=1)
        old_next_execution = self.group.next_execution
        with trap_jobs() as trap:
            self.env["export.async.schedule.group"]._cron_run_scheduled_groups()
            trap.assert_jobs_count(1)
            trap.assert_enqueued_job(
                self.group._run_scheduled_group,
            )
        self.assertEqual(self.group.next_execution, old_next_execution)

    def test_check_users_have_email(self):
        """Test validation error when user without email in template partners."""
        user_no_email = self.env["res.users"].create(
            {
                "name": "Test User No Email",
                "login": "test_no_email",
                "email": False,
            }
        )
        partner_no_email = user_no_email.partner_id
        template = self.env["mail.template"].create(
            {
                "name": "Test Template No Email",
                "model_id": self.env.ref(
                    "export_async_schedule.model_export_async_schedule_group"
                ).id,
                "partner_to": str(partner_no_email.id),
            }
        )
        with self.assertRaises(ValidationError):
            self.env["export.async.schedule.group"].create(
                {
                    "name": "Test Group Invalid",
                    "export_ids": [(6, 0, [self.export.id])],
                    "mail_template_id": template.id,
                }
            )

    def test_check_has_exports(self):
        """Test validation error when group has no exports."""
        with self.assertRaises(ValidationError):
            self.export.group_id = False

    def test_action_test_export(self):
        """Test send test export calls send_mail."""
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
        """Test display name includes group name and company."""
        self.assertIn("Test Export Group", self.group.display_name)
        self.assertIn(self.group.company_id.name, self.group.display_name)

    def test_onchange_mail_template_id(self):
        """Test user_ids are computed from template partners."""
        partner1 = self.env["res.partner"].create(
            {
                "name": "Partner 1",
                "email": "partner1@example.com",
            }
        )
        partner2 = self.env["res.partner"].create(
            {
                "name": "Partner 2",
                "email": "partner2@example.com",
            }
        )
        user1 = self.env["res.users"].create(
            {
                "name": "User 1",
                "login": "user1",
                "email": "partner1@example.com",
                "partner_id": partner1.id,
            }
        )
        user2 = self.env["res.users"].create(
            {
                "name": "User 2",
                "login": "user2",
                "email": "partner2@example.com",
                "partner_id": partner2.id,
            }
        )

        template = self.env["mail.template"].create(
            {
                "name": "Test Template",
                "model_id": self.env.ref(
                    "export_async_schedule.model_export_async_schedule_group"
                ).id,
                "partner_to": f"{partner1.id},{partner2.id}",
            }
        )

        new_group = self.env["export.async.schedule.group"].create(
            {
                "name": "Test Group 2",
                "export_ids": [(6, 0, [self.export.id])],
                "mail_template_id": self.mail_template.id,
            }
        )
        new_group.mail_template_id = template

        self.assertIn(user1, new_group.user_ids)
        self.assertIn(user2, new_group.user_ids)

    def test_get_export_filename_csv(self):
        """Test CSV export filename generation."""
        self.export.export_format = "csv"
        filename = self.group._get_export_filename(self.export)
        self.assertEqual(filename, "Test Partner Export.csv")

    def test_get_export_filename_excel(self):
        """Test Excel export filename generation."""
        self.export.export_format = "excel"
        filename = self.group._get_export_filename(self.export)
        self.assertEqual(filename, "Test Partner Export.xlsx")

    def test_get_recipient_emails_from_group_only(self):
        """Test recipients come from group users when template has no email_to."""
        self.mail_template.email_to = False
        emails = self.group._get_recipient_emails()
        self.assertIn(self.user.email, emails)

    def test_get_recipient_emails_from_template_only(self):
        """Test recipients come from template email_to when group has no users."""
        new_group = self.env["export.async.schedule.group"].create(
            {
                "name": "Test Group No Partners",
                "export_ids": [(6, 0, [self.export.id])],
                "mail_template_id": self.mail_template.id,
            }
        )
        new_group.user_ids = [(5, 0, 0)]
        template_email = "template@example.com"
        self.mail_template.email_to = template_email
        emails = new_group._get_recipient_emails()
        self.assertIn(template_email, emails)

    def test_get_recipient_emails_merge_group_and_template(self):
        """Test recipients are merged from group and template."""
        self.mail_template.email_to = "template@example.com"
        emails = self.group._get_recipient_emails()
        self.assertIn(self.user.email, emails)
        self.assertIn("template@example.com", emails)

    def test_get_recipient_emails_deduplicates(self):
        """Test duplicate recipients are removed."""
        self.mail_template.email_to = self.user.email
        emails = self.group._get_recipient_emails()
        self.assertEqual(emails.count(self.user.email), 1)

    def test_compute_template_partner_ids(self):
        """Test template partners are extracted from partner_to field."""
        partner = self.env["res.partner"].create(
            {"name": "Test Partner", "email": "test@example.com"}
        )
        self.mail_template.partner_to = str(partner.id)
        self.group._compute_partners_users_from_template()
        self.assertIn(partner, self.group.template_partner_ids)

    def test_compute_template_partner_ids_empty(self):
        """Test template_partner_ids is empty when partner_to is not set."""
        self.mail_template.partner_to = False
        self.group._compute_partners_users_from_template()
        self.assertFalse(self.group.template_partner_ids)
