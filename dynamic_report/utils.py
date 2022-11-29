from .models import DBTable, Field, Structure



def dynamic_filter(instance, filters, need_first = True):
    try:
        if need_first:
            return instance.objects.filter(**filters).first()
        else:
            return instance.objects.filter(**filters)
        
    except Exception:
        return False
     
    
def get_models_list(model):
    back_ref_model_list = [model]
    back_ref = {}
    models = Structure.objects.filter(model_name=model.name).order_by("id").distinct("id")
    for new_model in models:
        back_ref_model_list.append(new_model.db_table)
        back_ref[new_model.db_table.name] = {}
    return back_ref_model_list, back_ref
    
    
visited = {} 
mapper_list = {}

      
def DFS(model):
    if model.name in visited:
        return mapper_list[model.name]
    data={}
    fields = model.fields.all().order_by("id").distinct("id")
    for field in fields:
        if field.front_ref:
            child_model = DBTable.objects.filter(name=field.model_name).order_by("id").distinct("id")
            if len(child_model) > 0 and child_model.first().name not in visited:
                data1 = DFS(child_model.first())
                data[model.name].append(data1)
                mapper_list[child_model.first().name] = data1
            elif len(child_model) > 0 and child_model.first().name in visited:
                data[model.name].append(mapper_list[child_model.first().name])
        else:
            if model.name not in visited:
                visited[model.name] = [field.id]
                data[model.name] = [{"id":field.id,"field_name":field.field_name,"display_name":field.display_name,"type":field.field_type.name}]
            else:
                data[model.name].append({"id":field.id,"field_name":field.field_name,"display_name":field.display_name,"type":field.field_type.name})
    mapper_list[model.name] = data
    return data