from django.db.models import Q


class SubmissionQuerySet:

    @staticmethod
    def RBAC_filter_kwargs_by_role(user):
        """
        Return filter and exclude arguments using Q objects for optimized handling of conditions.
        """

        if "attio_user" in user.roles:
            WORK_TYPE = "c2c"
            EMPLOYER = "consultadd"
            SUBMISSION_AFTER = "2024-12-31"
            CONSULTANT_STATUS = "on_project"

            # Filter conditions combined with AND
            filter_q = Q(
                vendor_contact__isnull=False, employer=EMPLOYER, client__isnull=False,
                created__gt=SUBMISSION_AFTER, rate__isnull=False, work_type=WORK_TYPE
            )

            # Exclude conditions combined with OR
            exclude_q = Q(
                consultant_marketing__consultant__status=CONSULTANT_STATUS
            ) | Q(
                rate=0
            )

            return {"filter_q": filter_q, "exclude_q": exclude_q}

        elif "usa_employee" in user.roles:
            # OR condition for filter
            filter_q = Q(
                Q(created_by=user) | Q(consultant_marketing__consultant__internal_user_profile=user)
            )
            return {"filter_q": filter_q}

        elif "superadmin" in user.roles or "admin" in user.roles:
            # No restrictions for superadmin or admin
            return {}

        elif "marketer" in user.roles:
            # Marketers can only see their submissions
            filter_q = Q(created_by=user, consultant_marketing__in_pool=True, consultant_marketing__status="open")
            return {"filter_q": filter_q}

        elif "supervisor" in user.roles:
            # Supervisors exclude their own submissions in OR format
            return {}

        else:
            # Default case: restrict access (no records returned)
            return {}

    @staticmethod
    def ABAC_filter_kwargs_by_role(permission_set):
        if "attio_user" in permission_set.get("roles"):
            return {
                "fields": [
                    "city", "created_by", "marketing_team", "vendor_company_info", "consultant_name",
                ]
            }
