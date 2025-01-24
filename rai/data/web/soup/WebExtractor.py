from typing import List

from rai.data.web.soup.BaseExtractor import WebSoupExtractor
from rai.data.web.WebModels import WebActionModel, LoginDetectionModel, InputFieldModel, ButtonModel, \
    JavascriptFunctionsModel, SeleniumLocator
import re



class WebActionExtractor(WebSoupExtractor):

    def __init__(self, html):
        super().__init__()
        self.parse(html)

    @classmethod
    def pipeline(cls, html) -> WebActionModel:
        newCls = cls(html)
        return newCls.run()

    def extract_buttons(self):
        """
        Extracts all button-like elements:
          - <button>
          - <input type="button" or "submit">
          - role="button"
          - onclick attributes
        Returns a list of ButtonModel instances.
        """
        buttons_data = []
        try:
            # 1. <button> tags
            all_buttons = self.soup.find_all("button")
            for btn in all_buttons:
                locator = self._build_selenium_locator(btn)
                model = ButtonModel(
                    tag="button",
                    text=btn.get_text(strip=True),
                    id=btn.get("id", ""),
                    class_=btn.get("class", []),   # alias="class"
                    name=btn.get("name", ""),
                    onclick=btn.get("onclick", ""),
                    attributes={
                        k: v for k, v in btn.attrs.items()
                        if k not in ["id", "class", "name", "onclick"]
                    },
                    locator=locator
                )
                buttons_data.append(model)

            # 2. <input> tags with type="button" or "submit"
            input_buttons = self.soup.find_all(
                "input", {"type": re.compile(r"^(button|submit)$", re.IGNORECASE)}
            )
            for inp in input_buttons:
                locator = self._build_selenium_locator(inp)
                model = ButtonModel(
                    tag="input",
                    text=inp.get("value", ""),  # for an input button, text is basically value
                    id=inp.get("id", ""),
                    class_=inp.get("class", []),
                    name=inp.get("name", ""),
                    onclick=inp.get("onclick", ""),
                    attributes={
                        k: v for k, v in inp.attrs.items()
                        if k not in ["id", "class", "name", "onclick", "type", "value"]
                    },
                    locator=locator
                )
                buttons_data.append(model)

            # 3. Elements with role="button"
            role_buttons = self.soup.find_all(attrs={"role": "button"})
            for elem in role_buttons:
                if elem not in all_buttons and elem not in input_buttons:
                    locator = self._build_selenium_locator(elem)
                    model = ButtonModel(
                        tag=elem.name,
                        text=elem.get_text(strip=True),
                        id=elem.get("id", ""),
                        class_=elem.get("class", []),
                        name=elem.get("name", ""),
                        onclick=elem.get("onclick", ""),
                        attributes={
                            k: v for k, v in elem.attrs.items()
                            if k not in ["id", "class", "name", "onclick", "role"]
                        },
                        locator=locator
                    )
                    buttons_data.append(model)

            # 4. Elements with onclick (that aren't already recognized as buttons)
            onclick_elems = self.soup.select('[onclick]')
            for elem in onclick_elems:
                if (
                    elem not in all_buttons
                    and elem not in input_buttons
                    and elem not in role_buttons
                ):
                    locator = self._build_selenium_locator(elem)
                    model = ButtonModel(
                        tag=elem.name,
                        text=elem.get_text(strip=True),
                        id=elem.get("id", ""),
                        class_=elem.get("class", []),
                        name=elem.get("name", ""),
                        onclick=elem.get("onclick", ""),
                        attributes={
                            k: v for k, v in elem.attrs.items()
                            if k not in ["id", "class", "name", "onclick"]
                        },
                        locator=locator
                    )
                    buttons_data.append(model)
        except Exception as e:
            print(e)
        return buttons_data
    def extract_javascript_functions(self):
        script_functions = set()
        onclick_functions = set()
        try:
            # 1) <script> tags
            script_tags = self.soup.find_all("script")
            func_pattern = re.compile(
                r"function\s+([A-Za-z0-9_$]+)\s*\(|([A-Za-z0-9_$]+)\s*=\s*\(.*?\)\s*=>"
            )
            for script in script_tags:
                if script.string:
                    matches = func_pattern.findall(script.string)
                    for match in matches:
                        func_name = match[0] if match[0] else match[1]
                        if func_name:
                            script_functions.add(func_name)

            # 2) Onclick attributes
            onclick_elems = self.soup.select('[onclick]')
            onclick_pattern = re.compile(r"([A-Za-z0-9_$]+)\(")
            for elem in onclick_elems:
                attr_content = elem.get("onclick", "")
                calls = onclick_pattern.findall(attr_content)
                for c in calls:
                    onclick_functions.add(c)

            return JavascriptFunctionsModel(
                script_functions=sorted(script_functions),
                onclick_functions=sorted(onclick_functions),
            )
        except Exception as e:
            print(e)
            return None
    def extract_input_fields(self):
        inputs_data = []
        try:
            # <input> fields
            input_tags = self.soup.find_all("input")
            for inp in input_tags:
                locator = self._build_selenium_locator(inp)
                model = InputFieldModel(
                    tag="input",
                    type=inp.get("type", ""),
                    id=inp.get("id", ""),
                    name=inp.get("name", ""),
                    class_=inp.get("class", []),
                    placeholder=inp.get("placeholder", ""),
                    value=inp.get("value", ""),
                    locator=locator
                )
                inputs_data.append(model)

            # <textarea> fields
            textarea_tags = self.soup.find_all("textarea")
            for ta in textarea_tags:
                locator = self._build_selenium_locator(ta)
                model = InputFieldModel(
                    tag="textarea",
                    id=ta.get("id", ""),
                    name=ta.get("name", ""),
                    class_=ta.get("class", []),
                    placeholder=ta.get("placeholder", ""),
                    text=ta.get_text(strip=True),
                    locator=locator
                )
                inputs_data.append(model)

            # <select> fields
            select_tags = self.soup.find_all("select")
            for sel in select_tags:
                locator = self._build_selenium_locator(sel)
                model = InputFieldModel(
                    tag="select",
                    id=sel.get("id", ""),
                    name=sel.get("name", ""),
                    class_=sel.get("class", []),
                    options=[opt.get_text(strip=True) for opt in sel.find_all("option")],
                    locator=locator
                )
                inputs_data.append(model)
        except Exception as e:
            print(e)
        return inputs_data
    @staticmethod
    def _build_selenium_locator(elem) -> SeleniumLocator:

        try:
            tag_name = elem.name
            element_id = elem.get("id")
            name_attr = elem.get("name")
            classes = elem.get("class", [])

            if element_id:
                css_sel = f"#{element_id}"
            elif classes:
                css_sel = f"{tag_name}." + ".".join(classes)
            else:
                css_sel = tag_name

            class_str = " ".join(classes) if classes else ""

            return SeleniumLocator(
                tag_name=tag_name,
                element_id=element_id,
                name=name_attr,
                class_name=class_str,
                css_selector=css_sel
            )
        except Exception as e:
            print(e)
            return SeleniumLocator(
                tag_name="none",
                element_id="none",
                name="none",
                class_name="none",
                css_selector="none"
            )
    @staticmethod
    def detect_login_fields_and_buttons(inputs_data: List[InputFieldModel], buttons_data: List[ButtonModel]):
        username_patterns = re.compile(r"(user(name)?|email)", re.IGNORECASE)
        password_patterns = re.compile(r"pass(word)?", re.IGNORECASE)
        login_patterns = re.compile(r"login|sign\s*in", re.IGNORECASE)

        possible_username_fields = []
        possible_password_fields = []
        possible_login_buttons = []

        # Check input fields
        for inp in inputs_data:
            combined_text = f"{inp.name or ''} {inp.id or ''} {inp.placeholder or ''}"
            if username_patterns.search(combined_text):
                possible_username_fields.append(inp)

            if (
                inp.type and inp.type.lower() == "password"
            ) or password_patterns.search(combined_text):
                possible_password_fields.append(inp)

        # Check buttons
        for btn in buttons_data:
            combined_btn_text = (
                f"{btn.text or ''} {btn.id or ''} {btn.name or ''} "
                + " ".join(btn.css_class)
            )
            if login_patterns.search(combined_btn_text):
                possible_login_buttons.append(btn)

        return LoginDetectionModel(
            possible_username_fields=possible_username_fields,
            possible_password_fields=possible_password_fields,
            possible_login_buttons=possible_login_buttons,
        )

    def run(self) -> WebActionModel:
        buttons = self.extract_buttons()
        js_funcs = self.extract_javascript_functions()
        input_fields = self.extract_input_fields()
        login_stuff = self.detect_login_fields_and_buttons(input_fields, buttons)

        return WebActionModel(
            buttons=buttons,
            javascript_functions=js_funcs,
            input_fields=input_fields,
            login_detection=login_stuff,
        )
