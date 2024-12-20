import psycopg2
from django.db import connection
from django.http import JsonResponse
from django.core.management import BaseCommand
from transformers import AutoTokenizer, AutoModelForCausalLM

from huggingface_hub import login


api_key = "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"
login(api_key)


model_name = "meta-llama/Llama-2-7b-chat-hf"  # Use an appropriate model
tokenizer = AutoTokenizer.from_pretrained(model_name, use_auth_token=True)
model = AutoModelForCausalLM.from_pretrained(model_name, use_auth_token=True)


def execute_sql_query(connection, query):
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        return result
    except (Exception, psycopg2.Error) as error:
        print('Error executing the query:', error)
        return None


def generate_sql_query(user_query):
    """
    Convert user input into an SQL query using a Hugging Face model.
    """
    prompt = f"Convert the following request to SQL: {user_query}"
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(inputs.input_ids, max_length=150)
    sql_query = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return sql_query


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            """
                Generate a report based on user input using the Llama 2 model.
                """
            user_query = "get all submission"
            if not user_query:
                return JsonResponse({"error": "No query provided"}, status=400)

            # Generate the SQL query using the Llama 2 model

            sql_query = generate_sql_query(user_query)
            print(sql_query)
            try:
                # Execute the SQL query
                with connection.cursor() as cursor:
                    cursor.execute(sql_query)
                    rows = cursor.fetchall()
                    columns = [col[0] for col in cursor.description]
                    results = [dict(zip(columns, row)) for row in rows]
                print("results")
                return JsonResponse({"report": results}, status=200)
            except Exception as e:
                print("e")
        except Exception as e:
            print("e")
