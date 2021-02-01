# Copyright 2021 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # this is the trigger that sends notifications when jobs change
    _logger.info("Create/replace queue_job_notify function")
    cr.execute(
        """
            CREATE OR REPLACE
                FUNCTION queue_job_notify() RETURNS trigger AS $$
            BEGIN
                IF TG_OP = 'DELETE' THEN
                    IF OLD.state != 'done' THEN
                        PERFORM pg_notify('queue_job', OLD.uuid);
                    END IF;
                ELSE
                    PERFORM pg_notify('queue_job', NEW.uuid);
                END IF;
                RETURN NULL;
            END;
        """
    )
