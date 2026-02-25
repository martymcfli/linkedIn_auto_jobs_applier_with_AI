import base64
import json
import os
import random
import re
import tempfile
import time
import traceback
from datetime import date
from typing import List, Optional, Any, Tuple
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver import ActionChains
import src.utils as utils

class LinkedInEasyApplier:
    def __init__(self, driver: Any, resume_dir: Optional[str], set_old_answers: List[Tuple[str, str, str]], gpt_answerer: Any, resume_generator_manager):
        if resume_dir is None or not os.path.exists(str(resume_dir)):
            utils.printred(f"Resume path not found: {resume_dir}")
            resume_dir = None
        else:
            utils.printyellow(f"Resume loaded: {resume_dir}")
        self.driver = driver
        self.resume_path = resume_dir
        self.set_old_answers = set_old_answers
        self.gpt_answerer = gpt_answerer
        self.resume_generator_manager = resume_generator_manager
        self.all_data = self._load_questions_from_json()

    def _load_questions_from_json(self) -> List[dict]:
        output_file = 'answers.json'
        try:
            try:
                with open(output_file, 'r') as f:
                    try:
                        data = json.load(f)
                        if not isinstance(data, list):
                            raise ValueError("JSON file format is incorrect. Expected a list of questions.")
                    except json.JSONDecodeError:
                        data = []
            except FileNotFoundError:
                data = []
            return data
        except Exception:
            tb_str = traceback.format_exc()
            raise Exception(f"Error loading questions data from JSON file: \nTraceback:\n{tb_str}")

    def job_apply(self, job: Any):
        # Don't navigate away from search results — Easy Apply only works in the search view.
        # The job card should already be clicked by the job manager before calling this.
        time.sleep(random.uniform(1, 2))
        try:
            easy_apply_button = self._find_easy_apply_button()
            job.set_job_description(self._get_job_description())
            job.set_recruiter_link(self._get_job_recruiter())
            utils.printyellow("Clicking Easy Apply button...")
            easy_apply_button.click()
            # Wait for the modal to actually appear
            WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'jobs-easy-apply-modal'))
            )
            utils.printyellow("Easy Apply modal opened!")
            time.sleep(random.uniform(0.5, 1))
            self.gpt_answerer.set_job(job)
            self._fill_application_form(job)
        except Exception:
            tb_str = traceback.format_exc()
            utils.printred(f"Apply failed, discarding: {tb_str[:200]}")
            self._discard_application()
            raise Exception(f"Failed to apply to job! Original exception: \nTraceback:\n{tb_str}")

    def _find_easy_apply_button(self) -> WebElement:
        # Wait for the button to appear — no need to scroll the whole page first
        try:
            button = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//button[contains(@class, "jobs-apply-button") and contains(., "Easy Apply")]')
                )
            )
            return button
        except Exception:
            # One retry after refresh
            utils.printyellow("Easy Apply button not found, refreshing page...")
            self.driver.refresh()
            time.sleep(3)
            button = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//button[contains(@class, "jobs-apply-button") and contains(., "Easy Apply")]')
                )
            )
            return button

    def _get_job_description(self) -> str:
        try:
            # Try to click "See more" button (may not always exist)
            try:
                see_more_button = self.driver.find_element(By.XPATH, '//button[contains(@aria-label, "see more") or contains(@aria-label, "Show more")]')
                see_more_button.click()
                time.sleep(0.5)
            except:
                pass
            # Try multiple selectors for description
            for selector in ['jobs-description-content__text', 'jobs-description__content', 'jobs-box__html-content']:
                try:
                    description = self.driver.find_element(By.CLASS_NAME, selector).text
                    if description:
                        return description
                except:
                    continue
            # Fallback: grab text from detail pane
            try:
                detail = self.driver.find_element(By.CSS_SELECTOR, '.scaffold-layout__detail')
                return detail.text[:3000]
            except:
                return "No description available"
        except Exception:
            return "No description available"

    def _get_job_recruiter(self):
        # Quick check — don't wait 10 seconds for something that's usually not there
        try:
            hiring_team_section = self.driver.find_element(By.XPATH, '//h2[text()="Meet the hiring team"]')
            recruiter_element = hiring_team_section.find_element(By.XPATH, './/following::a[contains(@href, "linkedin.com/in/")]')
            return recruiter_element.get_attribute('href')
        except:
            return ""

    def _fill_application_form(self, job):
        while True:
            self.fill_up(job)
            if self._next_or_submit():
                break

    def _next_or_submit(self):
        # IMPORTANT: Only look for buttons INSIDE the Easy Apply modal, not the whole page
        modal = self.driver.find_element(By.CLASS_NAME, 'jobs-easy-apply-modal')

        next_button = modal.find_element(By.CLASS_NAME, "artdeco-button--primary")
        button_text = next_button.text.lower().strip()
        utils.printyellow(f"  Form button: '{next_button.text.strip()}'")

        if 'submit application' in button_text:
            self._unfollow_company()
            time.sleep(random.uniform(1.0, 1.5))
            next_button.click()
            time.sleep(random.uniform(2.0, 3.0))
            # Dismiss the post-submit confirmation modal/overlay so it doesn't block the next job card
            try:
                dismiss_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button.artdeco-modal__dismiss, button[aria-label="Dismiss"], button.artdeco-toast-item__dismiss')
                for btn in dismiss_buttons:
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(0.5)
            except:
                pass
            return True

        if 'review' in button_text:
            # Review page — just click through, don't check for errors
            utils.printyellow("  Clicking Review...")
            next_button.click()
            time.sleep(random.uniform(1.5, 2.5))
            return False

        # Regular "Next" button
        time.sleep(random.uniform(0.5, 1.0))
        next_button.click()
        time.sleep(random.uniform(1.5, 2.5))

        # Only check for errors on form pages, not review/submit pages
        try:
            modal = self.driver.find_element(By.CLASS_NAME, 'jobs-easy-apply-modal')
            # Check if we're now on a review or submit page — if so, skip error check
            try:
                current_btn = modal.find_element(By.CLASS_NAME, "artdeco-button--primary")
                current_text = current_btn.text.lower().strip()
                if 'submit' in current_text or 'review' in current_text:
                    return False
            except:
                pass
            self._check_for_errors()
        except:
            pass

    def _unfollow_company(self) -> None:
        try:
            follow_checkbox = self.driver.find_element(
                By.XPATH, "//label[contains(.,'to stay up to date with their page.')]")
            follow_checkbox.click()
        except Exception as e:
            pass

    def _check_for_errors(self) -> None:
        modal = self.driver.find_element(By.CLASS_NAME, 'jobs-easy-apply-modal')
        # If we're on a review or submit page, never raise — just return
        try:
            btn = modal.find_element(By.CLASS_NAME, "artdeco-button--primary")
            btn_text = btn.text.lower().strip()
            if 'submit' in btn_text or 'review' in btn_text:
                return
        except:
            pass
        error_elements = modal.find_elements(By.CLASS_NAME, 'artdeco-inline-feedback--error')
        if error_elements:
            error_texts = [e.text for e in error_elements if e.text.strip()]
            if not error_texts:
                return
            utils.printred(f"  Form errors detected: {error_texts}")
            if hasattr(self, '_error_retry_count'):
                self._error_retry_count += 1
            else:
                self._error_retry_count = 1
            # Give it more attempts before giving up
            if self._error_retry_count >= 6:
                self._error_retry_count = 0
                raise Exception(f"Failed after retries. Errors: {error_texts}")
            utils.printyellow("  Retrying form fill...")

    def _discard_application(self) -> None:
        try:
            # Close the Easy Apply modal
            dismiss_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button.artdeco-modal__dismiss, button[aria-label="Dismiss"]')
            for btn in dismiss_buttons:
                if btn.is_displayed():
                    btn.click()
                    break
            time.sleep(random.uniform(1, 2))
            # Confirm discard if prompted
            confirm_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button.artdeco-modal__confirm-dialog-btn, button[data-control-name="discard_application_confirm_btn"]')
            for btn in confirm_buttons:
                if btn.is_displayed():
                    btn.click()
                    break
            time.sleep(random.uniform(1, 2))
        except Exception:
            pass
        # Final cleanup — dismiss any remaining overlays
        try:
            overlays = self.driver.find_elements(By.CSS_SELECTOR, '.artdeco-modal-overlay--is-top-layer button.artdeco-modal__dismiss')
            for o in overlays:
                if o.is_displayed():
                    o.click()
                    time.sleep(0.5)
        except:
            pass

    def fill_up(self, job) -> None:
        modal = self.driver.find_element(By.CLASS_NAME, 'jobs-easy-apply-modal')

        # Handle file uploads first
        file_uploads = modal.find_elements(By.XPATH, ".//input[@type='file']")
        if file_uploads:
            self._handle_upload_fields(modal, job)

        # Handle all dropdowns (select elements)
        selects = modal.find_elements(By.TAG_NAME, 'select')
        for select_el in selects:
            try:
                self._handle_single_dropdown(select_el, modal)
            except Exception as e:
                utils.printred(f"  Dropdown error: {e}")

        # Handle all text/number inputs (skip hidden, file, radio, checkbox)
        inputs = modal.find_elements(By.TAG_NAME, 'input')
        for inp in inputs:
            itype = (inp.get_attribute('type') or 'text').lower()
            if itype in ('hidden', 'file', 'radio', 'checkbox'):
                continue
            try:
                self._handle_single_input(inp, modal)
            except Exception as e:
                utils.printred(f"  Input error: {e}")

        # Handle textareas
        textareas = modal.find_elements(By.TAG_NAME, 'textarea')
        for ta in textareas:
            try:
                self._handle_single_input(ta, modal)
            except Exception as e:
                utils.printred(f"  Textarea error: {e}")

        # Handle radio buttons (Yes/No questions etc)
        radio_groups = modal.find_elements(By.CLASS_NAME, 'fb-text-selectable__option')
        if radio_groups:
            self._handle_radio_group(radio_groups, modal)

        # Handle checkboxes — check consent/terms/acknowledgment, but NOT "top choice"
        checkboxes = modal.find_elements(By.XPATH, ".//input[@type='checkbox']")
        for cb in checkboxes:
            try:
                if not cb.is_selected():
                    # Get surrounding text to decide whether to check
                    try:
                        label = cb.find_element(By.XPATH, './ancestor::div[1]//label')
                        label_text = label.text.lower()
                    except:
                        label_text = ""
                    # Skip "top choice" and "follow" checkboxes
                    skip_keywords = ['top choice', 'top pick', 'follow', 'stay up to date']
                    if any(kw in label_text for kw in skip_keywords):
                        utils.printyellow(f"  Skipping checkbox: {label_text[:40]}")
                        continue
                    try:
                        label.click()
                    except:
                        self.driver.execute_script("arguments[0].click()", cb)
                    utils.printyellow(f"  Checked: {label_text[:40] if label_text else 'checkbox'}")
            except:
                pass

        # Handle fieldset-based radio groups (multiple groups on one page)
        fieldsets = modal.find_elements(By.TAG_NAME, 'fieldset')
        for fieldset in fieldsets:
            radios = fieldset.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')
            if not radios:
                continue
            # Check if any radio in this group is already selected
            any_selected = any(r.is_selected() for r in radios)
            if any_selected:
                continue
            # Get the question from the legend
            try:
                question_text = fieldset.find_element(By.TAG_NAME, 'legend').text.lower().strip()
            except:
                question_text = ""
            if not question_text:
                continue
            # Get option labels
            labels = fieldset.find_elements(By.TAG_NAME, 'label')
            options = [l.text.strip() for l in labels if l.text.strip()]
            if not options:
                continue
            utils.printyellow(f"  Fieldset radio Q: {question_text[:60]} | options: {options[:5]}")
            answer = self.gpt_answerer.answer_question_from_options(question_text, options)
            # Click the matching label
            for label in labels:
                if answer.lower() in label.text.lower() or label.text.lower() in answer.lower():
                    label.click()
                    utils.printyellow(f"  Selected: {label.text.strip()}")
                    break
            else:
                # Fuzzy match — click first non-empty label
                if labels:
                    labels[0].click()
                    utils.printyellow(f"  Selected (fallback): {labels[0].text.strip()}")

    def _handle_single_dropdown(self, select_el: WebElement, modal: WebElement) -> None:
        select = Select(select_el)
        options = [o.text for o in select.options]
        current = select.first_selected_option.text.strip()

        # Skip if already meaningfully selected
        placeholder_texts = ['select an option', 'select', '', '--', 'choose an option', 'none', 'choose one', 'please select']
        if current.lower().strip() not in placeholder_texts:
            return

        # Find the label
        sid = select_el.get_attribute('id')
        question_text = ""
        if sid:
            try:
                label = modal.find_element(By.CSS_SELECTOR, f'label[for="{sid}"]')
                question_text = label.text.lower().strip()
            except:
                pass
        if not question_text:
            try:
                parent = select_el.find_element(By.XPATH, './ancestor::div[contains(@class, "fb-dash-form-element") or contains(@class, "form-element")]')
                question_text = parent.text.split('\n')[0].lower().strip()
            except:
                question_text = "unknown dropdown question"

        utils.printyellow(f"  Dropdown Q: {question_text[:60]} | options: {options[:5]}")

        # Check cache
        for item in self.all_data:
            if self._sanitize_text(question_text) in item.get('question', '') and item.get('type') == 'dropdown':
                try:
                    select.select_by_visible_text(item['answer'])
                    utils.printyellow(f"  Selected (cached): {item['answer']}")
                    return
                except:
                    break

        answer = self.gpt_answerer.answer_question_from_options(question_text, options)
        self._save_questions_to_json({'type': 'dropdown', 'question': question_text, 'answer': answer})
        try:
            select.select_by_visible_text(answer)
        except:
            # Fuzzy match
            best = self.gpt_answerer.find_best_match(answer, options)
            select.select_by_visible_text(best)
            answer = best
        utils.printyellow(f"  Selected: {answer}")

    def _handle_single_input(self, field: WebElement, modal: WebElement) -> None:
        # Skip if already filled
        current_val = field.get_attribute('value') or ''
        if current_val.strip():
            return

        # Find the label
        fid = field.get_attribute('id')
        question_text = ""
        if fid:
            try:
                label = modal.find_element(By.CSS_SELECTOR, f'label[for="{fid}"]')
                question_text = label.text.lower().strip()
            except:
                pass
        if not question_text:
            try:
                parent = field.find_element(By.XPATH, './ancestor::div[contains(@class, "fb-dash-form-element") or contains(@class, "form-element")]')
                labels = parent.find_elements(By.TAG_NAME, 'label')
                if labels:
                    question_text = labels[0].text.lower().strip()
            except:
                pass
        if not question_text:
            question_text = field.get_attribute('aria-label') or field.get_attribute('placeholder') or 'unknown question'
            question_text = question_text.lower().strip()

        if not question_text or question_text == 'unknown question':
            return

        # Skip LinkedIn profile education/work history section fields entirely
        # These are pre-filled from your profile and shouldn't be touched
        try:
            section_ancestor = field.find_element(By.XPATH, './ancestor::div[contains(@class, "jobs-easy-apply-form-section")]')
            section_text = section_ancestor.text.lower()[:200]
            if any(kw in section_text for kw in ['education', 'school name', 'degree', 'work experience', 'title at']):
                utils.printyellow(f"  Skipping profile section field: {question_text[:40]}")
                return
        except:
            pass

        # Handle location/city typeahead fields — type and select from dropdown
        # ONLY for questions about YOUR current location, not education/work fields
        location_keywords = ['your city', 'your location', 'where are you located', 'current location', 'current city', 'location (city)', 'city you', 'relocat', 'where do you live', 'based in', 'reside']
        is_location_q = any(kw in question_text for kw in location_keywords)
        if is_location_q:
            utils.printyellow(f"  Location Q: {question_text[:60]} — typing Brooklyn, NY")
            # Click field to focus, then clear properly
            field.click()
            time.sleep(0.3)
            field.send_keys(Keys.CONTROL + "a")
            field.send_keys(Keys.DELETE)
            time.sleep(0.3)
            # Try typing "Brooklyn, NY" slowly
            for char in "Brooklyn, NY":
                field.send_keys(char)
                time.sleep(0.1)
            time.sleep(3)
            # Scope typeahead search to modal
            try:
                modal = self.driver.find_element(By.CSS_SELECTOR, '.jobs-easy-apply-modal')
            except:
                modal = self.driver
            typeahead_selectors = [
                '.search-typeahead-v2__hit',
                '[data-test-single-typeahead-entity-form-search-result]',
                '.basic-typeahead__selectable',
                '[role="option"]',
                '[role="listbox"] li',
            ]
            clicked = False
            for sel in typeahead_selectors:
                try:
                    suggestions = modal.find_elements(By.CSS_SELECTOR, sel)
                    if suggestions:
                        utils.printyellow(f"  Found {len(suggestions)} typeahead suggestions with '{sel}'")
                        for s in suggestions:
                            if s.is_displayed():
                                s.click()
                                clicked = True
                                utils.printyellow(f"  Selected: {s.text[:40]}")
                                break
                        if clicked:
                            break
                except:
                    continue
            if not clicked:
                # Try clearing and typing just "Brooklyn" instead
                utils.printyellow(f"  No suggestions for 'Brooklyn, NY' — trying just 'Brooklyn'")
                field.click()
                field.send_keys(Keys.CONTROL + "a")
                field.send_keys(Keys.DELETE)
                time.sleep(0.3)
                for char in "Brooklyn":
                    field.send_keys(char)
                    time.sleep(0.1)
                time.sleep(3)
                for sel in typeahead_selectors:
                    try:
                        suggestions = modal.find_elements(By.CSS_SELECTOR, sel)
                        if suggestions:
                            for s in suggestions:
                                if s.is_displayed():
                                    s.click()
                                    clicked = True
                                    utils.printyellow(f"  Selected: {s.text[:40]}")
                                    break
                            if clicked:
                                break
                    except:
                        continue
            if not clicked:
                # Last resort: keyboard
                utils.printyellow(f"  Keyboard fallback: arrow down + enter")
                field.send_keys(Keys.ARROW_DOWN)
                time.sleep(0.5)
                field.send_keys(Keys.ENTER)
            time.sleep(1)
            return

        # ===== HARDCODED FIELD HANDLERS =====
        # These prevent GPT misrouting (e.g. "address" -> self_identification -> "White")

        # Personal info fields
        if any(kw in question_text for kw in ['first name', 'given name']):
            self._enter_text(field, "Owen")
            utils.printyellow(f"  Personal: {question_text[:40]} -> Owen")
            return
        if any(kw in question_text for kw in ['last name', 'surname', 'family name']):
            self._enter_text(field, "McCormick")
            utils.printyellow(f"  Personal: {question_text[:40]} -> McCormick")
            return
        if any(kw in question_text for kw in ['full name']):
            self._enter_text(field, "Owen McCormick")
            utils.printyellow(f"  Personal: {question_text[:40]} -> Owen McCormick")
            return
        if any(kw in question_text for kw in ['email', 'e-mail']):
            self._enter_text(field, "mcmcowen@gmail.com")
            utils.printyellow(f"  Personal: {question_text[:40]} -> mcmcowen@gmail.com")
            return
        if any(kw in question_text for kw in ['phone', 'mobile', 'cell']):
            self._enter_text(field, "3472681742")
            utils.printyellow(f"  Personal: {question_text[:40]} -> 3472681742")
            return
        if any(kw in question_text for kw in ['linkedin']):
            self._enter_text(field, "https://www.linkedin.com/in/owen-p-mccormick/")
            utils.printyellow(f"  Personal: {question_text[:40]} -> LinkedIn URL")
            return
        if any(kw in question_text for kw in ['street', 'address', 'mailing']):
            self._enter_text(field, "Brooklyn, NY")
            utils.printyellow(f"  Personal: {question_text[:40]} -> Brooklyn, NY")
            return
        if any(kw in question_text for kw in ['zip', 'postal code']):
            self._enter_text(field, "11201")
            utils.printyellow(f"  Personal: {question_text[:40]} -> 11201")
            return
        if question_text in ['state', 'state/province']:
            self._enter_text(field, "New York")
            utils.printyellow(f"  Personal: {question_text[:40]} -> New York")
            return
        if question_text in ['country']:
            self._enter_text(field, "United States")
            utils.printyellow(f"  Personal: {question_text[:40]} -> United States")
            return

        # Pronouns
        if 'pronoun' in question_text:
            self._enter_text(field, "He/Him")
            utils.printyellow(f"  Personal: {question_text[:40]} -> He/Him")
            return

        # Portfolio/website
        portfolio_keywords = ['portfolio', 'website', 'personal site', 'github', 'other link', 'professional link']
        if any(kw in question_text for kw in portfolio_keywords):
            self._enter_text(field, "www.omccormick.com")
            utils.printyellow(f"  Portfolio: {question_text[:40]} -> www.omccormick.com")
            return

        # Education fields
        degree_keywords = ['degree', 'highest level of education', 'education level', 'school', 'university', 'college', 'institution', 'field of study', 'major']
        if any(kw in question_text for kw in degree_keywords):
            if any(kw in question_text for kw in ['school', 'university', 'college', 'institution']):
                answer = "Colorado State University Global"
            elif any(kw in question_text for kw in ['field of study', 'major', 'concentration']):
                answer = "Business Management"
            elif 'gpa' in question_text or 'grade' in question_text:
                answer = "Cum Laude"
            else:
                answer = "Bachelor of Science in Business Management"
            self._enter_text(field, answer)
            utils.printyellow(f"  Degree: {question_text[:40]} -> {answer}")
            return

        # Referral / how did you hear
        if any(kw in question_text for kw in ['referr', 'how did you hear', 'who referred']):
            self._enter_text(field, "LinkedIn")
            utils.printyellow(f"  Referral: {question_text[:40]} -> LinkedIn")
            return

        # Notice period / start date
        if any(kw in question_text for kw in ['notice period', 'when can you start', 'start date', 'earliest start']):
            self._enter_text(field, "2 weeks")
            utils.printyellow(f"  Availability: {question_text[:40]} -> 2 weeks")
            return

        is_numeric = self._is_numeric_field(field)
        if is_numeric:
            question_type = 'numeric'
            utils.printyellow(f"  Numeric Q: {question_text[:60]}")
            # Check cache
            for item in self.all_data:
                if item.get('question') == self._sanitize_text(question_text) and item.get('type') == 'numeric':
                    self._enter_text(field, str(item['answer']))
                    utils.printyellow(f"  Answered (cached): {item['answer']}")
                    return
            answer = self.gpt_answerer.answer_question_numeric(question_text)
            self._save_questions_to_json({'type': 'numeric', 'question': question_text, 'answer': answer})
            self._enter_text(field, str(answer))
            utils.printyellow(f"  Answered: {answer}")
        else:
            question_type = 'textbox'
            utils.printyellow(f"  Text Q: {question_text[:60]}")
            # Check cache
            for item in self.all_data:
                if 'cover' not in item.get('question', '') and item.get('question') == self._sanitize_text(question_text) and item.get('type') == 'textbox':
                    self._enter_text(field, str(item['answer']))
                    utils.printyellow(f"  Answered (cached): {str(item['answer'])[:50]}")
                    return
            answer = self.gpt_answerer.answer_question_textual_wide_range(question_text)
            self._save_questions_to_json({'type': 'textbox', 'question': question_text, 'answer': answer})
            self._enter_text(field, str(answer))
            utils.printyellow(f"  Answered: {str(answer)[:50]}")

    def _handle_radio_group(self, radios: list, modal: WebElement) -> None:
        # Find the question text from the fieldset/legend or nearby label
        try:
            fieldset = radios[0].find_element(By.XPATH, './ancestor::fieldset')
            question_text = fieldset.find_element(By.TAG_NAME, 'legend').text.lower().strip()
        except:
            try:
                parent = radios[0].find_element(By.XPATH, './ancestor::div[contains(@class, "fb-dash-form-element") or contains(@class, "form-element")]')
                question_text = parent.text.split('\n')[0].lower().strip()
            except:
                question_text = "yes/no question"

        # Resume selection page — actively select "O's rez"
        radio_texts = ' '.join([r.text.lower() for r in radios])
        if 'resume' in radio_texts or 'resume' in question_text or '.pdf' in radio_texts or '.docx' in radio_texts:
            utils.printyellow(f"  Resume selection detected — looking for O's rez...")
            for radio in radios:
                radio_label = radio.text.lower()
                if "o's rez" in radio_label or "o's rez" in radio_label:
                    try:
                        radio.find_element(By.TAG_NAME, 'label').click()
                        utils.printyellow(f"  Selected resume: {radio.text.strip()}")
                    except:
                        radio.click()
                    return
            # If not found by name, pick the first non-CV one (skip AI-generated CVs)
            for radio in radios:
                radio_label = radio.text.lower()
                if 'cv_' not in radio_label and 'cv ' not in radio_label:
                    try:
                        radio.find_element(By.TAG_NAME, 'label').click()
                        utils.printyellow(f"  Selected resume (non-CV): {radio.text.strip()}")
                    except:
                        radio.click()
                    return
            utils.printyellow(f"  Could not find O's rez, leaving default")
            return

        options = [r.text.lower().strip() for r in radios if r.text.strip()]
        if not options:
            return

        utils.printyellow(f"  Radio Q: {question_text[:60]} | options: {options}")

        # Check if already selected
        try:
            selected = modal.find_elements(By.CSS_SELECTOR, 'input[type="radio"]:checked')
            if selected:
                return
        except:
            pass

        # Check cache
        for item in self.all_data:
            if self._sanitize_text(question_text) in item.get('question', '') and item.get('type') == 'radio':
                self._select_radio(radios, item['answer'])
                utils.printyellow(f"  Selected (cached): {item['answer']}")
                return

        answer = self.gpt_answerer.answer_question_from_options(question_text, options)
        self._save_questions_to_json({'type': 'radio', 'question': question_text, 'answer': answer})
        self._select_radio(radios, answer)
        utils.printyellow(f"  Selected: {answer}")

    def _handle_upload_fields(self, modal: WebElement, job) -> None:
        file_upload_elements = modal.find_elements(By.XPATH, ".//input[@type='file']")
        for element in file_upload_elements:
            parent = element.find_element(By.XPATH, "..")
            self.driver.execute_script("arguments[0].classList.remove('hidden')", element)
            parent_text = parent.text.lower()
            # Determine if this is a resume or cover letter upload
            if 'cover' in parent_text and 'resume' not in parent_text:
                utils.printyellow("  Uploading cover letter...")
                self._create_and_upload_cover_letter(element, job)
            else:
                # Always use the actual resume file — never generate an AI one
                if self.resume_path is not None and self.resume_path.resolve().is_file():
                    utils.printyellow(f"  Uploading resume: {self.resume_path.name}")
                    element.send_keys(str(self.resume_path.resolve()))
                else:
                    utils.printred("  No resume file found! Skipping upload.")
            time.sleep(1)

    def _create_and_upload_resume(self, element, job):
        folder_path = 'generated_cv'
        os.makedirs(folder_path, exist_ok=True)
        try:
            file_path_pdf = os.path.join(folder_path, f"CV_{random.randint(0, 9999)}.pdf")
            with open(file_path_pdf, "xb") as f:
                f.write(base64.b64decode(self.resume_generator_manager.pdf_base64(job_description_text=job.description)))
            element.send_keys(os.path.abspath(file_path_pdf))
            job.pdf_path = os.path.abspath(file_path_pdf)
            time.sleep(2)
        except Exception:
            tb_str = traceback.format_exc()
            raise Exception(f"Upload failed: \nTraceback:\n{tb_str}")

    def _create_and_upload_cover_letter(self, element: WebElement, job: Any = None) -> None:
        cover_letter = self.gpt_answerer.answer_question_textual_wide_range("Write a cover letter")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf_file:
            letter_path = temp_pdf_file.name
            c = canvas.Canvas(letter_path, pagesize=letter)
            _, height = letter
            text_object = c.beginText(72, height - 72)
            text_object.setFont("Helvetica", 11)
            # Word wrap at ~80 chars per line
            for paragraph in cover_letter.split('\n'):
                words = paragraph.split()
                line = ""
                for word in words:
                    test_line = f"{line} {word}".strip()
                    if len(test_line) > 80:
                        text_object.textLine(line)
                        line = word
                    else:
                        line = test_line
                if line:
                    text_object.textLine(line)
                text_object.textLine("")  # blank line between paragraphs
            c.drawText(text_object)
            c.save()
            element.send_keys(letter_path)

    # Legacy section-based methods removed — fill_up now directly scans the modal for form elements

    def _is_numeric_field(self, field: WebElement) -> bool:
        field_type = (field.get_attribute('type') or '').lower()
        if field_type == 'number':
            return True
        field_id = (field.get_attribute('id') or '').lower()
        if 'numeric' in field_id:
            return True
        inputmode = (field.get_attribute('inputmode') or '').lower()
        if inputmode == 'numeric':
            return True
        # Check the label/question for numeric hints
        try:
            parent = field.find_element(By.XPATH, './ancestor::div[contains(@class, "jobs-easy-apply-form-section__grouping")]')
            label_text = parent.text.lower()
            numeric_keywords = ['how many years', 'years of experience', 'how many', 'gpa', 'salary', 'compensation', 'rate']
            if any(kw in label_text for kw in numeric_keywords):
                return True
        except:
            pass
        return False

    def _enter_text(self, element: WebElement, text: str) -> None:
        element.clear()
        element.send_keys(text)

    def _select_radio(self, radios: List[WebElement], answer: str) -> None:
        for radio in radios:
            if answer in radio.text.lower():
                radio.find_element(By.TAG_NAME, 'label').click()
                return
        radios[-1].find_element(By.TAG_NAME, 'label').click()

    def _select_dropdown_option(self, element: WebElement, text: str) -> None:
        select = Select(element)
        select.select_by_visible_text(text)

    def _save_questions_to_json(self, question_data: dict) -> None:
        output_file = 'answers.json'
        question_data['question'] = self._sanitize_text(question_data['question'])
        try:
            try:
                with open(output_file, 'r') as f:
                    try:
                        data = json.load(f)
                        if not isinstance(data, list):
                            data = []
                    except json.JSONDecodeError:
                        data = []
            except FileNotFoundError:
                data = []
            # Update existing entry if same type+question, otherwise append
            found = False
            for i, item in enumerate(data):
                if item.get('type') == question_data['type'] and item.get('question') == question_data['question']:
                    data[i] = question_data
                    found = True
                    break
            if not found:
                data.append(question_data)
            # Also update in-memory cache
            self.all_data = data
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

    def _sanitize_text(self, text: str) -> str:
        sanitized_text = text.lower()
        sanitized_text = sanitized_text.strip()
        sanitized_text = sanitized_text.replace('"', '')
        sanitized_text = sanitized_text.replace('\\', '')
        sanitized_text = re.sub(r'[\x00-\x1F\x7F]', '', sanitized_text)
        sanitized_text = sanitized_text.replace('\n', ' ').replace('\r', '')
        sanitized_text = sanitized_text.rstrip(',')
        return sanitized_text
