from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType

from attachment.models import Attachment
from project.models import Project, ProjectStatus, TimeSheet


class Command(BaseCommand):
    help = (
        "Read-only diagnostic for one or more Project IDs. "
        "Prints consultant, submission, status history, and TimeSheet state side-by-side. "
        "Usage: python manage.py diagnose_projects 1884 1857"
    )

    def add_arguments(self, parser):
        parser.add_argument('project_ids', nargs='+', type=int)

    def handle(self, *args, **options):
        timesheet_ct = ContentType.objects.get(model='timesheet')
        for pid in options['project_ids']:
            self._dump_project(pid, timesheet_ct)

    def _dump_project(self, pid, timesheet_ct):
        self.stdout.write("")
        self.stdout.write("=" * 78)
        self.stdout.write(f"PROJECT {pid}")
        self.stdout.write("=" * 78)

        try:
            project = Project.objects.select_related('submission', 'consultant').get(pk=pid)
        except Project.DoesNotExist:
            self.stdout.write(f"  Project {pid} does not exist.")
            return

        consultant = project.consultant
        if consultant:
            self.stdout.write("  Consultant:")
            self.stdout.write(f"    id={consultant.id}  name={consultant.name!r}  email={consultant.email!r}")
            self.stdout.write(
                f"    status={consultant.status!r}  is_active={consultant.is_active}  "
                f"first_login={consultant.first_login}"
            )
        else:
            self.stdout.write("  Consultant: <none>")

        sub = project.submission
        self.stdout.write("  Submission:")
        self.stdout.write(
            f"    id={sub.id}  client={sub.client!r}  work_type={sub.work_type!r}"
        )

        self.stdout.write("  Project fields:")
        self.stdout.write(
            f"    start_date={project.start_date}  end_date={project.end_date}  "
            f"employer={project.employer!r}"
        )
        self.stdout.write(
            f"    timesheet_frequency={project.timesheet_frequency!r}  "
            f"is_remote={project.is_remote}"
        )

        statuses = list(ProjectStatus.objects.filter(project=project).order_by('created'))
        current_count = sum(1 for s in statuses if s.is_current)
        self.stdout.write(f"  ProjectStatus rows ({len(statuses)} total, {current_count} is_current=True):")
        for s in statuses:
            marker = " <-- CURRENT" if s.is_current else ""
            self.stdout.write(f"    [{s.id}] {s.created:%Y-%m-%d %H:%M}  status={s.status!r}  is_current={s.is_current}{marker}")
        if current_count > 1:
            self.stdout.write(
                "    !! WARNING: more than one ProjectStatus has is_current=True. "
                "ProjectTimeSheetSerializer.get_status uses .get() and will raise "
                "MultipleObjectsReturned for this project."
            )

        all_ts = TimeSheet.objects.filter(project=project)
        ts_total = all_ts.count()
        ts_active_drafts = all_ts.filter(status='draft', is_active=True).count()
        self.stdout.write("  TimeSheets:")
        self.stdout.write(f"    total={ts_total}  active_drafts={ts_active_drafts}")

        recent = all_ts.order_by('-created')[:3]
        if recent:
            self.stdout.write("    most recent 3:")
            for t in recent:
                self.stdout.write(
                    f"      [{t.id}] {t.start} → {t.end}  status={t.status!r}  "
                    f"is_active={t.is_active}  submitted_at={t.submitted_at}"
                )
        else:
            self.stdout.write("    (no TimeSheet rows)")

        ts_ids = list(all_ts.values_list('id', flat=True))
        if ts_ids:
            att_count = Attachment.objects.filter(
                content_type=timesheet_ct, object_id__in=ts_ids, is_active=True
            ).count()
            self.stdout.write(f"    attachments on these TimeSheets (is_active=True): {att_count}")

        if sub.work_type and sub.work_type.lower() == 'c2c' and ts_active_drafts == 0:
            self.stdout.write(
                "  !! work_type is C2C but there are zero active draft TimeSheets. "
                "Mobile timesheet-submit will 404 at project/mobile_api.py:194-199 "
                "(no week_id can match)."
            )
        if not project.start_date:
            self.stdout.write(
                "  !! start_date is NULL. project/utils.py:460 will raise on "
                "datetime.strptime(None) — drafts were never seeded."
            )
