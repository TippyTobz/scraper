import logging
import time
import random
from base import JobProvider, JobResult

logger = logging.getLogger(__name__)

# Scrape more than needed so we have enough after filtering by role
SCRAPE_BUFFER = 100

# Backoff range in seconds between scroll actions to avoid rate limiting
SCROLL_BACKOFF_MIN = 1.5
SCROLL_BACKOFF_MAX = 3.0


class HiringCafeProvider(JobProvider):
    """
    Scrapes job listings from hiring.cafe using Selenium in headless mode.
    Includes randomised backoff between scroll actions to avoid rate limiting.
    """

    async def search(self, role: str, limit: int = 20) -> list[JobResult]:
        # Selenium is sync — run in executor to avoid blocking the async event loop
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, self._scrape, role, limit
        )

    def _scrape(self, role: str, limit: int) -> list[JobResult]:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--single-process")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-sync")
        options.add_argument("--metrics-recording-only")
        options.add_argument("--mute-audio")
        options.add_argument("--no-first-run")
        options.add_argument("--safebrowsing-disable-auto-update")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--ignore-ssl-errors")
        options.add_argument("--ignore-certificate-errors-spki-list")

        browser = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        wait = WebDriverWait(browser, 15)

        try:
            # ── Open site ──────────────────────────────────────────────────
            browser.get("https://hiring.cafe/")
            time.sleep(3)

            # ── Set location to United States ──────────────────────────────
            trigger_selectors = [
                "//div[contains(@class,'md:cursor-pointer')]",
                "//div[contains(@class,'cursor-pointer')]",
                "//div[contains(@class,'hidden') and contains(@class,'md:block')]",
            ]
            location_trigger = None
            for selector in trigger_selectors:
                try:
                    location_trigger = WebDriverWait(browser, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    break
                except Exception:
                    continue

            if location_trigger:
                browser.execute_script("arguments[0].click();", location_trigger)
                time.sleep(1)
                try:
                    modal_input = WebDriverWait(browser, 10).until(
                        EC.visibility_of_element_located(
                            (By.ID, "react-select-multi_location_selector-input")
                        )
                    )
                    modal_input.clear()
                    modal_input.send_keys("United States")
                    time.sleep(1)
                    modal_input.send_keys(Keys.RETURN)
                    time.sleep(0.5)

                    try:
                        apply_btn = WebDriverWait(browser, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[text()='Apply']"))
                        )
                        apply_btn.click()
                    except Exception:
                        try:
                            apply_btn = browser.find_element(
                                By.XPATH, "//button[contains(text(),'Apply')]"
                            )
                            browser.execute_script("arguments[0].click();", apply_btn)
                        except Exception:
                            pass

                    time.sleep(3)
                except Exception as e:
                    logger.warning(f"HiringCafe: location setup failed: {e}")

            # ── Search for role ─────────────────────────────────────────────
            search_box = wait.until(
                EC.element_to_be_clickable((By.ID, "query-search-v4"))
            )
            search_box.clear()
            for char in role:
                search_box.send_keys(char)
                time.sleep(0.05)
            search_box.send_keys(Keys.RETURN)

            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.grid"))
            )
            time.sleep(4)

            # ── Scroll with backoff to load job cards ───────────────────────
            job_cards = []
            scroll_attempts = 0
            max_scrolls = 15

            while len(job_cards) < SCRAPE_BUFFER and scroll_attempts < max_scrolls:
                browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")

                # Randomised backoff between scrolls — avoids pattern detection
                backoff = random.uniform(SCROLL_BACKOFF_MIN, SCROLL_BACKOFF_MAX)
                logger.debug(f"HiringCafe: scroll {scroll_attempts + 1} — sleeping {backoff:.1f}s")
                time.sleep(backoff)

                job_cards = browser.find_elements(By.CSS_SELECTOR, "div.relative.bg-white")
                scroll_attempts += 1

            logger.info(f"HiringCafe: {len(job_cards)} cards loaded for role '{role}'")

            # ── Extract job data ─────────────────────────────────────────────
            raw_jobs = []
            for card in job_cards[:SCRAPE_BUFFER]:
                try:
                    title = card.find_element(
                        By.CSS_SELECTOR, "span.font-bold.text-start"
                    ).text.strip()

                    location = card.find_element(
                        By.CSS_SELECTOR, "div.mt-1.flex.items-center span.line-clamp-2"
                    ).text.strip()

                    bold_spans = card.find_elements(By.CSS_SELECTOR, "span.font-bold")
                    company = bold_spans[1].text.replace(":", "").strip() if len(bold_spans) > 1 else ""

                    apply_url = card.find_element(
                        By.XPATH, ".//a[contains(@href, 'viewjob')]"
                    ).get_attribute("href")

                    if title and apply_url:
                        raw_jobs.append({
                            "title": title,
                            "company": company,
                            "location": location,
                            "apply_url": apply_url,
                        })
                except Exception:
                    continue

            # ── Filter to jobs relevant to the searched role ─────────────────
            role_keywords = [word.lower() for word in role.split() if len(word) > 2]
            filtered = [
                job for job in raw_jobs
                if any(kw in job["title"].lower() for kw in role_keywords)
            ]

            # Fall back to unfiltered if filtering removes too much
            final_jobs = filtered if len(filtered) >= 5 else raw_jobs
            final_jobs = final_jobs[:limit]

            logger.info(
                f"HiringCafe: returning {len(final_jobs)} jobs for role '{role}' "
                f"({len(filtered)} matched out of {len(raw_jobs)} scraped)"
            )

            return [
                JobResult(
                    title=job["title"],
                    company=job["company"],
                    location=job["location"],
                    apply_url=job["apply_url"],
                )
                for job in final_jobs
            ]

        except Exception as e:
            logger.error(f"HiringCafe scraper error for role '{role}': {e}")
            return []

        finally:
            browser.quit()
