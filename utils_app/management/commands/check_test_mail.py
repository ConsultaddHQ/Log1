from constance import config
from django.core.management import BaseCommand

from employee.models import User
from marketing.models import Test, Answer
from marketing.utils import structure_mail_data
from utils_app.aws_utils import download_s3_object
from utils_app.models import MapMail
from utils_app.thred_mail import send_email_attachment_multiple
from utils_app.utils import delete_temp_file


class Command(BaseCommand):
    def handle(self, *args, **options):
        # try:
        #     test_type = 'Online'
        #     test = Test.objects.get(id=2952)
        #     consultant = test.submission.consultant
        #     queryset = User.objects.filter(
        #         team=test.submission.marketing_team, role__name__in=['admin', 'proxy'], is_active=True
        #     )
        #     path = []
        #     created_by = test.submission.created_by
        #     skills = ", ".join(skill.title() for skill in test.skills)
        #     to = ['shreyas.k@consultadd.com']
        #     cc = ['shivam.k@consultadd.com']
        #     subject = f'Test :: TST-{test.id} :: {test_type} :: {consultant.name} :: {skills} '
        #     resume = test.submission.attachments.filter(attachment_type='resume')
        #     if resume:
        #         response, error = download_s3_object(resume.first().attachment_file.name)
        #         if not error:
        #             path.append(response)
        #     test_docs = test.attachments.all()
        #     for doc in test_docs:
        #         response, error = download_s3_object(doc.attachment_file.name)
        #         if not error:
        #             path.append(response)
        #     # deadline = datetime.strptime(test.deadline, "%Y-%m-%d").strftime("%b. %d, %Y") if test.deadline else 'NA'
        #     deadline = test.deadline.strftime("%b. %d, %Y") if test.deadline else 'NA'
        #     mail_data = {
        #         'subject': subject,
        #         'to': to, 'cc': cc, 'bcc': [],
        #         'template': '/home/ubuntu/log1/marketing/templates/test_mail.html',
        #         'context': {
        #             'skills': skills,
        #             'deadline': deadline,
        #             'consultant': consultant.name,
        #             'marketer_email': created_by.email,
        #             'consultant_email': consultant.email,
        #             'city': test.submission.current_city,
        #             'visa_end': test.submission.visa_end,
        #             'dob': test.submission.date_of_birth,
        #             'marketer': created_by.employee_name,
        #             'visa_type': test.submission.visa_type,
        #             'consultant_phone': consultant.phone_no,
        #             'visa_start': test.submission.visa_start,
        #             'marketing_email': test.submission.email,
        #             'marketing_phone': test.submission.phone,
        #             'job_title': test.submission.lead.job_title,
        #             'test_link': 'NA',
        #             'is_video': 'No',
        #             'vendor_company': test.submission.lead.vendor_company.name,
        #             'is_offline': 'Yes',
        #             'jd': test.submission.lead.job_desc.replace("\n", " ;newline; "),
        #             'con_informed': 'Yes',
        #             'client': test.submission.client if test.submission.client else 'NA',
        #             'con_timezone':'NA',
        #             'additional_details': 'NA',
        #         },
        #         'attachments': path
        #     }
        #     res, msg, from_mail = send_email_attachment_multiple(mail_data, 'product@consultadd.com', request=None)
        #     delete_temp_file(path)
        try:

            test = Test.objects.get(id=2952)
            consultant = test.submission.consultant
            queryset = User.objects.filter(
                team=test.submission.marketing_team, role__name__in=['admin', 'proxy'], is_active=True
            )
            created_by = test.submission.created_by
            scrum_masters = [user.email for user in queryset]
            skills = ", ".join(skill.title() for skill in test.skills)

            test_type = 'Online'
            if test.is_video:
                test_type = "Video"
            # if test.is_offline:
            #     test_type = 'Offline'
            engineers_email = [user.email for user in test.engineer.all()]
            engineers_email.append(test.submitted_by.email)
            if test.engineer.all():
                engineer = ", ".join(engineer.employee_name for engineer in test.engineer.all())
            else:
                engineer = 'NA'
            answer_qs = Answer.objects.filter(object_id=2952, content_type__model='test')
            ques_answers = []
            for obj in answer_qs:
                ques_answers.append({
                    "id": obj.id,
                    "answer": obj.answer.split(":")[0],
                    "comment": obj.answer.split(":")[-1] if len(obj.answer.split(":"))>1 else None,
                    "question": obj.question.title,
                    "parent_question": obj.parent_question.title if obj.parent_question else None,
                })
            path = list()

            for answer in ques_answers:
                if answer['answer'] == 'submitted':
                    ans = Answer.objects.get(id=answer['id'])
                    test_docs = ans.attachment.filter(attachment_type='test_feedback')
                    answer['answer'] = len(test_docs)
                    for doc in test_docs:
                        response, error = download_s3_object(doc.attachment_file.name)
                        path.append(response)

            to = [created_by.email]
            title = f"Test Completed"
            cc = scrum_masters + [config.ENGINEERING] + engineers_email
            subject = f'Test Completed :: TST-{test.id} :: {test_type} :: {consultant.name} :: {skills}'
            single_question, parent_question = structure_mail_data(ques_answers)
            rate_performance = {}
            for question in ques_answers:
                if question['question'] == 'Rate your performance':
                    rate_performance = question
                    ques_answers.remove(question)
            data = {
                'ques_answers': ques_answers,
                'rate_performance': rate_performance,
            }
            mail_data = {
                'to': to, 'cc': cc, 'bcc': [],
                'subject': subject, 'attachments': path,
                'template': '../templates/submit_engineer_feedback.html',
                'context': {
                    'parent_question': parent_question,
                    'engineer': engineer, 'title': title,
                    'rate_performance': data['rate_performance'],
                    'single_question': single_question, 'remarks': test.engineer_remarks,
                },
            }
            # Need to filter on based one type and objectId
            mail_id = None
            email_object = MapMail.objects.filter(content_type__model="test", object_id=test.id).first()
            if email_object:
                mail_id = email_object.mail_id
            breakpoint()
            res, msg, mail_id = send_email_attachment_multiple(mail_data, config.APP_ADMIN, request=None, mail_id=mail_id)
            delete_temp_file(path)

        except Exception as error:
            print(error)