import os
from rest_framework import serializers

from legal.models import Petition, Document, DocumentList, Reason


class PetitionTypeSerializer(serializers.ModelSerializer):
    petition_type = serializers.SerializerMethodField()

    class Meta:
        model = Petition
        fields = ('id', 'petition_type', 'status', 'created')

    @staticmethod
    def get_petition_type(obj):
        return {
            "name": obj.petition_type,
            "display_name": obj.get_petition_type_display(),
        }


class DocumentSerializer(serializers.ModelSerializer):
    doc_type_name = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()

    @staticmethod
    def get_category(obj):
        return obj.doc_type.category

    @staticmethod
    def get_doc_type_name(obj):
        return obj.doc_type.name

    @staticmethod
    def get_file_name(obj):
        return os.path.split(obj.file.name)[1]

    class Meta:
        model = Document
        fields = ('id', 'petition', 'doc_type_name', 'doc_type', 'file_name', 'verified', 'category', 'remark')


class ReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reason
        fields = ('id', 'created', 'petition', 'petition_status', 'reason', 'created_by')


class DocumentURLSerializer(serializers.ModelSerializer):
    doc_type_name = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()

    @staticmethod
    def get_category(obj):
        return obj.doc_type.category

    @staticmethod
    def get_doc_type_name(obj):
        return obj.doc_type.name

    class Meta:
        model = Document
        fields = ('id', 'petition', 'creator', 'doc_type_name', 'doc_type', 'file', 'verified', 'category', 'remark')


class PetitionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Petition
        fields = '__all__'


class PetitionSerializer(serializers.ModelSerializer):
    consultant = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField()
    total_documents = serializers.SerializerMethodField()
    uploaded_documents = serializers.SerializerMethodField()

    class Meta:
        model = Petition
        fields = ('id', 'petition_type', 'employer', 'consultant', 'assigned_to', 'beneficiary_type', 'status',
                  'total_documents', 'uploaded_documents', 'expiry_date')

    @staticmethod
    def get_consultant(obj):
        return {
            "id": obj.beneficiary.id,
            "name": obj.beneficiary.name,
            "email": obj.beneficiary.email,
        }

    @staticmethod
    def get_assigned_to(obj):
        return obj.assigned_to.employee_name

    @staticmethod
    def get_total_documents(obj):
        return DocumentList.objects.filter(petition=obj).count()

    @staticmethod
    def get_uploaded_documents(obj):
        return Document.objects.filter(petition=obj).count()


class PetitionGetSerializer(serializers.ModelSerializer):
    rfe = serializers.SerializerMethodField()
    docs = serializers.SerializerMethodField()
    reasons = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField()

    class Meta:
        model = Petition
        fields = ('id', 'petition_type', 'employer', 'consultant', 'assigned_to', 'beneficiary_type', 'docs', 'reasons',
                  'status', 'lca_no', 'uscis_no', 'fedex_no', 'premium_processing', 'created_by', 'is_active', 'rfe',
                  'expiry_date')

    @staticmethod
    def get_rfe(obj):
        rfe = obj.reasons.filter(petition_status='rfe')
        if rfe:
            return True
        return False

    @staticmethod
    def get_docs(obj):
        return DocumentSerializer(obj.documents.filter(doc_type__category='Petition Document'), many=True).data

    @staticmethod
    def get_reasons(obj):
        return ReasonSerializer(obj.reasons.all(), many=True).data

    @staticmethod
    def get_consultant(obj):
        return {
            "id": obj.beneficiary.id,
            "name": obj.beneficiary.name,
            "email": obj.beneficiary.email,
        }

    @staticmethod
    def get_assigned_to(obj):
        return obj.assigned_to.employee_name
