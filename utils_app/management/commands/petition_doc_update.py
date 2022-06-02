from django.core.management import BaseCommand
from consultant.models import Consultant
from legal.models import Types, Petition, Document, DocumentList


class Command(BaseCommand):
    help = "this command is for updated all petition doc"

    def handle(self, *args, **options):
        all_consultant = Consultant.objects.all()
        for consultant in all_consultant:
            all_petition = Petition.objects.filter(beneficiary_id=consultant.id)
            if all_petition:
                base_petition_id = all_petition.last()
                documents = Document.objects.filter(petition=base_petition_id).\
                    exclude(doc_type__category='Petition Document')
                for petition in all_petition:
                    current_documents = Document.objects.filter(petition=petition.id).\
                        exclude(doc_type__category='Petition Document')
                    if current_documents != documents:
                        for doc in documents:
                            if doc not in current_documents:
                                Document.objects.create(
                                    file=doc.file,
                                    verified=None,
                                    creator=doc.creator,
                                    doc_type_id=doc.doc_type_id,
                                    petition_id=petition.id,
                                )

        print("petition doc updated successfully")
