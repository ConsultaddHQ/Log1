from django.core.management import BaseCommand

from consultant.models import MSAccount
from utils_app.ms_account import MicrosoftAccount


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            users = []
            ms = MicrosoftAccount()
            for user in users:
                account = MSAccount.objects.create(
                    email=user['email'],
                    consultant_email=user['consultant_email'],
                )
                user_id, msg = ms.create_account(user)
                account.user_id = user_id

                if msg == 'ok':
                    if ms.assign_licence(user_id) == "ok":
                        account.licence_assigned = True
                        member_id, msg = ms.assign_team(user_id)
                        if msg == 'ok':
                            account.member_id = member_id

                account.save()
        except Exception as error:
            print(error)
