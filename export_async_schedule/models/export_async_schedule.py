# Copyright 2019 Camptocamp
# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class ExportAsyncSchedule(models.Model):
    _name = "export.async.schedule"
    _inherit = ["export.async.schedule.mixin", "mail.thread", "mail.activity.mixin"]
    _description = "Export Async Schedule"
    _rec_name = "display_name"

    display_name = fields.Char(compute="_compute_display_name", store=True)

    # Override user_ids to define explicit relation table
    user_ids = fields.Many2many(
        relation="export_async_schedule_res_users_rel",
        tracking=True,
    )
    model_id = fields.Many2one(
        comodel_name="ir.model", required=True, ondelete="cascade", tracking=True
    )
    model_name = fields.Char(related="model_id.model", string="Model Name")
    domain = fields.Char(string="Export Domain", default=[], tracking=True)
    ir_export_id = fields.Many2one(
        comodel_name="ir.exports",
        string="Export List",
        required=True,
        domain="[('resource', '=', model_name)]",
        ondelete="restrict",
        tracking=True,
    )
    export_format = fields.Selection(
        selection=[("csv", "CSV"), ("excel", "Excel")],
        default="csv",
        required=True,
        tracking=True,
    )
    import_compat = fields.Boolean(string="Import-compatible Export", tracking=True)
    group_id = fields.Many2one(
        comodel_name="export.async.schedule.group",
        string="Export Groups",
        help="Groups that include this scheduled export.",
        tracking=True,
    )

    @api.depends("model_id.name", "ir_export_id.name")
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.model_id.name}: {record.ir_export_id.name}"

    @api.onchange("group_id")
    def _onchange_group_id(self):
        """Propagate values from group when schedule is added to a group."""
        if self.group_id:
            self.active = self.group_id.active
            self.user_ids = self.group_id.user_ids
            self.next_execution = self.group_id.next_execution
            self.interval = self.group_id.interval
            self.interval_unit = self.group_id.interval_unit
            self.end_of_month = self.group_id.end_of_month
            self.lang = self.group_id.lang

    @api.model
    def _get_fields_with_labels(self, model_name, export_fields):
        self_fields = self.env[model_name]._fields
        result = []
        for field_name in export_fields:
            if "/" in field_name:
                # The ir.exports.line model contains only the name of the
                # field, and when we follow relations, the name of the fields
                # joined by /. example: 'bank_ids/acc_number'
                # Here, we follow the relations to get the labels
                parts = field_name.split("/")
                model_fields = self_fields
                label_parts = []
                for cur_field_name in parts:
                    cur_field = model_fields[cur_field_name]
                    label_parts.append(cur_field._description_string(self.env))
                    comodel_name = cur_field.comodel_name
                    if comodel_name:
                        model_fields = self.env[cur_field.comodel_name]._fields
                label = "/".join(label_parts)
            else:
                label = self_fields[field_name]._description_string(self.env)
            result.append({"label": label, "name": field_name})
        return result

    def _prepare_export_params(self):
        export_fields = [
            export_field.name for export_field in self.ir_export_id.export_fields
        ]
        if self.import_compat:
            export_fields = [
                {"label": export_field, "name": export_field}
                for export_field in export_fields
            ]
        else:
            export_fields = self._get_fields_with_labels(
                self.model_name,
                list(export_fields),
            )
        export_format = self.export_format == "excel" and "xlsx" or self.export_format
        return {
            "format": export_format,
            "model": self.model_name,
            "fields": export_fields,
            "ids": False,
            "domain": safe_eval(self.domain),
            "context": self.env.context,
            "import_compat": self.import_compat,
            "user_ids": self.user_ids.ids,
        }

    def run_schedule(self):
        for record in self:
            if record.next_execution > datetime.now():
                continue
            record.action_export()
            record.next_execution = record._compute_next_date()

    def action_export(self):
        for record in self:
            if record.group_id:
                continue
            record = record.with_context(lang=record.lang)
            params = record._prepare_export_params()
            record.env["delay.export"].with_delay().export(params)

    def action_view_group(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "export_async_schedule.action_export_async_schedule_group"
        )
        if self.group_id:
            action["view_mode"] = "form"
            action["res_id"] = self.group_id.id
            action["views"] = [(False, "form")]
        return action
