import csv
import pandas as pd
from decimal import Decimal
from datetime import datetime
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

from employee.models import User, Tagging
from marketing.models import Question, Answer
from engineering.models import Cycle, EngineerPoint

from utils_app.utils import generate_s3_url
from log1.utils import write_exception, ERROR_MSG
from notification.utils import create_notification, push_notification


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


def get_engineer_detail_csv(payload, request):
    try:
        filename = f'{datetime.now()}'.replace(' ', '')
        file = open(f"engineer_report_{filename}.csv", "w")
        writer = csv.writer(file)
        writer.writerow([
            "Engineer name", "Consultant Name", "Support Start Date", "Project Start Date", "Support Duration",
            "Technology", "Client", "Modified at", "Timezone", "Status", "Remote"
        ])
        for data in payload:
            count = 0
            while count < data['project']['bandwidth']:
                project = data['project']['data'][count]
                consultant = project.get('consultant')
                description = project.get('description')
                support_info = project.get('support_info')
                modified_at = project['modified_at']['date'] if project.get('modified_at') else "Not Updated"
                writer.writerow([
                    data.get('employee_name'), consultant.get('name'), support_info.get('start'), project.get('start'),
                    f'{support_info.get("duration", 0)} months', description.get('technology'),
                    project['project'].get('client'), modified_at, description.get('timezone'),
                    project.get('support_status'), project['project']['is_remote']
                ])
                count += 1
        file.close()
        file_url = generate_s3_url(file.name)
        return file_url
    except Exception as error:
        write_exception(error, request)


def get_shift(shift_type, request):
    try:
        shifts = User.SHIFT_CHOICE
        for shift in shifts:
            if shift_type == shift[0]:
                return shift[1]
        return None
    except Exception as error:
        write_exception(error, request)


def get_team_structure_xlsx(payload, counts, request):
    try:
        columns = ['Engineer Name', 'SkillSet', 'Shift', 'Support Consultant', 'Team Name']
        rows = []
        for data in payload:
            rows.append([data.get('employee_name'),
                         ", ".join([i for i in data.get('technology', [])]) if data.get('technology', []) else [],
                         get_shift(data.get('shift'), request),
                         ", ".join([i['consultant'] for i in data['current_project']['project']])
                         if data.get('current_project') else None, data['team']])
        df1 = pd.DataFrame(rows, columns=columns)

        frames = []
        for count_type in counts:
            columns = [None, count_type.capitalize(), 'Count', None]
            rows = []
            for data in counts[count_type]:
                rows.append([None, data['display_name'], data['count'], None])
            df2 = pd.DataFrame(rows, columns=columns)
            frames.append(df2)
        result = pd.concat(frames, axis=1)

        filename = f'{datetime.now()}'.replace(' ', '')
        writer = pd.ExcelWriter(f'team_structure_{filename}.xlsx', engine='xlsxwriter')
        df1.to_excel(writer, sheet_name='Team Structure', index=None)
        result.to_excel(writer, sheet_name='Count', index=None)

        writer.save()
        file_url = generate_s3_url(f'team_structure_{filename}.xlsx')
        return file_url
    except Exception as error:
        write_exception(error, request)


def get_remote_project_csv(payload, request):
    try:
        filename = f'{datetime.now()}'.replace(' ', '')
        file = open(f"remote_project_report_{filename}.csv", "w")
        writer = csv.writer(file)
        writer.writerow([
            "Remote Engineer", "Consultant Name", "Support Engineer", "Support Start Date", "Support Status",
            "Project Start Date", "Support Duration", "Technology", "Client", "Timezone", "Project Status"
        ])
        for data in payload:
            writer.writerow([
                data['consultant']['remote_employee'], data['consultant']['name'], data['support_info']['name'],
                data['support_info']['start_date'], data['support_info']['status'], data['start_date'],
                data['support_info']['duration'], data['project_detail']['technology'],
                data['project_detail']['client'], data['project_detail']['timezone'], data['project_detail']['status']
            ])
        file.close()
        file_url = generate_s3_url(file.name)
        return file_url
    except Exception as error:
        write_exception(error, request)


