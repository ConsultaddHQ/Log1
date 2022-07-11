import csv
from datetime import datetime
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from employee.models import User, Tagging
from log1.utils import write_exception, ERROR_MSG
from notification.utils import create_notification, push_notification
from utils_app.utils import upload_csv_file_s3


def tag_and_notify(update, tags, user, tag_type='create'):
    user_list = []
    if not tags:
        return None

    if tag_type == 'create':
        content_type = ContentType.objects.get(model='projectupdate')
        tag_obj = Tagging.objects.create(content_type=content_type, object_id=update.id)
        for tag in tags.strip().split(','):
            if tag:
                user = get_object_or_404(User, id=int(tag))
                user_list.append(user)
                tag_obj.tagged_user.add(user)

    elif tag_type == 'update':
        if update.tagged_user.exists():
            for tag in tags:
                user = get_object_or_404(User, id=tag)
                user_list.append(user)
                update.tagged_user.first().tagged_user.add(user)

    title = f"{user.employee_name} tagged you in a project update of {update.project.consultant.name}"
    notification_data = {
        'title': title,
        'category': 'info',
        'description': title,
        'sender_id': user.id,
        'target_id': update.id,
        'sender_user_type': 'user',
        'parent_user_type': 'project',
        'recipient_user_type': 'user',
        'target_type': 'projectupdate',
        'parent_id': update.project.id,
    }
    create_notification(user_list, notification_data)

    # Push Notification
    message_body = {
        "category": "alert",
        "show_in_foreground": True,
        "title": title, "body": title,
        "click_action": "https://app.log1.com",
        "data": {
            'is_read': False,
            'is_deleted': False,
            'target': 'project',
            'sub_target_id': update.id,
            'sub_target': 'projectupdate',
            'target_id': update.project.id,
            'timestamp': str(datetime.now()),
        },
    }
    push_notification(tags, message_body)


def get_csv_report(payload, request):
    try:
        filename = f'{datetime.now()}'.replace(' ', '')
        file = open(f"engineer_report_{filename}.csv", "w")
        writer = csv.writer(file)
        writer.writerow([
            "Engineer name", "Consultant Name", "Support Start Date", "Project Start Date", "Support Duration",
            "Technology", "Client", "Modified at", "Timezone", "Status", "Remote Project"
        ])
        for data in payload:
            count = 0
            while count < data['project']['bandwidth']:
                project = data['project']['data'][count]
                support_info = project['support_info']
                description = project['description']
                consultant = project['consultant']
                modified_at = project['modified_at']['date'] if project.get('modified_at') else "Not Updated"
                writer.writerow([
                    data.get('employee_name'), consultant.get('name'), support_info.get('start'), project.get('start'),
                    f'{support_info.get("duration", 0)} months', description.get('technology'),
                    project['project'].get('client'), modified_at, description.get('timezone'),
                    project.get('support_status'), "Yes" if project.get('is_remote') else "No"
                ])
                count += 1
        file.close()
        file_url = upload_csv_file_s3(file.name)
        return file_url
    except Exception as error:
        write_exception(error, request)
