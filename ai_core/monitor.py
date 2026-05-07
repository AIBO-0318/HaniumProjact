"""
I-Study - App Monitor Module
차단 앱 모니터링 및 화이트리스트 URL 모니터링 모듈
"""

import threading
import time
from typing import Callable, List, Optional
import ctypes
from ctypes import wintypes

try:
    from shared.logger import get_logger, LoggerConfig
    logger = get_logger("monitor", "monitor.log")
except ImportError:
    import logging
    logger = logging.getLogger("monitor")


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class WhitelistMonitor:
    """화이트리스트 기반 브라우저 URL 모니터링 클래스"""
    
    BROWSER_KEYWORDS = ['chrome', 'edge', 'firefox', 'brave', 'whale', 'opera', '네이버 웨일']
    
    def __init__(
        self,
        whitelist_urls: List[dict] = None,
        on_blocked_site_detected: Optional[Callable[[str], None]] = None,
        check_interval: float = 1.5
    ):
        self.whitelist_urls = whitelist_urls or []
        self.on_blocked_site_detected = on_blocked_site_detected
        self.check_interval = check_interval
        
        self.is_running = False
        self.thread = None
        self._lock = threading.Lock()
        self._already_warned = False
        self._last_blocked_title = ""
    
    def update_whitelist(self, whitelist_urls: List[dict]):
        with self._lock:
            self.whitelist_urls = whitelist_urls.copy()
    
    def _get_active_window_title(self) -> str:
        try:
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buffer, length + 1)
                return buffer.value
        except Exception:
            pass
        return ""
    
    def _is_browser_window(self, title: str) -> bool:
        title_lower = title.lower()
        for kw in self.BROWSER_KEYWORDS:
            if kw in title_lower:
                return True
        return False
    
    SAFE_KEYWORDS = [
        '새 탭', 'new tab', '시작 페이지', 'start page',
        'about:blank', 'chrome://', 'edge://', 'whale://',
    ]

    SITE_TITLE_KEYWORDS = {
        'ebsi.co.kr': ['ebsi', 'ebs', '교육방송', '고교강의', 'ebs i'],
        'dict.naver.com': ['네이버 사전', '네이버사전', 'naver', '사전'],
        'mimacstudy.com': ['마이맥', '대성마이맥', '대성', 'mimacstudy'],
        'megastudy.net': ['메가스터디', '메가', 'megastudy', 'mega'],
        'etoos.com': ['이투스', 'etoos'],
        'chatgpt.com': ['chatgpt', 'chat gpt', 'openai'],
        'gemini.google.com': ['gemini', '제미나이', 'google ai'],
    }

    def _build_keywords(self):
        keywords = set()
        
        with self._lock:
            whitelist = self.whitelist_urls.copy()
        
        for site in whitelist:
            site_name = site.get("name", "").lower().strip()
            site_url = site.get("url", "").lower().strip()
            
            if site_name:
                keywords.add(site_name)
            
            for word in site_name.split():
                if len(word) >= 2:
                    keywords.add(word)
            
            no_space = site_name.replace(" ", "")
            if len(no_space) >= 2:
                keywords.add(no_space)
            
            domain = site_url.replace("https://", "").replace("http://", "").replace("www.", "")
            domain = domain.split("/")[0]
            
            skip = {'com', 'co', 'kr', 'net', 'org', 'www', 'asp'}
            for part in domain.split("."):
                if len(part) >= 3 and part not in skip:
                    keywords.add(part)
            
            for domain_key, title_kws in self.SITE_TITLE_KEYWORDS.items():
                if domain_key in site_url:
                    for kw in title_kws:
                        keywords.add(kw.lower())
        
        return keywords

    def _extract_url_from_title(self, title: str) -> str:
        """창 제목에서 URL 추출 (브라우저 창 제목 형식: '페이지제목 - 도메인 - 브라우저명')"""
        title_lower = title.lower()
        
        common_domains = [
            'youtube.com', 'naver.com', 'google.com', 'daum.net',
            'ebsi.co.kr', 'dict.naver.com', 'mimacstudy.com',
            'megastudy.net', 'etoos.com', 'chatgpt.com',
            'gemini.google.com', 'facebook.com', 'instagram.com',
            'twitter.com', 'tiktok.com', 'netflix.com'
        ]
        
        for domain in common_domains:
            if domain in title_lower:
                return domain
        
        return ""
    
    def _is_whitelisted(self, title: str) -> bool:
        title_lower = title.lower()
        
        for safe in self.SAFE_KEYWORDS:
            if safe in title_lower:
                logger.debug(f"Whitelisted by SAFE_KEYWORD: '{safe}'")
                return True
        
        if "i-study" in title_lower:
            logger.debug("Whitelisted by I-Study app")
            return True
        
        extracted_url = self._extract_url_from_title(title)
        if extracted_url:
            logger.debug(f"Extracted domain from title: '{extracted_url}'")
            
            with self._lock:
                whitelist = self.whitelist_urls.copy()
            
            for site in whitelist:
                site_url = site.get("url", "").lower()
                if extracted_url in site_url:
                    logger.debug(f"Whitelisted by domain match: '{extracted_url}' in '{site_url}'")
                    return True
        
        keywords = self._build_keywords()
        for kw in keywords:
            if len(kw) >= 4 and kw in title_lower:
                logger.debug(f"Whitelisted by keyword: '{kw}'")
                return True
        
        logger.debug(f"NOT whitelisted. Title: '{title_lower[:100]}'")
        return False
    
    def _minimize_window(self):
        try:
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                SW_MINIMIZE = 6
                user32.ShowWindow(hwnd, SW_MINIMIZE)
        except Exception:
            pass
    
    def _monitoring_loop(self):
        logger.info("WhitelistMonitor loop started with 8s grace period")
        time.sleep(8.0)
        logger.info("Grace period ended, monitoring active")
        last_warn_time = 0
        cooldown = 10
        
        while self.is_running:
            title = self._get_active_window_title()
            
            if title:
                is_browser = self._is_browser_window(title)
                logger.debug(f"Active window: '{title[:50]}...' | Browser: {is_browser}")
                
                if is_browser:
                    is_whitelisted = self._is_whitelisted(title)
                    logger.debug(f"Whitelist check: {is_whitelisted}")
                    
                    if not is_whitelisted:
                        logger.warning(f"Non-whitelisted site detected: '{title}'")
                        time.sleep(2.0)
                        if not self.is_running:
                            break
                        title2 = self._get_active_window_title()
                        
                        if (title2 and self._is_browser_window(title2)
                                and not self._is_whitelisted(title2)):
                            now = time.time()
                            if now - last_warn_time >= cooldown:
                                last_warn_time = now
                                logger.warning(f"BLOCKING site: '{title2}'")
                                self._minimize_window()
                                if self.on_blocked_site_detected:
                                    self.on_blocked_site_detected(title2)
                            else:
                                logger.debug(f"Blocked site '{title2}' in cooldown ({int(now - last_warn_time)}s/{cooldown}s)")
            
            time.sleep(self.check_interval)
    
    def start(self):
        logger.info(f"Starting WhitelistMonitor (whitelist size: {len(self.whitelist_urls)})")
        
        if self.is_running:
            logger.warning("WhitelistMonitor already running")
            return
        
        self.is_running = True
        self._already_warned = False
        self._last_blocked_title = ""
        
        self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.thread.start()
        
        LoggerConfig.log_state_change(logger, "WhitelistMonitor", "STOPPED", "RUNNING")
        logger.info("WhitelistMonitor started successfully")
    
    def stop(self):
        logger.info("Stopping WhitelistMonitor")
        
        self.is_running = False
        LoggerConfig.log_state_change(logger, "WhitelistMonitor", "RUNNING", "STOPPED")
        
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        
        logger.info("WhitelistMonitor stopped successfully")
