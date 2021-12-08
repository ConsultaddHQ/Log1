import factory
from factory import fuzzy
import random
from faker import Faker
from factory.django import DjangoModelFactory
from .models import *

fake = Faker()


class ConsultantFactory(DjangoModelFactory):

    class Meta:
        model = Consultant

    id = fuzzy.FuzzyInteger(1111, 9999)
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