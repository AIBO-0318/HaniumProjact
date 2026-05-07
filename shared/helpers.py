"""
유틸리티 헬퍼 함수 모듈
브라우저 제어, 색상 변환 등 공통 기능을 제공합니다.
"""

import ctypes
import ctypes.wintypes
import time
import pyautogui


def darken_color(hex_color: str, factor: float = 0.8) -> str:
    """
    HEX 색상을 어둡게 변환
    
    Args:
        hex_color: HEX 색상 코드 (예: "#FF6B6B")
        factor: 어둡게 할 비율 (0.0 ~ 1.0)
    
    Returns:
        어두워진 HEX 색상 코드
    """
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"#{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"


def find_browser_window():
    """
    브라우저 창 핸들(HWND) 찾기
    
    Returns:
        브라우저 창 핸들 또는 None
    """
    user32 = ctypes.windll.user32
    result = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    def enum_callback(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value.lower()
                keywords = [
                    'youtube', 'ebsi', 'ebs', 'mimacstudy', 'megastudy',
                    'etoos', 'chrome', 'edge', 'firefox', 'brave', 'whale'
                ]
                for kw in keywords:
                    if kw in title:
                        result.append(hwnd)
                        return False
        return True

    user32.EnumWindows(enum_callback, 0)
    return result[0] if result else None


def send_key_to_browser(key: str):
    """
    브라우저 창에 키 입력 전송
    
    Args:
        key: 전송할 키 이름 (예: 'space', 'left')
    """
    try:
        user32 = ctypes.windll.user32
        hwnd = find_browser_window()
        if hwnd:
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.3)
            pyautogui.press(key)
            time.sleep(0.1)
    except Exception:
        pass


def pause_video():
    """영상 일시정지 (Space 키)"""
    send_key_to_browser('space')


def play_video():
    """영상 재생 (Space 키)"""
    send_key_to_browser('space')


def rewind_10_seconds():
    """10초 되감기 (Left 키)"""
    send_key_to_browser('left')


def rewind_and_play():
    """되감기 후 재생"""
    rewind_10_seconds()
    time.sleep(0.1)
    play_video()


def format_time(seconds: int) -> str:
    """
    초를 HH:MM:SS 포맷으로 변환
    
    Args:
        seconds: 초
    
    Returns:
        "HH : MM : SS" 형식 문자열
    """
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d} : {m:02d} : {s:02d}"


def format_time_short(seconds: int) -> str:
    """
    초를 Xh Xm 포맷으로 변환
    
    Args:
        seconds: 초
    
    Returns:
        "Xh Xm" 형식 문자열
    """
    h, r = divmod(seconds, 3600)
    m, _ = divmod(r, 60)
    return f"{h}h {m}m"
