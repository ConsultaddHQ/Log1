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
    status = random.choice(['on_bench', 'archived', 'on_project'])
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
    cycle = random.choice([1,2,3])
    in_pool = random.choice(['True', 'False'])
    previous_marketing_days = random.choice([0,1,2])
    preferred_location = fuzzy.FuzzyText(fake.city())
    status = random.choice(['open', 'close'])
    consultant = factory.SubFactory(ConsultantFactory)
