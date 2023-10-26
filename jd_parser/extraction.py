import os
import spacy
import pickle
import jellyfish
from django.conf import settings
from spacy.language import Language

pickle_city_path = os.path.join(settings.MODELS_PATH, 'cities.pkl')
city_model_path = os.path.join(settings.MODELS_PATH, 'nlp_cities_and_states')
role_model_path = os.path.join(settings.MODELS_PATH, 'role_model')

with open(pickle_city_path, 'rb') as file:
    city_matcher = pickle.load(file)

Language.factories['city_matcher'] = lambda nlp, **cfg: city_matcher
nlp_location = spacy.load(city_model_path)
nlp_role = spacy.load(role_model_path)


def fuzzy_match(s1, s2, max_dist=.8):
    return jellyfish.jaro_distance(s1, s2) >= max_dist


def get_city_from_jd(jd):
    doc = nlp_location(jd.lower())
    l = []
    cities = []

    for ent in doc.ents:
        if (ent.label_ == 'USLOC') and (ent.text.title() not in cities):
            l.append({'name': ent.text.title()})
            cities.append(ent.text.title())
    return l


def get_role_from_jd(jd):
    doc = nlp_role(jd)
    l = []
    for ent in doc.ents:
        if ent.label_ == 'ROLE':
            l.append(ent.text)
    return ','.join(set(l))


def extraction(jd):
    role = get_role_from_jd(jd)
    location = get_city_from_jd(jd)

    return {
        "ROLE": role,
        "LOCATION": list(location),
    }
