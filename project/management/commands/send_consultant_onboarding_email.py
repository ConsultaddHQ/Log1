from django.core.management.base import BaseCommand
from django.test import RequestFactory
from project.models import Project
from utils_app.thred_mail import send_email as send_email_
from constance import config
import string
import random


class Command(BaseCommand):
    help = "Send consultant onboarding emails to existing projects"

    def add_arguments(self, parser):
        parser.add_argument(
            'project_ids',
            nargs='+',
            type=int,
            help='Project IDs to send emails to (space-separated). Required'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would happen without sending emails.'
        )
        parser.add_argument(
            '--set-password',
            action='store_true',
            help='Generate and set a new password for consultants.'
        )

    @staticmethod
    def generate_password(length=10):
        """Generate a random password for consultant account"""
        characters = string.ascii_letters + string.digits + string.punctuation
        password = ''.join(random.choice(characters) for _ in range(length))
        return password

    def send_consultant_onboarding_mail(self, project, password, request_factory):
        """Send consultant account creation email"""
        try:
            request = request_factory.get('/')
            
            mail_data = {
                'template': '../templates/consultant_account_creation.html',
                'subject': f'Your account created on Consultadd Time Track App',
                'to': [project.consultant.email],
                'cc': [config.FINANCE, 'yash.j@consultadd.com'],
                'bcc': ['mansi.j@consultadd.com'],
                'context': {
                    'iphone_link': config.IPHONE_APP_LINK,
                    'android_link': config.ANDROID_APP_LINK,
                    'password': password,
                    'new_user': True,
                    'consultant_name': project.consultant.name,
                    'client': project.submission.client.title() if project.submission.client else 'Consultadd',
                    'consultant_email': project.consultant.email,
                },
            }
            msg, resp, _ = send_email_(mail_data, config.RELATIONS, request)
            return resp == "ok"
        except Exception as error:
            self.stdout.write(f"    ERROR: {str(error)}")
            return False

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        set_password = options.get('set_password', False)
        project_ids = options.get('project_ids', [])
        request_factory = RequestFactory()

        self.stdout.write("\n" + "="*70)
        self.stdout.write("SEND CONSULTANT ONBOARDING EMAIL TO PROJECTS")
        self.stdout.write("="*70 + "\n")

        results = {
            "total": len(project_ids),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "details": []
        }

	if not project_ids:
		self.stdout.write(self.style.ERROR("ERROR: Project IDs are required. ))

        for project_id in project_ids:
            try:
                project = Project.objects.select_related('consultant', 'submission').get(id=project_id)
                consultant = project.consultant

                self.stdout.write(f"Project {project_id} | Consultant: {consultant.name} ({consultant.email})")

                if dry_run:
                    self.stdout.write(f"  [DRY RUN] Would send email to {consultant.email}")
                    results["success"] += 1
                    results["details"].append({
                        "project_id": project_id,
                        "consultant": consultant.name,
                        "status": "dry_run",
                    })
                    continue

                # Generate password if requested
                if set_password:
                    password = self.generate_password()
                    consultant.set_password(password)
                    consultant.save()
                    self.stdout.write(f"  Password set: {password}")
                else:
                    if not consultant.has_usable_password():
                        password = self.generate_password()
                        consultant.set_password(password)
                        consultant.save()
                        self.stdout.write(f"  Generated password: {password}")
                    else:
                        self.stdout.write(f"  Consultant already has a password")
                        results["skipped"] += 1
                        results["details"].append({
                            "project_id": project_id,
                            "consultant": consultant.name,
                            "status": "skipped",
                            "reason": "Already has password"
                        })
                        continue

                # Send email
                self.stdout.write(f"  Sending email...")
                email_sent = self.send_consultant_onboarding_mail(project, password, request_factory)

                if email_sent:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Email sent successfully"))
                    results["success"] += 1
                    results["details"].append({
                        "project_id": project_id,
                        "consultant": consultant.name,
                        "email": consultant.email,
                        "status": "success",
                    })
                else:
                    self.stdout.write(self.style.ERROR(f"  ✗ Email sending failed"))
                    results["failed"] += 1
                    results["details"].append({
                        "project_id": project_id,
                        "consultant": consultant.name,
                        "status": "failed",
                        "error": "Email sending failed"
                    })
                self.stdout.write("")

            except Project.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Project {project_id} | ✗ NOT FOUND\n"))
                results["failed"] += 1
                results["details"].append({
                    "project_id": project_id,
                    "status": "failed",
                    "error": "Project not found"
                })
            except Exception as error:
                self.stdout.write(self.style.ERROR(f"Project {project_id} | ✗ ERROR: {str(error)}\n"))
                results["failed"] += 1
                results["details"].append({
                    "project_id": project_id,
                    "status": "failed",
                    "error": str(error)
                })

        # Print summary
        self.stdout.write("\n" + "="*70)
        self.stdout.write("SUMMARY")
        self.stdout.write("="*70)
        self.stdout.write(f"Total: {results['total']}")
        self.stdout.write(self.style.SUCCESS(f"✓ Success: {results['success']}"))
        self.stdout.write(self.style.ERROR(f"✗ Failed: {results['failed']}"))
        self.stdout.write(f"⊘ Skipped: {results['skipped']}")
        self.stdout.write("="*70 + "\n")

