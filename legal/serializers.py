import os
from rest_framework import serializers

from legal.models import Petition, Document


class DocumentSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()

    def get_file_name(self, obj):
        return os.path.split(obj.file.name)[1]

    class Meta:
        model = Document
        fields = ('id', 'petition', 'creator', 'doc_type', 'file_name')


class DocumentURLSerializer(serializers.ModelSerializer):

    class Meta:
        model = Document
        fields = ('id', 'petition', 'creator', 'doc_type', 'file')


class PetitionSerializer(serializers.ModelSerializer):
    docs = serializers.SerializerMethodField()
    consultant = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField()

    class Meta:
        model = Petition
        fields = ('id', 'petition_type', 'employer', 'consultant', 'assigned_to', 'beneficiary_type', 'docs', 'status')

    def get_docs(self, obj):
        return DocumentURLSerializer(obj.documents.all(), many=True).data

    def get_consultant(self, obj):
        return obj.beneficiary.name

    def get_assigned_to(self, obj):
        return obj.assigned_to.employee_name
