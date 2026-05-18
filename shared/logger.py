"""
로깅 설정 모듈
각 컴포넌트별 로거를 생성하고 관리합니다.
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


class LoggerConfig:
    """로깅 설정 및 로거 생성 클래스"""
    
    _initialized = False
    _loggers = {}
    
    @staticmethod
    def setup_logging(log_dir="logs"):
        """
        로깅 시스템 초기 설정
        
        Args:
            log_dir: 로그 파일 저장 디렉토리
        """
        if LoggerConfig._initialized:
            return
        
        # 로그 디렉토리 생성
        os.makedirs(log_dir, exist_ok=True)
        
        # 기본 로그 포맷
        log_format = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 상세 로그 포맷 (파일용)
        detailed_format = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        LoggerConfig._initialized = True
        LoggerConfig._log_format = log_format
        LoggerConfig._detailed_format = detailed_format
        LoggerConfig._log_dir = log_dir
    
    @staticmethod
    def get_logger(name, log_file=None, level=logging.INFO):
        """
        로거 생성 또는 반환
        
        Args:
            name: 로거 이름
            log_file: 로그 파일명 (None이면 로거 이름.log)
            level: 로깅 레벨
            
        Returns:
            logging.Logger 인스턴스
        """
        if not LoggerConfig._initialized:
            LoggerConfig.setup_logging()
        
        if name in LoggerConfig._loggers:
            return LoggerConfig._loggers[name]
        
        # 로거 생성
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = False
        
        # 기존 핸들러 제거
        logger.handlers.clear()
        
        # 콘솔 핸들러 추가
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(LoggerConfig._log_format)
        logger.addHandler(console_handler)
        
        # 파일 핸들러 추가
        if log_file is None:
            log_file = f"{name}.log"
        
        file_path = os.path.join(LoggerConfig._log_dir, log_file)
        
        # 로테이팅 파일 핸들러 (최대 5MB, 3개 백업)
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(LoggerConfig._detailed_format)
        logger.addHandler(file_handler)
        
        LoggerConfig._loggers[name] = logger
        
        logger.info(f"=== Logger '{name}' initialized ===")
        
        return logger
    
    @staticmethod
    def log_function_call(logger, func_name, **kwargs):
        """함수 호출 로그"""
        args_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        logger.debug(f"CALL: {func_name}({args_str})")
    
    @staticmethod
    def log_function_result(logger, func_name, result, elapsed_time=None):
        """함수 결과 로그"""
        time_str = f" (took {elapsed_time:.3f}s)" if elapsed_time else ""
        logger.debug(f"RESULT: {func_name} -> {result}{time_str}")
    
    @staticmethod
    def log_error(logger, func_name, error):
        """에러 로그"""
        logger.error(f"ERROR in {func_name}: {type(error).__name__}: {str(error)}", exc_info=True)
    
    @staticmethod
    def log_state_change(logger, component, old_state, new_state):
        """상태 변화 로그"""
        logger.info(f"STATE CHANGE: {component} [{old_state}] -> [{new_state}]")
    
    @staticmethod
    def log_metric(logger, metric_name, value, unit=""):
        """성능 메트릭 로그"""
        unit_str = f" {unit}" if unit else ""
        logger.info(f"METRIC: {metric_name} = {value}{unit_str}")


# 편의 함수들
def get_logger(name, log_file=None):
    """로거 가져오기"""
    return LoggerConfig.get_logger(name, log_file)


def log_call(logger):
    """함수 호출 데코레이터"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            func_name = func.__name__
            LoggerConfig.log_function_call(logger, func_name, **kwargs)
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                LoggerConfig.log_function_result(logger, func_name, result, elapsed)
                return result
            except Exception as e:
                LoggerConfig.log_error(logger, func_name, e)
                raise
        return wrapper
    return decorator
