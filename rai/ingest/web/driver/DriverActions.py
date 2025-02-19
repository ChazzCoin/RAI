import time

from F.LOG import Log
from selenium.common import NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from rai.ingest.web.RaiUrl import RaiUrl
from rai.ingest.web.WebModels import WebLoginDetails, SeleniumLocator
from rai.ingest.web.driver.BaseDriver import WebBaseDriver

Log = Log("WebMaster")

class WebBaseActions(WebBaseDriver):
    do_login: bool = False
    login_details: WebLoginDetails = None
    max_scrolls = 5
    login_url = None

    tab_count = 0
    selected_tab = 0

    def action(self): return ActionChains(self.driver)

    """ Future Pipeline Driver """
    def _find_element_by_locator(self, locator: SeleniumLocator):
        if locator.element_id:
            return self.driver.find_element(By.ID, locator.element_id)
        elif locator.name:
            return self.driver.find_element(By.NAME, locator.name)
        elif locator.css_selector:
            return self.driver.find_element(By.CSS_SELECTOR, locator.css_selector)
        else:
            return self.driver.find_element(By.TAG_NAME, locator.tag_name)
    def click_button(self, button_model) -> bool:
        try:
            css_sel = button_model.locator.css_selector
            element = self.driver.find_element(By.CSS_SELECTOR, css_sel)
            element.click()
            return True
        except Exception as e:
            print(e)
            return False
    def fill_input_field(self, input_model, value: str):
        css_sel = input_model.locator.css_selector
        element = self.driver.find_element(By.CSS_SELECTOR, css_sel)
        element.clear()
        element.send_keys(value)
    def fill_textarea(self, textarea_model, value: str):
        css_sel = textarea_model.locator.css_selector
        element = self.driver.find_element(By.CSS_SELECTOR, css_sel)
        element.clear()
        element.send_keys(value)
    def select_dropdown_option(self, select_model, visible_text: str):
        css_sel = select_model.locator.css_selector
        select_element = self.driver.find_element(By.CSS_SELECTOR, css_sel)
        dropdown = Select(select_element)
        dropdown.select_by_visible_text(visible_text)
    """ LOGIN """
    def setup_login(self, username, password):
        if username and password:
            self.do_login = True
            self.login_url = RaiUrl(self.base_url).join_to_base('login')
            self.login_details = WebLoginDetails(username=username, password=password)
    def login(self, username, password):
        if not username and not password: return
        self.setup_login(username, password)
        if not self.do_login: return
        self.driver.get(self.login_url)
        time.sleep(3)
        # Initialize placeholders
        username_element = None
        password_element = None
        login_button_element = None

        try:
            # 1. Find candidate for username
            #    Common practices: type="text" or type="email", name/id that contains "user"/"email"/"login"
            all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
            for inp in all_inputs:
                input_type = inp.get_attribute("type") or ""
                name_attr = (inp.get_attribute("name") or "").lower()
                id_attr = (inp.get_attribute("id") or "").lower()
                placeholder_attr = (inp.get_attribute("placeholder") or "").lower()

                # Try to detect a username or email field:
                # If type is text or email, and if the name/id/placeholder suggests "user" or "email"
                if (
                        (input_type in ["text", "email"]) and
                        ("user" in name_attr or "user" in id_attr or "email" in name_attr or "email" in id_attr or
                         "user" in placeholder_attr or "email" in placeholder_attr)
                ):
                    username_element = inp
                    break
            time.sleep(2)
            # 2. Find candidate for password
            for inp in all_inputs:
                input_type = inp.get_attribute("type") or ""
                if input_type == "password":
                    password_element = inp
                    break

            # 3. Find candidate for Login/Sign-In button
            #    We look for <button> or <input type="submit"> or <input type="button">
            #    containing "Login" or "Sign In" in text/value attributes
            all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
            all_inputs += self.driver.find_elements(By.XPATH, "//input[@type='submit' or @type='button']")
            time.sleep(2)
            # Combine both sets of possible button candidates
            for btn in all_buttons + all_inputs:
                btn_text = (btn.text or "").strip().lower()
                btn_value = (btn.get_attribute("value") or "").strip().lower()

                if any(keyword in btn_text for keyword in ["login", "log in", "sign in", "signin"]):
                    login_button_element = btn
                    break
                if any(keyword in btn_value for keyword in ["login", "log in", "sign in", "signin"]):
                    login_button_element = btn
                    break
        except NoSuchElementException:
            Log.e("Some element(s) could not be found on the page.")

        if self.login_details:
            self.login_details.user_input = username_element
            self.login_details.pass_input = password_element
            self.login_details.login_btn = login_button_element
        else:
            self.login_details = WebLoginDetails(
                user_input=username_element,
                pass_input=password_element,
                login_btn=login_button_element,
            )

        if username_element and password_element and login_button_element:
            self.login_details.success = True
            self.perform_login()
    def perform_login(self):
        Log.i("Logging In...")
        if not self.login_details or not self.login_details.success:
            return
        time.sleep(1)
        if self.login_details.user_input and self.login_details.pass_input and self.login_details.login_btn:
            # Type the username and password
            self.login_details.user_input.clear()  # Clear any existing text (optional)
            self.login_details.user_input.send_keys(self.login_details.username)
            time.sleep(1)
            self.login_details.pass_input.clear()
            self.login_details.pass_input.send_keys(self.login_details.password)
            time.sleep(1)
            # Click the login/sign-in button
            self.login_details.login_btn.click()
            time.sleep(2)
            Log.s("Logged In!")
        else:
            print("Error: One or more login elements were not found or are invalid.")
            Log.e("FAILED to Log In!")
    """ HELPERS """
    def set_tab_count(self):
        try:
            nav_buttons = self.driver.find_elements(By.CSS_SELECTOR, "#scroll-tabs-mobile li a")
            self.tab_count = len(nav_buttons) or 0
        except NoSuchElementException:
            self.tab_count = 0

    def click_nav_tab(self, tab_index=0):
        try:
            nav_buttons = self.driver.find_elements(By.CSS_SELECTOR, "#scroll-tabs-mobile li a")
            self.tab_count = len(nav_buttons)
            next_btn = nav_buttons[tab_index]
            self.driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
            next_btn.click()
            time.sleep(2)
            return True
        except:
            return False

    def click_next_nav_tab(self):
        try:
            nav_buttons = self.driver.find_elements(By.CSS_SELECTOR, "#scroll-tabs-mobile li a")
            self.tab_count = len(nav_buttons)
            next_btn = nav_buttons[self.selected_tab]
            self.driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
            next_btn.click()
            time.sleep(2)
            return True
        except:
            return False
    def click_next_table_page(self, click_times: int=1, selector="nav a.pagination-link.pagination-next"):
        try:
            for i in range(click_times):
                next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                disabled_attr = next_button.get_attribute("disabled")
                if str(disabled_attr) == "disabled" or str(disabled_attr) == "true":
                    return False
                self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                next_button.click()
                time.sleep(1)
                continue
            return True
        except:
            return False
    def handle_popups(self):
        try:
            # Example: Dismiss cookie consent popup if present
            popup_buttons = self.driver.find_elements(By.XPATH,"//button[contains(text(), 'Accept') or contains(text(), 'Agree')]")
            for button in popup_buttons:
                button.click()
                time.sleep(1)  # Allow some time for the popup to close
        except Exception as e:
            Log.e(f"Popup handling error: {str(e)}")
    def do_infinite_scroll_down(self):
        for _ in range(self.max_scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Delay to ensure dynamic content is loaded
    def do_infinite_scroll_up(self):
        for _ in range(self.max_scrolls):
            self.driver.execute_script("window.scrollTo(0, 0);")  # Scroll to the top
            time.sleep(2)  # Delay to ensure dynamic content is loaded