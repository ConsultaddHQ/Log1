# import jellyfish
# from django.core.management import BaseCommand
#
# from marketing.models import Submission
# from fuzzywuzzy import fuzz, process
# from itertools import combinations
#
# class Command(BaseCommand):
#
#     # @classmethod
#     # def group_similar_names(cls, names, threshold=50):
#     #     grouped_names = {}  # Dictionary to store groups
#     #
#     #     for name1, name2 in combinations(names, 2):
#     #         similarity_score = fuzz.token_set_ratio(name1, name2)
#     #         if similarity_score >= threshold:
#     #             # Find the groups that contain either name1 or name2
#     #             group1 = None
#     #             group2 = None
#     #             for group_number, group in grouped_names.items():
#     #                 if name1 in group:
#     #                     group1 = group_number
#     #                 if name2 in group:
#     #                     group2 = group_number
#     #
#     #             # Merge the groups if both names are already in different groups
#     #             if group1 is not None and group2 is not None and group1 != group2:
#     #                 grouped_names[group1].update(grouped_names[group2])
#     #                 del grouped_names[group2]
#     #             # Add the names to the same group if one of them is already in a group
#     #             elif group1 is not None:
#     #                 grouped_names[group1].add(name2)
#     #             elif group2 is not None:
#     #                 grouped_names[group2].add(name1)
#     #             # Create a new group if neither name is in an existing group
#     #             else:
#     #                 new_group_number = len(grouped_names) + 1
#     #                 grouped_names[new_group_number] = {name1, name2}
#     #
#     #     return grouped_names
#     @classmethod
#     def group_similar_names(cls,names, threshold):
#         grouped_lists = []
#         processed = set()
#
#         for i, name1 in enumerate(names):
#             if i in processed:
#                 continue
#
#             similar_group = [name1]
#             for j, name2 in enumerate(names[i + 1:], start=i + 1):
#                 jaro_winkler_distance = jellyfish.jaro_winkler(name1, name2)
#                 if jaro_winkler_distance >= threshold:
#                     similar_group.append(name2)
#                     processed.add(j)
#
#             grouped_lists.append(similar_group)
#
#         return grouped_lists
#
#     def handle(self, *args, **options):
#         try:
#             import re
#             import csv
#             queryset = Submission.objects.exclude(client=None).order_by('client').distinct('client').values_list(
#                 'client', flat=True)
#             clients = list(set(re.sub('\W+', '', q).lower() for q in queryset))
#             # clients = list(set(q.lower() for q in queryset))
#             clients.sort()
#             # print(clients)
#             # print(clients)
#             grouped_companies = self.group_similar_names(clients, 0.8)
#             with open('jellyfish.csv', 'w', newline='') as csvfile:
#                 csvwriter = csv.writer(csvfile)
#                 csvwriter.writerow(['Company names'])
#
#                 for group in grouped_companies:
#                     csvwriter.writerow(group)
#
#
#
#             # grouped_companies = self.group_similar_names(clients,0.9)
#             # with open('grouped_companies.csv', 'w', newline='') as csvfile:
#             #     csvwriter = csv.writer(csvfile)
#             #     csvwriter.writerow(['Group Number', 'Company Names'])
#             #
#             #     for group_number, group in grouped_companies.items():
#             #         company_names = ', '.join(group)
#             #         csvwriter.writerow([group_number, company_names])
#
#             # print(grouped_companies)
#             # Rest of your code...
#         except Exception as error:
#            print(error)


# import jellyfish
# from django.core.management import BaseCommand
# from marketing.models import Submission
# import csv
#
# class Command(BaseCommand):
#
#     @classmethod
#     def group_similar_names(cls, names, threshold):
#         grouped_lists = []
#         processed = set()
#
#         for i, name1 in enumerate(names):
#             if i in processed:
#                 continue
#
#             similar_group = [name1]
#             for j, name2 in enumerate(names[i + 1:], start=i + 1):
#                 jaro_winkler_distance = jellyfish.jaro_winkler(name1, name2)
#                 if jaro_winkler_distance >= threshold:
#                     similar_group.append(name2)
#                     processed.add(j)
#
#             grouped_lists.append(similar_group)
#
#         return grouped_lists
#
#     def handle(self, *args, **options):
#         try:
#             import re
#
#             queryset = Submission.objects.exclude(client=None).order_by('client').distinct('client').values_list(
#                 'client', flat=True)
#             clients = list(set(re.sub('\W+', '', q).lower() for q in queryset))
#             clients.sort()
#
#             jaro_winkler_threshold = 0.8
#             grouped_companies = self.group_similar_names(clients, jaro_winkler_threshold)
#
#             with open('jellyfish.csv', 'w', newline='') as csvfile:
#                 csvwriter = csv.writer(csvfile)
#                 csvwriter.writerow(['Company names'])
#
#                 for group in grouped_companies:
#                     company_names = ', '.join(group)  # Join the names in the group
#                     csvwriter.writerow([company_names])  # Write the entire group as a single row
#
#         except Exception as error:
#             print(error)


#
# import jellyfish
# from django.core.management import BaseCommand
# from marketing.models import Submission
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
#             queryset = Submission.objects.exclude(client=None).order_by('client').distinct('client').values_list(
#                 'client', flat=True)
#             clients = list(set(re.sub('\W+', '', q).lower() for q in queryset))
#             clients.sort()
#
#             jaro_winkler_threshold = 0.8
#             # grouped_companies = self.group_similar_names(clients, jaro_winkler_threshold)
#
#             grouped_companies = self.group_companies(clients)
#             print(grouped_companies)
#             # Write the grouped companies to a CSV file
#             output_file = "grouped_companies.csv"
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
from marketing.models import Submission


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

            queryset = Submission.objects.exclude(client=None).order_by('client').distinct('client').values_list(
                'client', flat=True)
            clients = list(set(re.sub('\W+', '', q).lower() for q in queryset))
            clients.sort()

            jaro_winkler_threshold = 0.8
            # grouped_companies = self.group_similar_names(clients, jaro_winkler_threshold)

            grouped_companies = self.group_companies(clients)
            print(grouped_companies)
            # Write the grouped companies to a CSV file
            output_file = "grouped_companies_lcs.csv"

            with open(output_file, mode="w", newline="") as file:
                writer = csv.writer(file)

                # Write the header row
                writer.writerow(["Group", "Company"])

                # Write the grouped companies
                for i, group in enumerate(grouped_companies, start=1):
                    writer.writerow([i, group])
        except Exception as error:
            print(error)
