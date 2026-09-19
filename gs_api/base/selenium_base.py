"""
Selenium 公共方法封装。

基于用户偏好的四层自动化架构，提供浏览器驱动、元素定位、
截图、窗口切换等通用 UI 操作基类，用于高升AI的 Web 端辅助测试。
"""

import os
import time
from pathlib import Path
from typing import Optional, Tuple

import allure
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .config import config, REPORT_DIR

SCREENSHOT_DIR = REPORT_DIR / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


class SeleniumBase:
    """Selenium 操作基类。"""

    def __init__(self, driver: Optional[WebDriver] = None):
        self.driver = driver or self._create_driver()
        self._wait = WebDriverWait(self.driver, config.get("selenium.implicitly_wait", 10))

    # ------------------------------------------------------------------
    # Driver 管理
    # ------------------------------------------------------------------

    def _create_driver(self) -> WebDriver:
        browser = config.get("selenium.browser", "chrome").lower()
        headless = config.get("selenium.headless", True)
        window_size = config.get("selenium.window_size", "1920,1080")
        driver_path = config.get("selenium.driver_path", "")

        if browser == "chrome":
            opts = ChromeOptions()
            if headless:
                opts.add_argument("--headless=new")
            opts.add_argument(f"--window-size={window_size}")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--ignore-certificate-errors")
            opts.add_experimental_option("excludeSwitches", ["enable-logging"])

            service = ChromeService(executable_path=driver_path) if driver_path else ChromeService()
            driver = webdriver.Chrome(service=service, options=opts)
        else:
            raise ValueError(f"暂不支持浏览器类型: {browser}")

        driver.set_page_load_timeout(config.get("selenium.page_load_timeout", 30))
        return driver

    def quit(self) -> None:
        if self.driver:
            self.driver.quit()

    def close(self) -> None:
        if self.driver:
            self.driver.close()

    # ------------------------------------------------------------------
    # 导航
    # ------------------------------------------------------------------

    def open(self, url: str) -> None:
        with allure.step(f"打开页面: {url}"):
            self.driver.get(url)

    def refresh(self) -> None:
        self.driver.refresh()

    def back(self) -> None:
        self.driver.back()

    def forward(self) -> None:
        self.driver.forward()

    @property
    def current_url(self) -> str:
        return self.driver.current_url

    @property
    def title(self) -> str:
        return self.driver.title

    # ------------------------------------------------------------------
    # 元素定位
    # ------------------------------------------------------------------

    def _locator(self, by: str, value: str) -> Tuple[str, str]:
        by_map = {
            "id": By.ID,
            "name": By.NAME,
            "class": By.CLASS_NAME,
            "css": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "link": By.LINK_TEXT,
            "plink": By.PARTIAL_LINK_TEXT,
            "tag": By.TAG_NAME,
        }
        return (by_map.get(by.lower(), By.XPATH), value)

    def find_element(self, by: str, value: str) -> WebElement:
        return self.driver.find_element(*self._locator(by, value))

    def find_elements(self, by: str, value: str) -> list[WebElement]:
        return self.driver.find_elements(*self._locator(by, value))

    def wait_visible(self, by: str, value: str, timeout: Optional[int] = None) -> WebElement:
        wait = WebDriverWait(self.driver, timeout or 10)
        return wait.until(EC.visibility_of_element_located(self._locator(by, value)))

    def wait_clickable(self, by: str, value: str, timeout: Optional[int] = None) -> WebElement:
        wait = WebDriverWait(self.driver, timeout or 10)
        return wait.until(EC.element_to_be_clickable(self._locator(by, value)))

    def wait_present(self, by: str, value: str, timeout: Optional[int] = None) -> WebElement:
        wait = WebDriverWait(self.driver, timeout or 10)
        return wait.until(EC.presence_of_element_located(self._locator(by, value)))

    def is_element_present(self, by: str, value: str) -> bool:
        try:
            self.find_element(by, value)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # 元素操作
    # ------------------------------------------------------------------

    def click(self, by: str, value: str) -> None:
        with allure.step(f"点击元素: {by}={value}"):
            el = self.wait_clickable(by, value)
            el.click()

    def type(self, by: str, value: str, text: str, clear_first: bool = True) -> None:
        with allure.step(f"输入文本: {by}={value} -> {text[:30]}..."):
            el = self.wait_visible(by, value)
            if clear_first:
                el.clear()
            el.send_keys(text)

    def get_text(self, by: str, value: str) -> str:
        return self.wait_visible(by, value).text

    def get_attribute(self, by: str, value: str, name: str) -> str:
        return self.find_element(by, value).get_attribute(name)

    def select_by_text(self, by: str, value: str, text: str) -> None:
        from selenium.webdriver.support.ui import Select
        el = self.wait_visible(by, value)
        Select(el).select_by_visible_text(text)

    def select_by_value(self, by: str, value: str, val: str) -> None:
        from selenium.webdriver.support.ui import Select
        el = self.wait_visible(by, value)
        Select(el).select_by_value(val)

    # ------------------------------------------------------------------
    # 截图与等待
    # ------------------------------------------------------------------

    def screenshot(self, name: Optional[str] = None) -> str:
        fname = name or f"screenshot_{int(time.time() * 1000)}.png"
        fpath = SCREENSHOT_DIR / fname
        self.driver.save_screenshot(str(fpath))
        allure.attach.file(
            str(fpath),
            name=fname,
            attachment_type=allure.attachment_type.PNG,
        )
        return str(fpath)

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    # ------------------------------------------------------------------
    # 窗口 / iframe
    # ------------------------------------------------------------------

    def switch_window(self, index: int = 0) -> None:
        self.driver.switch_to.window(self.driver.window_handles[index])

    def switch_frame(self, by: str = "", value: str = "") -> None:
        if by and value:
            self.driver.switch_to.frame(self.find_element(by, value))
        else:
            self.driver.switch_to.default_content()

    def switch_alert(self, accept: bool = True) -> str:
        alert = self.driver.switch_to.alert
        text = alert.text
        if accept:
            alert.accept()
        else:
            alert.dismiss()
        return text

    # ------------------------------------------------------------------
    # JS 操作
    # ------------------------------------------------------------------

    def execute_script(self, script: str, *args) -> Any:
        return self.driver.execute_script(script, *args)

    def scroll_to_bottom(self) -> None:
        self.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def scroll_into_view(self, by: str, value: str) -> None:
        el = self.find_element(by, value)
        self.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
