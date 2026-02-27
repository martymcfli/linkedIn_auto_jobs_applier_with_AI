import os
import random
import time
import traceback
from itertools import product
from pathlib import Path
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import src.utils as utils
from src.job import Job
from src.linkedIn_easy_applier import LinkedInEasyApplier
import json


class EnvironmentKeys:
    def __init__(self):
        self.skip_apply = self._read_env_key_bool("SKIP_APPLY")
        self.disable_description_filter = self._read_env_key_bool("DISABLE_DESCRIPTION_FILTER")

    @staticmethod
    def _read_env_key(key: str) -> str:
        return os.getenv(key, "")

    @staticmethod
    def _read_env_key_bool(key: str) -> bool:
        return os.getenv(key) == "True"

class LinkedInJobManager:
    def __init__(self, driver):
        self.driver = driver
        self.set_old_answers = set()
        self.easy_applier_component = None

    def set_parameters(self, parameters):
        self.company_blacklist = parameters.get('companyBlacklist', []) or []
        self.title_blacklist = parameters.get('titleBlacklist', []) or []
        self.positions = parameters.get('positions', [])
        self.locations = parameters.get('locations', [])
        self.base_search_url = self.get_base_search_url(parameters)
        self.seen_jobs = []
        resume_path = parameters.get('uploads', {}).get('resume', None)
        if resume_path is not None and Path(resume_path).exists():
            self.resume_path = Path(resume_path)
        else:
            self.resume_path = None
        self.output_file_directory = Path(parameters['outputFileDirectory'])
        self.env_config = EnvironmentKeys()

    def set_gpt_answerer(self, gpt_answerer):
        self.gpt_answerer = gpt_answerer

    def set_resume_generator_manager(self, resume_generator_manager):
        self.resume_generator_manager = resume_generator_manager

    def start_applying(self):
        self.easy_applier_component = LinkedInEasyApplier(self.driver, self.resume_path, self.set_old_answers, self.gpt_answerer, self.resume_generator_manager)
        searches = list(product(self.positions, self.locations))
        random.shuffle(searches)
        page_sleep = 0
        minimum_time = 10
        minimum_page_time = time.time() + minimum_time
        self.successful_applications = 0
        self.successful_jobs = []  # Track jobs we applied to for outreach
        self.max_applications = int(os.environ.get("MAX_APPLICATIONS", 0))  # 0 = unlimited

        for position, location in searches:
            location_url = "&location=" + location
            job_page_number = -1
            utils.printyellow(f"Starting the search for {position} in {location}.")

            try:
                while True:
                    page_sleep += 1
                    job_page_number += 1
                    utils.printyellow(f"Going to job page {job_page_number}")
                    self.next_job_page(position, location_url, job_page_number)
                    time.sleep(random.uniform(1.5, 3.5))
                    utils.printyellow("Starting the application process for this page...")
                    self.apply_jobs()
                    utils.printyellow("Applying to jobs on this page has been completed!")
                    if self.max_applications > 0 and self.successful_applications >= self.max_applications:
                        break

                    time_left = minimum_page_time - time.time()
                    if time_left > 0:
                        utils.printyellow(f"Sleeping for {time_left:.0f} seconds.")
                        time.sleep(time_left)
                        minimum_page_time = time.time() + minimum_time
                    if page_sleep % 5 == 0:
                        sleep_time = random.randint(5, 34)
                        utils.printyellow(f"Sleeping for {sleep_time / 60:.1f} minutes.")
                        time.sleep(sleep_time)
                        page_sleep += 1
            except Exception as e:
                utils.printred(f"Error on search page: {e}")
                utils.printred(traceback.format_exc())
            if self.max_applications > 0 and self.successful_applications >= self.max_applications:
                break
            time_left = minimum_page_time - time.time()
            if time_left > 0:
                utils.printyellow(f"Sleeping for {time_left:.0f} seconds.")
                time.sleep(time_left)
                minimum_page_time = time.time() + minimum_time
            if page_sleep % 5 == 0:
                sleep_time = random.randint(50, 90)
                utils.printyellow(f"Sleeping for {sleep_time / 60:.1f} minutes.")
                time.sleep(sleep_time)
                page_sleep += 1

        # After all applications, do outreach for successful jobs
        if self.successful_jobs:
            self.outreach_batch(self.successful_jobs)

    def outreach_batch(self, jobs):
        """For each job we applied to, find the hiring contact and draft a message."""
        utils.printyellow(f"\n{'='*60}")
        utils.printyellow(f"OUTREACH: Drafting messages for {len(jobs)} applications")
        utils.printyellow(f"{'='*60}\n")

        MESSAGE_TEMPLATE = (
            "Hey {name} — I just applied for the {job_title} role at {company}. "
            "I've spent the last seven years in client management and ran a lifestyle brand, "
            "most recently consulting for international startups on CRM and process work. "
            "Figured I'd reach out directly. Happy to chat if it makes sense."
        )

        for job in jobs:
            try:
                utils.printyellow(f"Outreach: {job.title} at {job.company}...")

                # If we already have a recruiter link from the application, use it
                if job.recruiter_link:
                    contact_url = job.recruiter_link
                    utils.printyellow(f"  Using recruiter link: {contact_url}")
                else:
                    # Navigate to the job page to find hiring team
                    contact_url = self._find_hiring_contact(job)

                if not contact_url:
                    utils.printyellow(f"  No contact found for {job.company}, skipping outreach.")
                    continue

                # Get the person's name from their profile
                contact_name = self._get_profile_name(contact_url)
                if not contact_name:
                    utils.printyellow(f"  Couldn't get name from profile, skipping.")
                    continue

                # Draft the message
                first_name = contact_name.split()[0]
                message = MESSAGE_TEMPLATE.format(
                    name=first_name,
                    job_title=job.title.split('\n')[0].strip(),
                    company=job.company.strip()
                )

                # Open message window and type it
                self._send_draft_message(contact_url, contact_name, message)
                utils.printyellow(f"  Message drafted for {contact_name} — REVIEW AND HIT SEND")
                time.sleep(2)

            except Exception as e:
                utils.printred(f"  Outreach failed for {job.company}: {e}")
                continue

        utils.printyellow(f"\n{'='*60}")
        utils.printyellow(f"OUTREACH COMPLETE — Check LinkedIn for draft messages to review and send")
        utils.printyellow(f"{'='*60}\n")

    def _find_hiring_contact(self, job):
        """Navigate to the job page and find the hiring team contact."""
        try:
            if job.link:
                self.driver.get(job.link)
                time.sleep(3)

            # Look for "Meet the hiring team" section
            try:
                hiring_section = self.driver.find_element(
                    By.XPATH, '//h2[contains(text(), "Meet the hiring team") or contains(text(), "meet the hiring team")]'
                )
                # Find the first profile link in or after this section
                profile_link = hiring_section.find_element(
                    By.XPATH, './/following::a[contains(@href, "/in/")]'
                )
                url = profile_link.get_attribute('href').split('?')[0]
                utils.printyellow(f"  Found hiring team contact: {url}")
                return url
            except:
                pass

            # Look for recruiter/poster info in the job detail
            try:
                poster = self.driver.find_element(
                    By.CSS_SELECTOR, 'a.jobs-poster__name, a[data-tracking-control-name="public_jobs_topcard-author"]'
                )
                url = poster.get_attribute('href').split('?')[0]
                utils.printyellow(f"  Found job poster: {url}")
                return url
            except:
                pass

            # Look for any "Message" button that links to a person
            try:
                message_btn = self.driver.find_element(
                    By.XPATH, '//button[contains(text(), "Message")]'
                )
                # The message button is usually near a profile link
                parent = message_btn.find_element(By.XPATH, './ancestor::div[1]')
                profile_link = parent.find_element(By.XPATH, './/a[contains(@href, "/in/")]')
                url = profile_link.get_attribute('href').split('?')[0]
                utils.printyellow(f"  Found messageable contact: {url}")
                return url
            except:
                pass

        except Exception as e:
            utils.printred(f"  Error finding contact: {e}")

        return None

    def _get_profile_name(self, profile_url):
        """Navigate to a profile and get the person's name."""
        try:
            self.driver.get(profile_url)
            time.sleep(3)
            # Try multiple selectors for the name
            for selector in ['h1.text-heading-xlarge', 'h1.pv-top-card--list-bullet', 'h1']:
                try:
                    name_el = self.driver.find_element(By.CSS_SELECTOR, selector)
                    name = name_el.text.strip()
                    if name and len(name) > 1:
                        utils.printyellow(f"  Contact name: {name}")
                        return name
                except:
                    continue
        except Exception as e:
            utils.printred(f"  Error getting profile name: {e}")
        return None

    def _send_draft_message(self, profile_url, contact_name, message):
        """Open the message window for a contact and type the draft message."""
        # Make sure we're on their profile
        if self.driver.current_url.split('?')[0] != profile_url:
            self.driver.get(profile_url)
            time.sleep(3)

        # Click the Message button on their profile
        try:
            msg_button = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable((By.XPATH,
                    '//button[contains(@class, "message") or contains(text(), "Message")]'
                ))
            )
            msg_button.click()
            time.sleep(2)
        except:
            # Try the "More" dropdown then Message
            try:
                more_btn = self.driver.find_element(By.XPATH, '//button[contains(@aria-label, "More actions")]')
                more_btn.click()
                time.sleep(1)
                msg_option = self.driver.find_element(By.XPATH, '//span[text()="Message"]/..')
                msg_option.click()
                time.sleep(2)
            except:
                utils.printred(f"  Could not open message window for {contact_name}")
                return

        # Find the message input and type the draft
        try:
            # LinkedIn message box is a contenteditable div
            msg_box = WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    'div.msg-form__contenteditable, div[role="textbox"][contenteditable="true"], div.msg-form__msg-content-container--is-active div[contenteditable]'
                ))
            )
            msg_box.click()
            time.sleep(0.5)
            msg_box.send_keys(message)
            utils.printyellow(f"  Typed message for {contact_name} — waiting for you to review and send")
        except Exception as e:
            utils.printred(f"  Could not type message: {e}")

    def apply_jobs(self):
        try:
            no_jobs_element = self.driver.find_element(By.CLASS_NAME, 'jobs-search-two-pane__no-results-banner--expand')
            if 'No matching jobs found' in no_jobs_element.text or 'unfortunately, things aren' in self.driver.page_source.lower():
                raise Exception("No more jobs on this page")
        except NoSuchElementException:
            pass

        # Wait for job list items to load
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "li.scaffold-layout__list-item"))
            )
        except Exception:
            utils.printred("Could not load job results list, refreshing...")
            self.driver.refresh()
            time.sleep(5)
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "li.scaffold-layout__list-item"))
                )
            except Exception:
                raise Exception("Job list never loaded after refresh")

        # Scroll the list to load all items
        try:
            job_results = self.driver.find_element(By.CSS_SELECTOR, ".scaffold-layout__list")
            utils.scroll_slow(self.driver, job_results)
            utils.scroll_slow(self.driver, job_results, step=300, reverse=True)
        except Exception:
            pass

        time.sleep(2)
        job_list_elements = self.driver.find_elements(By.CSS_SELECTOR, 'li.scaffold-layout__list-item')
        if not job_list_elements:
            raise Exception("No job list items found on page")

        utils.printyellow(f"Found {len(job_list_elements)} job cards on this page")

        for job_tile in job_list_elements:
            # Extract info from tile
            job_title, company, job_location, link, apply_method = self.extract_job_information_from_tile(job_tile)
            if not job_title:
                continue

            job = Job(job_title, company, job_location, link, apply_method)
            utils.printyellow(f"Processing: {job.title} at {job.company} [{job.apply_method}]")

            if self.is_blacklisted(job.title, job.company, job.link):
                utils.printyellow(f"Blacklisted {job.title} at {job.company}, skipping...")
                self.write_to_file(job, "skipped")
                continue

            if job.apply_method in {"Continue", "Applied", "Viewed"}:
                utils.printyellow(f"Already applied/viewed/external: {job.title} at {job.company}, skipping...")
                self.write_to_file(job, "skipped")
                continue

            try:
                # Click the job card in the sidebar to load it in the detail pane
                # This keeps us on the search page where Easy Apply actually works
                utils.printyellow(f"Clicking job card for: {job.title}...")
                card_link = job_tile.find_element(By.CSS_SELECTOR, 'a.job-card-container__link')
                card_link.click()
                time.sleep(random.uniform(1.5, 2.5))

                # Now apply from the detail pane
                utils.printyellow(f"Applying to: {job.title} at {job.company}...")
                self.easy_applier_component.job_apply(job)
                self.successful_applications += 1
                self.successful_jobs.append(job)
                utils.printyellow(f"Successfully applied to: {job.title} at {job.company}! ({self.successful_applications} total)")
                self.write_to_file(job, "success")
                if self.max_applications > 0 and self.successful_applications >= self.max_applications:
                    utils.printyellow(f"Reached {self.max_applications} successful applications. Stopping.")
                    return
            except Exception as e:
                utils.printred(f"Failed to apply to {job.title}: {e}")
                self.write_to_file(job, "failed")
                continue

    def write_to_file(self, job, file_name):
        if job.pdf_path:
            pdf_path = Path(job.pdf_path).resolve().as_uri()
        else:
            pdf_path = ""
        data = {
            "company": job.company,
            "job_title": job.title,
            "link": job.link,
            "job_recruiter": job.recruiter_link,
            "job_location": job.location,
            "pdf_path": pdf_path
        }
        file_path = self.output_file_directory / f"{file_name}.json"
        if not file_path.exists():
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump([data], f, indent=4)
        else:
            with open(file_path, 'r+', encoding='utf-8') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = []
                existing_data.append(data)
                f.seek(0)
                json.dump(existing_data, f, indent=4)
                f.truncate()

    def get_base_search_url(self, parameters):
        url_parts = []
        if parameters['remote']:
            url_parts.append("f_CF=f_WRA")
        experience_levels = [str(i+1) for i, (level, v) in enumerate(parameters.get('experienceLevel', {}).items()) if v]
        if experience_levels:
            url_parts.append(f"f_E={','.join(experience_levels)}")
        url_parts.append(f"distance={parameters['distance']}")
        job_types = [key[0].upper() for key, value in parameters.get('jobTypes', {}).items() if value]
        if job_types:
            url_parts.append(f"f_JT={','.join(job_types)}")
        date_mapping = {
            "all time": "",
            "month": "&f_TPR=r2592000",
            "week": "&f_TPR=r604800",
            "24 hours": "&f_TPR=r86400"
        }
        date_param = next((v for k, v in date_mapping.items() if parameters.get('date', {}).get(k)), "")
        url_parts.append("f_LF=f_AL")  # Easy Apply
        base_url = "&".join(url_parts)
        return f"?{base_url}{date_param}"

    def next_job_page(self, position, location, job_page):
        self.driver.get(f"https://www.linkedin.com/jobs/search/{self.base_search_url}&keywords={position}{location}&start={job_page * 25}")

    def extract_job_information_from_tile(self, job_tile):
        job_title, company, job_location, apply_method, link = "", "", "", "", ""
        try:
            title_el = job_tile.find_element(By.CSS_SELECTOR, 'a.job-card-container__link')
            job_title = title_el.text.strip()
            link = title_el.get_attribute('href').split('?')[0]
        except:
            pass
        try:
            company = job_tile.find_element(By.CSS_SELECTOR, '.artdeco-entity-lockup__subtitle').text.strip()
        except:
            pass
        try:
            job_location = job_tile.find_element(By.CSS_SELECTOR, '.artdeco-entity-lockup__caption').text.strip()
        except:
            pass
        try:
            footer = job_tile.find_element(By.CSS_SELECTOR, '.job-card-container__footer-wrapper')
            apply_method = footer.text.strip()
        except:
            apply_method = ""

        return job_title, company, job_location, link, apply_method

    def is_blacklisted(self, job_title, company, link):
        job_title_words = job_title.lower().split(' ')
        title_blacklisted = any(word in job_title_words for word in self.title_blacklist)
        company_blacklisted = company.strip().lower() in (word.strip().lower() for word in self.company_blacklist)
        link_seen = link in self.seen_jobs
        return title_blacklisted or company_blacklisted or link_seen
