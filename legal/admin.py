from django.contrib import admin

from .models import Petition, Document, Types, DocumentList


@admin.register(Types)
class TypesAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'display_name')
    search_fields = ('id', 'name', 'category', 'display_name')


@admin.register(DocumentList)
class DocumentListAdmin(admin.ModelAdmin):
    list_filter = ('doc_type__name', 'to_show')
    list_display = ('id', 'doc_type', 'to_show', 'petition', 'created')
    search_fields = ('id', 'doc_type__name', 'petition__beneficiary__name')


@admin.register(Petition)
class VisaPetitionAdmin(admin.ModelAdmin):
    list_filter = ('status', 'petition_type', 'premium_processing', 'beneficiary_type', 'is_active')
    search_fields = ('id', 'beneficiary__name', 'assigned_to__employee_name', 'fedex_no', 'uscis_no', 'lca_no')
    list_display = ('id', 'beneficiary', 'status', 'petition_type', 'assigned_to', 'created_by', 'employer',
                    'premium_processing', 'lca_no', 'uscis_no', 'fedex_no', 'is_active')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_filter = ('doc_type__name', 'verified')
    list_display = ('id', 'petition', 'doc_type', 'creator', 'verified')
    search_fields = ('id', 'petition__id', 'petition__beneficiary__name', 'doc_type__name', 'creator__employee_name')
