from F import DICT

def get_all_models_to_dict() -> {}:
    model_dict = {}
    for model in results:
        name = DICT.get("name", model)
        weighted_terms = DICT.get("weighted_terms", model)
        secondary_weighted_terms = DICT.get("secondary_weighted_terms", model)
        model_dict[name] = {"weighted_terms": weighted_terms, "secondary_weighted_terms": secondary_weighted_terms}
    return model_dict