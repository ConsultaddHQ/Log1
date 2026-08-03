from django.core.management.base import BaseCommand

from project.models import Project, TimeSheet
from datetime import datetime, timedelta, date

class Command(BaseCommand):
    help = (
        "Re-seed C2C draft TimeSheets for one or more projects from their current start_date. "
        "Safe: refuses to run if any non-draft TimeSheet exists. "
        "Usage: python manage.py reseed_drafts 1884 [--dry-run]"
    )

    def add_arguments(self, parser):
        parser.add_argument('project_ids', nargs='+', type=int)
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Print what would happen without modifying the database.",
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        for pid in options['project_ids']:
            self.stdout.write("")
            self.stdout.write(f"PROJECT {pid}")
            try:
                project = Project.objects.select_related('submission', 'consultant').get(pk=pid)
            except Project.DoesNotExist:
                self.stdout.write(f"  Project {pid} does not exist.")
                continue
            ok, msg, _created = reseed_project_drafts(project, dry_run=dry_run)
            prefix = "  OK:" if ok else "  --"
            self.stdout.write(f"{prefix} {msg}")




def reseed_project_drafts(project, dry_run=False):
    """Re-seed C2C draft TimeSheets for a project from its current start_date.

    Refuses to run if any non-draft TimeSheet exists, so submitted/rejected/
    approved/updated rows are never touched. Returns (ok, message, drafts_created).
    """
    if project.consultant is None:
        return False, "skipped: project has no consultant", 0
    submission = project.submission
    work_type = (submission.work_type or '').lower()
    if work_type != 'c2c':
        return False, f"skipped: work_type={submission.work_type!r} (only C2C uses pre-seeded drafts)", 0
    if not project.statuses.filter(status='joined', is_current=True).exists():
        return False, "skipped: project does not have a current 'joined' status", 0
    if project.start_date is None:
        return False, "skipped: start_date is NULL", 0
    if TimeSheet.objects.filter(project=project).exclude(status='draft').exists():
        return False, "skipped: project has non-draft TimeSheets (submitted/rejected/approved/updated)", 0

    start_date = datetime.strptime(str(project.start_date), '%Y-%m-%d')
    week_day = start_date.weekday()
    if week_day == 6:
        start_date = start_date + timedelta(days=1)
        end_date = start_date + timedelta(days=6)
    else:
        end_date = start_date + timedelta(days=6 - week_day)

    existing_drafts = list(
        TimeSheet.objects.filter(project=project, status='draft', is_active=True).values_list(
            'id', 'start', 'end'
        )
    )

    planned = []
    cur_start, cur_end = start_date, end_date
    for _ in range(2):
        planned.append((cur_start.date(), cur_end.date()))
        cur_start = cur_end + timedelta(days=1)
        cur_end = cur_end + timedelta(days=7)

    if dry_run:
        msg = (
            f"dry-run: would delete {len(existing_drafts)} draft(s) "
            f"{[(d[1], d[2]) for d in existing_drafts]}; "
            f"would create drafts {planned}"
        )
        return True, msg, len(planned)

    deleted_count = TimeSheet.objects.filter(
        project=project, status='draft', is_active=True
    ).delete()[0]

    created = 0
    cur_start, cur_end = start_date, end_date
    for _ in range(2):
        _, was_created = TimeSheet.objects.get_or_create(
            start=cur_start, end=cur_end,
            hours=0, status='draft', project=project,
        )
        if was_created:
            created += 1
        cur_start = cur_end + timedelta(days=1)
        cur_end = cur_end + timedelta(days=7)

    return True, f"deleted {deleted_count} draft(s); created {created} draft(s) for weeks {planned}", created




