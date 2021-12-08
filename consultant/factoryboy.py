import random
import factory
from .models import *
from faker import Faker
from factory import fuzzy
from marketing.models import Submission, Lead
from factory.django import DjangoModelFactory

fake = Faker()


class ConsultantFactory(DjangoModelFactory):

    class Meta:
        model = Consultant

    email = fuzzy.FuzzyText(fake.email())
    name = fuzzy.FuzzyText(fake.name())
    gender = random.choice(['male', 'female'])
    skills = random.choice(['Python', 'Java', 'React', 'JS', 'Ruby'])
    current_city = fuzzy.FuzzyText(fake.city())
    status = random.choice(['on_bench', 'archived', 'on_project', 'terminated'])
    work_type = random.choice(['c2c', 'full_time'])
    is_active = random.choice(['True', 'False'])
    first_login = random.choice(['True', 'False'])
    remote_only = random.choice(['True', 'False'])
    phone_no = fuzzy.FuzzyInteger(6666666666, 9999999999)
    p_is_active = random.choice(['True', 'False'])
    visa_petition = random.choice(['True', 'False'])


class ConsultantMarketingFactory(DjangoModelFactory):

    class Meta:
        model = ConsultantMarketing

    rtg = random.choice(['True', 'False'])
    cycle = random.choice([1,2,3,])
    in_pool = random.choice(['True', 'False'])
    previous_marketing_days = random.choice([0,1,2])
    preferred_location = fuzzy.FuzzyText(fake.city())
    status = random.choice(['open', 'close'])
    consultant = factory.SubFactory(ConsultantFactory)


class LeadFactory(DjangoModelFactory):

    class Meta:
        model = Lead

    job_desc = fuzzy.FuzzyText(fake.sentence())
    city = fuzzy.FuzzyText(fake.city)
    job_title = random.choice(['SDE', 'ASE', 'Full-stack'])
    primary_skill = random.choice(["true", "false"])


class SubmissionFactory(DjangoModelFactory):

    class Meta:
        model = Submission

    employer = fuzzy.FuzzyText(fake.name())
    rate = fuzzy.FuzzyInteger(45, 120)
    is_active = random.choice(['True', 'False'])
    is_complete = random.choice(['True', 'False'])
    email = fuzzy.FuzzyText(fake.email())
    client = fuzzy.FuzzyText(length=5)
    phone = fuzzy.FuzzyInteger(6666666666, 9999999999)
    status = random.choice(["in_offer", "draft", 'sub', 'project', 'interview'])
    current_city = fuzzy.FuzzyText(fake.city())
    education = random.choice(['phd', 'm.tech', 'b.tech'])
    consultant_marketing = factory.SubFactory(ConsultantMarketingFactory)
