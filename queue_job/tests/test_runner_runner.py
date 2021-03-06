# -*- coding: utf-8 -*-
# Copyright 2015-2016 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

import doctest
from odoo.addons.queue_job.jobrunner import runner


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(runner))
    return tests
