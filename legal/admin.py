from django.contrib import admin

from .models import Petition, Document


@admin.register(Petition)
class VisaPetitionAdmin(admin.ModelAdmin):
    list_filter = ('status', 'petition_type', 'premium_processing', 'beneficiary_type', 'is_active')
    search_fields = ('id', 'beneficiary__name', 'assigned_to__employee_name', 'fedex_no', 'uscis_no', 'lca_no')
    list_display = ('id', 'beneficiary', 'status', 'petition_type', 'assigned_to', 'created_by', 'employer',
                    'premium_processing', 'lca_no', 'uscis_no', 'fedex_no', 'is_active')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_filter = ('doc_type', 'verified')
    list_display = ('id', 'petition', 'doc_type', 'creator', 'verified')
    search_fields = ('id', 'petition__id', 'petition__beneficiary__name', 'doc_type', 'creator__employee_name')
