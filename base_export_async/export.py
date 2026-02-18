# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

"""These classes are a response to the use of initial export controllers
in the export async job.

It is to avoid the following issue when the export async job is executed
without a proper inbound object.

Traceback (most recent call last):
  File "/__w/queue/queue/export_async_schedule/tests/
  test_export_async_schedule_group.py", line 158, in
  test_export_file_content_with_user_context
    content = group_as_super._get_export_file_content(self.export)
  File "/__w/queue/queue/export_async_schedule/models/
  export_async_schedule_group.py", line 99, in _get_export_file_content
    return self.env["delay.export"].with_user(user)._get_file_content(
        params)
  File "/opt/odoo-venv/lib/python3.10/site-packages/odoo/addons/
  base_export_async/models/delay_export.py", line 65, in
  _get_file_content
    return xls.from_data(columns_headers, import_data)
  File "/opt/odoo/addons/web/controllers/export.py", line 596, in
  from_data
    with ExportXlsxWriter(fields, len(rows)) as xlsx_writer:
  File "/opt/odoo/addons/web/controllers/export.py", line 189, in
  __init__
    request.env['res.currency'].search_read([], ['decimal_places'])]
  File "/opt/odoo-venv/lib/python3.10/site-packages/werkzeug/local.py",
  line 432, in __get__
    obj = instance._get_current_object()
  File "/opt/odoo-venv/lib/python3.10/site-packages/werkzeug/local.py",
  line 554, in _get_current_object
    return self.__local()  # type: ignore
  File "/opt/odoo-venv/lib/python3.10/site-packages/werkzeug/local.py",
  line 226, in _lookup
    raise RuntimeError("object unbound")
RuntimeError: object unbound
"""

from odoo.addons.web.controllers.export import CSVExport as CSVExportController
from odoo.addons.web.controllers.export import ExcelExport as ExcelExportController
from odoo.addons.web.controllers.export import ExportFormat


class CSVExport(ExportFormat):
    @property
    def content_type(self):
        return CSVExportController.content_type.fget(self)

    @property
    def extension(self):
        return CSVExportController.extension.fget(self)

    def from_data(self, fields, rows):
        return CSVExportController.from_data(self, fields, rows)


class ExcelExport(ExportFormat):
    @property
    def content_type(self):
        return ExcelExportController.content_type.fget(self)

    @property
    def extension(self):
        return ExcelExportController.extension.fget(self)

    def from_group_data(self, fields, groups):
        return ExcelExportController.from_group_data(self, fields, groups)

    def from_data(self, fields, rows):
        return ExcelExportController.from_data(self, fields, rows)
