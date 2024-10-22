# from Utils import FILE
"""
-> Rules
1. Each "topic" has 3 attributes, a. search_terms b. weighted_terms c. rss_feeds
2. Each "topics" attribute starts with the topic name, underscores only.
"""
extended_stop_words = ["with", "more", "s", "has", "have", "they", "this", "their", "was", "not", "said", "also",
                       "most", "but", "from", "whether", "so", "ways", "if", "were", "have", "my", "being", "re", "what",
                       "where", "many", "other", "t", "i", "than", "had", "who", "amoung", "get", "say", "could", "way"]
# meta_names = FILE.load_dict_from_file("meta_names")
# -------------------------------------> CATEGORIES AND THEIR KEY-TERMS <-------------------------------------------- #

MAX_WEIGHT = 200
HIGH_WEIGHT = 130
MIDDLE_WEIGHT = 75
LOW_WEIGHT = 25
MINI_WEIGHT = 10
NANO_WEIGHT = 3

class MainCategories:
    # -> If any lists are added, add here.
    keys = ["search_terms", "weighted_terms", "rss_feeds", "secondary_weighted_terms", "url_sources"]

    def get_var(self, var_name):
        """  GETTER HELPER  """
        return self.__getattribute__(var_name)

    @staticmethod
    def combine_var_name(topic, term):
        return topic + "_" + term

    ####################################################################################################################
    # -> 0. General <-
    ####################################################################################################################
    general = "General"
    general_search_terms = ["business", "government", "federal government", "white house", "politics", "global news",
                            "news", "united states economy", "global economy", "president"]
    
    general_weighted_terms = {"thousand": LOW_WEIGHT,
                              "million": LOW_WEIGHT,
                              "billion": MIDDLE_WEIGHT,
                              "trillion": MIDDLE_WEIGHT,
                              "space": MINI_WEIGHT,
                              "mainstream": MINI_WEIGHT,
                              "property": NANO_WEIGHT,
                              "network": MINI_WEIGHT,
                              "future": LOW_WEIGHT,
                              "crowdfunding": NANO_WEIGHT,
                              "economy": MINI_WEIGHT,
                              "market valuation": MINI_WEIGHT,
                              "Metrics": NANO_WEIGHT,
                              "market action": NANO_WEIGHT,
                              "dominance": NANO_WEIGHT,
                              "assets": MINI_WEIGHT,
                              "Drops": NANO_WEIGHT,
                              "Dips": NANO_WEIGHT,
                              "value proposition": MINI_WEIGHT,
                              "fluctuates": NANO_WEIGHT,
                              "portfolio": NANO_WEIGHT,
                              "crash": NANO_WEIGHT,
                              "optimistic": NANO_WEIGHT,
                              "projections": NANO_WEIGHT,
                              "hedge fund": NANO_WEIGHT,
                              "hedgefund": NANO_WEIGHT,
                              "holders": NANO_WEIGHT,
                              "holder": NANO_WEIGHT,
                              "owns": NANO_WEIGHT,
                              "fund": NANO_WEIGHT,
                              "game": NANO_WEIGHT,
                              "gaming": NANO_WEIGHT,
                              "market capitalization": LOW_WEIGHT,
                              "developer": NANO_WEIGHT,
                              "development": NANO_WEIGHT,
                              "develop": NANO_WEIGHT,
                              "engineer": NANO_WEIGHT,
                              "engineering": NANO_WEIGHT,
                              "4g": MINI_WEIGHT,
                              "5g": MINI_WEIGHT,
                              "6g": MINI_WEIGHT,
                              "fiber": MINI_WEIGHT,
                              "optical": MINI_WEIGHT,
                              "fiber optic": MINI_WEIGHT,
                              "business": NANO_WEIGHT,
                              "businesses": NANO_WEIGHT,
                              "meeting": NANO_WEIGHT,
                              "meetings": NANO_WEIGHT,
                              "committee": NANO_WEIGHT,
                              "fed": MINI_WEIGHT,
                              "the fed": MINI_WEIGHT,
                              "federal": NANO_WEIGHT,
                              "federal reserve": LOW_WEIGHT,
                              "bull market": NANO_WEIGHT,
                              "bear market": NANO_WEIGHT,
                              "inflation": MINI_WEIGHT,
                              "deflation": MINI_WEIGHT,
                              "plunges": MINI_WEIGHT,
                              "leaked": MIDDLE_WEIGHT,
                              "announcement": MINI_WEIGHT}

    ####################################################################################################################
    # -> 2.  <-
    ####################################################################################################################


    ####################################################################################################################
    # -> 3.  <-
    ####################################################################################################################




    @staticmethod
    def get_main_fopic_category_names():
        test = MainCategories.__dict__.keys()
        variables = []
        for item in test:
            if str(item).startswith("__"):
                continue
            elif str(item).startswith("keys"):
                continue
            elif str(item).__contains__("_"):
                continue
            else:
                variables.append(item)
        return variables