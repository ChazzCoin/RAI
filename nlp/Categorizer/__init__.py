import FairResources
from nlp.Categorizer.MainCategories import MainCategories
from nlp.Categorizer.SubCategories import SubCategories
from nlp.Categorizer import Categorizer
from F import LIST
from F import DICT

MAIN_CATEGORY_NAMES = MainCategories.get_main_fopic_category_names()
SUB_CATEGORY_NAMES = SubCategories.get_sub_category_names()
MAIN_CATEGORY_LIST = MainCategories.keys

"""
::TODO::
When a topic is requested, this class should build all the lists and sources for that topic.
- Each client should get passed this object and use it to do all its searching/matching.
"""
class Topics:
    main_category_names = MAIN_CATEGORY_NAMES
    main_fopic_category_keys = MAIN_CATEGORY_LIST
    all_categories = {}
    main_categories = {}
    sub_categories = {}
    sources = {}

    @classmethod
    def ALL_CATEGORIES(cls):
        newCls = cls()
        newCls.build_all_categories()
        newCls.build_main_categories()
        newCls.build_sub_categories()
        return newCls


    @classmethod
    def RUN_FULL_CATEGORIZER(cls, content) -> { str: { str: ( int, { str: int } ) } }:
        newCls = cls()
        newCls.build_main_categories()
        newCls.build_sub_categories()
        newCls.main_categorizer(content)
        newCls.sub_categorizer(content)
        return { "main_categories": newCls.main_categorizer(content),
                 "sub_categories": newCls.sub_categorizer(content) }

    @classmethod
    def RUN_MAIN_CATEGORIZER(cls, content):
        newCls = cls()
        newCls.build_main_categories()
        return newCls.main_categorizer(content)

    @classmethod
    def RUN_SUB_CATEGORIZER(cls, content):
        newCls = cls()
        newCls.build_sub_categories()
        return newCls.sub_categorizer(content)

    @classmethod
    def RUN_ALL_CATEGORIZER(cls, content):
        newCls = cls()
        newCls.build_main_categories()
        return newCls.main_categorizer(content)

    # -> Main -> Build All Main Categories -> Dict {}
    def build_main_categories(self, categories: [] = None):
        if categories is None:
            categories = MainCategories.get_main_fopic_category_names()
        """  DYNAMIC {JSON/DICT} BUILDER  """
        for category in categories:
            if category == "keys" or str(category).startswith("__"):
                continue
            category = category.lower()
            self.main_categories[category] = self.build_single_main_category(category)

    # -> Main -> Build All Main Categories -> Dict {}
    def build_all_categories(self, categories: [] = None):
        if categories is None:
            categories = MainCategories.get_main_fopic_category_names()
        """  DYNAMIC {JSON/DICT} BUILDER  """
        for category in categories:
            if category == "keys" or str(category).startswith("__"):
                continue
            category = category.lower()
            temp = self.build_single_main_category(category)
            self.all_categories = DICT.lazy_merge_dicts(self.all_categories, temp)

    # -> Main -> Build Single Main Category into Dict {}
    def build_single_main_category(self, category) -> {}:
        temp_json = {}
        for term in self.main_fopic_category_keys:
            tempList = self.get_main_category_var(self.combine_var_name(category, term))
            temp_json[term] = LIST.scramble(tempList)
        return temp_json

    # -> SUB -> Build All Sub Categories into Dict {}
    def build_sub_categories(self) -> {}:
        temp_json = {}
        for sub_cat in SUB_CATEGORY_NAMES:
            temp_json[sub_cat] = self.get_sub_category_var(sub_cat)
        self.sub_categories = temp_json

    def sub_categorizer(self, *content):
        return Categorizer.categorizer_layer2(content=content, categories=self.sub_categories)

    def main_categorizer(self, *content):
        return Categorizer.categorizer_layer2(content=content, categories=self.main_categories)

    def main_secondary_categorizer(self, topicName, *content):
        topic = self.main_categories[topicName]
        secondary_terms = topic["secondary_weighted_terms"]
        return Categorizer.categorizer_layer2(content=content, categories=secondary_terms)

    def score_categorizer(self, sentences):
        return Categorizer.score_sentences(sentences=sentences, weighted_words=self.get_all_weighted_terms())

    """HELPERS"""
    def get_all_weighted_terms(self):
        all_weighted = {}
        for category_name in self.main_categories.keys():
            # -> Extract Weighted Terms from Category/SubCategory
            weighted_terms = DICT.get("weighted_terms", self.main_categories[category_name], default=False)
            all_weighted = DICT.lazy_merge_dicts(all_weighted, weighted_terms)
        return all_weighted

    @staticmethod
    def get_main_category_var(var_name):
        """  GETTER HELPER  """
        try:
            cls = MainCategories()
            if hasattr(cls, var_name):
                obj = cls.__getattribute__(var_name)
                return obj
            return []
        except Exception as e:
            print(f"Failed to get attribute. e=[ {e} ]")
            return []

    @staticmethod
    def get_sub_category_var(var_name):
        """  GETTER HELPER  """
        try:
            obj = SubCategories().__getattribute__(var_name)
            return obj
        except Exception as e:
            print(f"Failed to get attribute. e=[ {e} ]")
            return []

    @staticmethod
    def combine_var_name(topic, term):
        return topic + "_" + term



if __name__ == "__main__":
    # print(TERMS_LIST)
    t = Topics.ALL_CATEGORIES()
    collection = "models"
    # -> Model
    name = "programming"
    weighted_terms = t.main_categories[name]["weighted_terms"]
    secondary_weighted_terms = t.main_categories[name]["secondary_weighted_terms"]
    from FCM.Jarticle.jModels import jModels
    jm = jModels()
    modelQ = jm.create_model_query(name, weighted_terms, secondary_weighted_terms)
    jm.add_model(modelQ)