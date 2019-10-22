from spacy.matcher import PhraseMatcher
from spacy.tokens import Span


class CityMatcher(object):
    name = 'city_matcher'

    def __init__(self, nlp, terms, label):
        patterns = [nlp(term) for term in terms] + [nlp(term.lower()) for term in terms]
        self.matcher = PhraseMatcher(nlp.vocab)
        self.matcher.add(label, None, *patterns)

    def __call__(self, doc):
        matches = self.matcher(doc)
        spans = []
        for label, start, end in matches:
            span = Span(doc, start, end, label=label)

            spans.append(span)
        doc.ents = spans
        return doc


class SkillMatcher(object):
    name = 'skill_matcher'

    def __init__(self, nlp, terms, label):
        patterns = [nlp(term) for term in terms]
        self.term_list = terms
        self.matcher = PhraseMatcher(nlp.vocab)
        self.matcher.add(label, None, *patterns)

    def __call__(self, doc):
        matches = self.matcher(doc)
        spans = []
        for label, start, end in matches:
            span = Span(doc, start, end, label=label)

            spans.append(span)
        doc.ents = spans
        return doc
