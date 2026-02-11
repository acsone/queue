# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

MAX_SCHEDULES_IN_NAME = 3


class ExportAsyncScheduleGroup(models.Model):
    _name = "export.async.schedule.group"
    _inherit = ["export.async.schedule.mixin", "mail.thread", "mail.activity.mixin"]
    _description = "Export Async Schedule Group"
    _rec_name = "display_name"

    # Override user_ids to define explicit relation table
    user_ids = fields.Many2many(
        relation="export_async_schedule_group_res_users_rel",
        tracking=True,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
    )
    export_schedule_ids = fields.Many2many(
        comodel_name="export.async.schedule",
        relation="export_async_schedule_group_schedule_rel",
        column1="group_id",
        column2="schedule_id",
        string="Scheduled Exports",
        required=True,
        tracking=True,
    )
    mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Email Template",
        required=True,
        domain="[('model', '=', 'export.async.schedule.group')]",
        help="Email template used to send the grouped exports.",
        tracking=True,
    )

    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("company_id.name", "export_schedule_ids.display_name")
    def _compute_display_name(self):
        for record in self:
            schedules = ", ".join(
                record.export_schedule_ids.mapped("display_name")[
                    :MAX_SCHEDULES_IN_NAME
                ]
            )
            if len(record.export_schedule_ids) > MAX_SCHEDULES_IN_NAME:
                schedules += ", ..."
            record.display_name = f"{record.company_id.name}: {schedules}"

    @api.constrains("user_ids")
    def _check_users_have_email(self):
        for record in self:
            users_without_email = record.user_ids.filtered(lambda u: not u.email)
            if users_without_email:
                user_names = ", ".join(users_without_email.mapped("name"))
                raise ValidationError(
                    _("The following users must have an email address: %s", user_names)
                )

    @api.onchange(
        "active",
        "user_ids",
        "next_execution",
        "interval",
        "interval_unit",
        "end_of_month",
        "lang",
    )
    def _onchange_export_schedule_propagation(self):
        for export in self.export_schedule_ids:
            export.active = self.active
            export.user_ids = self.user_ids
            export.next_execution = self.next_execution
            export.interval = self.interval
            export.interval_unit = self.interval_unit
            export.end_of_month = self.end_of_month
            export.lang = self.lang

    @api.model
    def _cron_run_scheduled_groups(self):
        groups = self.search([("next_execution", "<=", datetime.now())])
        if not groups:
            return
        # Batch processing: enqueue all groups in a single job
        groups.with_delay()._run_scheduled_groups_batch()

    def _run_scheduled_groups_batch(self):
        for group in self:
            try:
                group.action_export_group()
                group.next_execution = group._compute_next_date()
            except Exception as e:
                # Log error but continue processing other groups
                group.env["ir.logging"].sudo().create(
                    {
                        "name": "export.async.schedule.group",
                        "type": "server",
                        "level": "ERROR",
                        "message": f"Error exporting group {group.id}: {e!s}",
                        "path": "export_async_schedule",
                        "func": "_run_scheduled_groups_batch",
                        "line": 0,
                    }
                )

    def _get_export_file_content(self, schedule):
        schedule = schedule.with_context(lang=schedule.lang)
        params = schedule._prepare_export_params()
        return self.env["delay.export"]._get_file_content(params)

    def _get_export_filename(self, schedule):
        export_name = schedule.ir_export_id.name or schedule.model_id.name
        return f"{export_name}.xlsx"

    def action_export_group(self):
        self.ensure_one()

        # Early validation
        if not self.export_schedule_ids:
            raise UserError(_("No scheduled exports configured for this group."))

        recipient_emails = ",".join(self.user_ids.filtered("email").mapped("email"))
        if not recipient_emails:
            raise UserError(_("No recipients with valid email addresses configured."))

        if not self.mail_template_id:
            raise UserError(_("No email template configured."))

        # Create attachments
        attachments = self.env["ir.attachment"]
        for schedule in self.export_schedule_ids:
            content = self._get_export_file_content(schedule)
            filename = self._get_export_filename(schedule)
            attachment = attachments.create(
                {
                    "name": filename,
                    "datas": base64.b64encode(content),
                    "type": "binary",
                    "res_model": self._name,
                    "res_id": self.id,
                }
            )
            attachments |= attachment

        # Send email
        odoo_bot = self.env.ref("base.partner_root")
        try:
            self.mail_template_id.send_mail(
                self.id,
                email_values={
                    "email_from": odoo_bot.email,
                    "email_to": recipient_emails,
                    "attachment_ids": [(6, 0, attachments.ids)],
                },
            )
        finally:
            # Clean up attachments after sending
            attachments.unlink()

    def action_test_export(self):
        self.ensure_one()
        self.action_export_group()
