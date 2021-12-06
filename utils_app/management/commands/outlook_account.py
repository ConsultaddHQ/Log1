from django.core.management import BaseCommand

from utils_app.ms_account import MicrosoftAccount
from consultant.models import Consultant, MSAccount


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            users = [
                {
                    "name": "jane Doe",
                    "email": "jane.doe@consultadd.com",
                    "consultant_email": "janedoe@gmail.com",
                }
            ]
            ms = MicrosoftAccount()
            for user in users:
                qs = Consultant.objects.filter(email=user['consultant_email'])
                if qs:
                    consultant = qs.first()
                else:
                    continue
                user['password'] = f"consultadd@1{consultant.id}23"
                account, _ = MSAccount.objects.get_or_create(
                    consultant=consultant,
                )
                account.email = user['email']
                # Creating Account
                user_id, msg = ms.create_account(user)
                if msg == 'ok':
                    account.user_id = user_id
                    # Assigning licence
                    if ms.assign_licence(user_id) == "ok":
                        account.licence_assigned = True
                        # Assigning Team
                        member_id, msg = ms.assign_team(user_id)
                        if msg == 'ok':
                            account.member_id = member_id

                account.save()
        except Exception as error:
            print(error)
