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

    class Meta:
        model = Petition
        fields = '__all__'

    def get_docs(self, obj):
        return DocumentURLSerializer(obj.documents.all(), many=True).data

