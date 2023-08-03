# import jellyfish
# from django.core.management import BaseCommand
# from marketing.models import Submission, VendorCompany
# import csv
#
# class Command(BaseCommand):
#
#     @classmethod
#     def calculate_similarity(cls,name1, name2):
#         return jellyfish.jaro_winkler(name1, name2)
#
#     @classmethod
#     def group_companies(cls,companies):
#         groups = []
#
#         for company in companies:
#             found_group = False
#
#             # Try to find a group for the current company
#             for group in groups:
#                 for member in group:
#                     # Check the similarity of the current company with each group member
#                     if cls.calculate_similarity(company, member) > 0.85:
#                         group.append(company)
#                         found_group = True
#                         break
#
#             # If no group was found, create a new group with the current company
#             if not found_group:
#                 groups.append([company])
#
#         return groups
#
#
#     def handle(self, *args, **options):
#         try:
#             import re
#
#             queryset = VendorCompany.objects.all().values_list('name',flat=True)
#             vendors = list(set(re.sub('\W+', '', q).lower() for q in queryset))
#             vendors.sort()
#             print(len(vendors))
#             jaro_winkler_threshold = 0.8
#             # grouped_companies = self.group_similar_names(clients, jaro_winkler_threshold)
#
#             grouped_companies = self.group_companies(vendors)
#             print(grouped_companies)
#             # Write the grouped companies to a CSV file
#             output_file = "vendor_companies_jellyfish.csv"
#
#             with open(output_file, mode="w", newline="") as file:
#                 writer = csv.writer(file)
#
#                 # Write the header row
#                 writer.writerow(["Group", "Company"])
#
#                 # Write the grouped companies
#                 for i, group in enumerate(grouped_companies, start=1):
#                     writer.writerow([i, group])
#         except Exception as error:
#             print(error)


import csv
from django.core.management import BaseCommand
from marketing.models import Submission, VendorCompany


class Command(BaseCommand):

    @classmethod
    def calculate_lcsu_similarity(cls, name1, name2):
        # Function to calculate the length of the Longest Common Substring
        def lcsu_length(X, Y):
            m, n = len(X), len(Y)
            dp = [[0] * (n + 1) for _ in range(m + 1)]
            max_length = 0

            for i in range(1, m + 1):
                for j in range(1, n + 1):
                    if X[i - 1] == Y[j - 1]:
                        dp[i][j] = dp[i - 1][j - 1] + 1
                        max_length = max(max_length, dp[i][j])
                    else:
                        dp[i][j] = 0

            return max_length

        # Calculate the LCSu similarit
        max_length = lcsu_length(name1, name2)
        similarity = max_length / max(len(name1), len(name2))
        return similarity

    @classmethod
    def group_companies(cls, companies):
        groups = []

        for company in companies:
            found_group = False

            # Try to find a group for the current company
            for group in groups:
                for member in group:
                    # Check the LCS similarity of the current company with each group member
                    if cls.calculate_lcsu_similarity(company, member) >= 0.8:
                        group.append(company)
                        found_group = True
                        break

            # If no group was found, create a new group with the current company
            if not found_group:
                groups.append([company])

        return groups

    def handle(self, *args, **options):
        try:
            import re

            queryset = VendorCompany.objects.all().values_list('name', flat=True)
            print(len(queryset))
            vendors = list(set(re.sub('\W+', '', q).lower() for q in queryset))
            vendors.sort()
            #             print(len(vendors))
            jaro_winkler_threshold = 0.8
            # grouped_companies = self.group_similar_names(clients, jaro_winkler_threshold)

            grouped_companies = self.group_companies(vendors)
            print(grouped_companies)
            # Write the grouped companies to a CSV file
            output_file = "vendor_company_lcs.csv"

            with open(output_file, mode="w", newline="") as file:
                writer = csv.writer(file)

                # Write the header row
                writer.writerow(["Group", "Company"])

                # Write the grouped companies
                for i, group in enumerate(grouped_companies, start=1):
                    writer.writerow([i, group])
        except Exception as error:
            print(error)
