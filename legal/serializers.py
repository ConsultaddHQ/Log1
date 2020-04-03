import os
from rest_framework import serializers

from legal.models import Petition, Document


class DocumentSerializer(serializers.ModelSerializer):
    doc_type_name = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()

    def get_category(self, obj):
        return obj.doc_type.category

    def get_doc_type_name(self, obj):
        return obj.doc_type.name

    def get_file_name(self, obj):
        return os.path.split(obj.file.name)[1]

    class Meta:
        model = Document
        fields = ('id', 'petition', 'creator', 'doc_type_name', 'doc_type', 'file_name', 'verified', 'category', 'remark')


class DocumentURLSerializer(serializers.ModelSerializer):
    doc_type_name = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()

    def get_category(self, obj):
        return obj.doc_type.category

    def get_doc_type_name(self, obj):
        return obj.doc_type.name

    class Meta:
        model = Document
        fields = ('id', 'petition', 'creator', 'doc_type_name', 'doc_type', 'file', 'verified', 'category', 'remark')


class PetitionSerializer(serializers.ModelSerializer):
    consultant = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField()

    class Meta:
        model = Petition
        fields = ('id', 'petition_type', 'employer', 'consultant', 'assigned_to', 'beneficiary_type', 'status')

    def get_consultant(self, obj):
        return {
            "id": obj.beneficiary.id,
            "name": obj.beneficiary.name,
            "email": obj.beneficiary.email,
        }

    def get_assigned_to(self, obj):
        return obj.assigned_to.employee_name


class PetitionGetSerializer(serializers.ModelSerializer):
    docs = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField()

    class Meta:
        model = Petition
        fields = ('id', 'petition_type', 'employer', 'consultant', 'assigned_to', 'beneficiary_type', 'docs', 'status',
                  'lca_no', 'uscis_no', 'fedex_no', 'premium_processing', 'created_by', 'is_active')

    def get_docs(self, obj):
        return DocumentURLSerializer(obj.documents.all(), many=True).data

    def get_consultant(self, obj):
        return {
            "id": obj.beneficiary.id,
            "name": obj.beneficiary.name,
            "email": obj.beneficiary.email,
        }

    def get_assigned_to(self, obj):
        return obj.assigned_to.employee_name
