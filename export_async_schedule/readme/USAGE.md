When the configuration of a Scheduled Export is done, their execution is automatic.

Users will receive an email containing a link to download the exported file at the
specified frequency. The attachments stay in the database for 7 days by default (it can
be changed with the system parameter `attachment.ttl`.

## Export Groups

To group multiple exports into a single email:

1. Go to **Settings > Technical > Automation > Grouped Exports**.
2. Create a new group with:
   - A name for the group
   - The company (if multi-company)
   - The recipient email address
   - The email template to use
   - The scheduled exports to include in the group
   - The scheduling parameters (interval, next execution)
3. Use the **Test Export** button to verify the configuration.

When a scheduled export is part of a group, its individual execution is disabled. The
cron job will automatically send the grouped exports at the scheduled time.