@staticmethod
def calculate_mcq_points(no_of_mcq):
    first_twenty_points = (20 if no_of_mcq > 20 else no_of_mcq) * 0.25
    next_ten_points = (10 if no_of_mcq > 30 else no_of_mcq - 20) * 0.20
    rest_all_points = (no_of_mcq - 30 if no_of_mcq > 30 else -1) * 0.15
    points = first_twenty_points + (next_ten_points if next_ten_points > 0 else 0) + (
        rest_all_points if rest_all_points > 0 else 0)
    return round(points, 2)


def calculate_points(test_platform_name, test_type, test_current_status, no_of_people_involved=0, no_mcq_q=0,
                     no_coding_q=0):
    points = 0
    if test_type.lower() == 'online':
        if no_mcq_q and no_coding_q:
            test_points = calculate_mcq_points(int(no_mcq_q)) + int(no_coding_q) * 3
            bonus_points = 0.75 * (1 if test_current_status == 'passed' else 0)
            points = (test_points + bonus_points) / no_of_people_involved
        elif no_coding_q:
            test_points = int(no_coding_q) * 3
            bonus_points = 1 * (1 if test_current_status == 'passed' else 0)
            points = (test_points + bonus_points) / no_of_people_involved
        elif no_mcq_q:
            test_points = calculate_mcq_points(int(no_mcq_q))
            bonus_points = 0.5 * (1 if test_current_status == 'passed' else 0)
            points = (test_points + bonus_points) / no_of_people_involved
        else:
            pass
    elif test_type.lower() == 'offline':
        test_points = 10
        bonus_points = 2 * (1 if test_current_status == 'passed' else 0)
        points = (test_points + bonus_points) / no_of_people_involved
    else:
        pass
    return round(points, 2)


def assigned_test_points(test, request):
    try:
        platform_name = None
        mcqs, coding_answers = 0, 0
        online_test = Answer.objects.filter(object_id=test.id, content_type__model='test',
                                            question__title='Select type of test',
                                            question__form_name='online_test').first()
        if not online_test:
            test_type = 'offline'
        else:
            test_type = 'online'
            platform = Answer.objects.filter(object_id=test.id, content_type__model='test', question__title='Platform',
                                             question__form_name='online_test').first()
            if platform:
                platform_name = platform.answer

        MCQ_question_answer = Answer.objects.filter(
            object_id=test.id, content_type__model='test', question__title='Number of MCQ questions'
        ).first()
        if MCQ_question_answer:
            mcqs = MCQ_question_answer.answer

        coding_question_answer = Answer.objects.filter(
            object_id=test.id, content_type__model='test', question__title='Number of coding questions'
        ).first()
        if coding_question_answer:
            coding_answers = coding_question_answer.answer
        employee_associated = test.engineer.all()
        points =calculate_points(
            test_type=test_type,
            test_current_status=test.status,
            test_platform_name=platform_name,
            no_mcq_q=mcqs, no_coding_q=coding_answers,
            no_of_people_involved=len(employee_associated)
        )
        for engineer in employee_associated:
            if 1 <= test.created.month <= 6:
                cycle_start = datetime(test.created.year + 1, 1, 1)
                cycle_end = datetime(test.created.year + 1, 6, 30)
            else:
                cycle_start = datetime(test.created.year, 7, 1)
                cycle_end = datetime(test.created.year, 12, 31)

            cycle = Cycle.objects.get_or_create(start_date=cycle_start, end_date=cycle_end)
            previous_points = EngineerPoint.objects.filter(engineer=engineer, is_active=True)
            engineer_point, created = EngineerPoint.objects.get_or_create(engineer=engineer, cycle=cycle[0])
            if created:
                previous_points.update(is_active=False)
            engineer_point.points = Decimal(str(engineer_point.points)) + Decimal(str(points))
            engineer_point.save()

    except Exception as error:
        write_exception(error, request)
