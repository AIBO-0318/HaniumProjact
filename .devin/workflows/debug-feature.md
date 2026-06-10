---
description: 기능 분석 및 로그 기반 디버깅 워크플로우 - 기능 요청 시 로그를 생성하고 오류를 분석/수정
---

# I-Study 기능 분석 및 로그 기반 디버깅 워크플로우

이 워크플로우는 사용자가 I-Study 시스템의 특정 기능에 대해 요청할 때 적용됩니다.
모든 기능 변경/추가/수정 시 아래 단계를 따릅니다.

---

## 1. 기능 식별 및 코드 위치 확인

- 요청된 기능이 어떤 모듈에 해당하는지 확인
  - **머리 방향 추적**: `core/head_pose_tracker.py` (HeadPoseTracker)
  - **URL 모니터링**: `core/monitor.py` (WhitelistMonitor)
  - **앱 차단**: `core/monitor.py` (AppMonitor)
  - **데이터베이스**: `core/database.py` (FocusDatabase)
  - **캘리브레이션**: `ui/dialogs/calibration.py` (CalibrationWindow)
  - **학습 통계**: `ui/pages/stats_page.py` (StatsPage)
  - **영상 제어**: `utils/helpers.py`
  - **팝업**: `ui/dialogs/popups.py`
  - **메인 앱 흐름**: `ui/app.py` (FocusEyePro)
  - **설정**: `config/settings.py`
- 관련 파일을 읽어 현재 상태 파악

## 2. 로그 추가/확인

### 2.1 기존 로거 확인
- `core/head_pose_tracker.py` → `logs/headpose.log` (head_pose_tracker 로거)
- `core/monitor.py` → `logs/monitor.log` (monitor 로거)
- 다른 모듈은 로거 미적용 상태

### 2.2 새 로거 추가 패턴
해당 모듈에 로거가 없으면 아래 패턴으로 추가:

```python
# 파일 상단에 추가
try:
    from utils.logger_config import get_logger, LoggerConfig
    logger = get_logger("모듈이름", "모듈이름.log")
except ImportError:
    import logging
    logger = logging.getLogger("모듈이름")
```

### 2.3 핵심 로그 포인트
기능 구현/수정 시 반드시 아래 포인트에 로그 추가:

```python
# 함수 진입
logger.info(f"함수명 called with param={param}")

# 상태 변화
LoggerConfig.log_state_change(logger, "컴포넌트", "이전상태", "새상태")

# 성능 메트릭
LoggerConfig.log_metric(logger, "메트릭명", 값, "단위")

# 에러 발생
LoggerConfig.log_error(logger, "함수명", exception)

# 중요 판정 로직
logger.debug(f"판정 근거: value={value}, threshold={threshold}, result={result}")
```

## 3. 기능 구현/수정

- 코드 변경 수행
- 변경 전후의 동작 차이를 로그로 기록할 수 있도록 구성
- 에러 핸들링에 반드시 로그 포함

## 4. 로그 기반 검증

### 4.1 로그 파일 확인
// turbo
```
Get-Content -Tail 50 d:\I-Study\logs\headpose.log
```

// turbo
```
Get-Content -Tail 50 d:\I-Study\logs\monitor.log
```

### 4.2 로그 분석 체크리스트
- [ ] 기능이 정상 호출되는지 (함수 진입 로그 확인)
- [ ] 상태 전환이 올바른지 (STATE CHANGE 로그 확인)
- [ ] 에러가 발생하지 않는지 (ERROR 로그 확인)
- [ ] 성능이 적절한지 (METRIC 로그 확인)
- [ ] 임계값/판정이 올바른지 (DEBUG 판정 로그 확인)

### 4.3 에러 발견 시
1. 로그에서 ERROR/WARNING 메시지 추출
2. traceback에서 에러 발생 위치 특정
3. 근본 원인(root cause) 분석
4. 최소 변경으로 수정 (upstream fix 우선)
5. 수정 후 로그로 재검증

## 5. 문서 업데이트

기능 변경이 있을 경우:
- `docs/FEATURES.md` 해당 섹션 업데이트
- 새 기능이면 `docs/ANALYSIS_DESIGN.md` 업데이트
- 설정 변경이면 `README.md` 업데이트

## 6. 로그 레벨 가이드

| 레벨 | 용도 | 예시 |
|------|------|------|
| DEBUG | 상세 디버깅 정보 | 임계값 비교, 중간 계산값 |
| INFO | 정상 동작 기록 | 시작/종료, 상태 변화, 메트릭 |
| WARNING | 비정상이나 계속 동작 | 카메라 백엔드 폴백, 빈 결과 |
| ERROR | 기능 실패 | 예외 발생, 리소스 접근 실패 |

---

## 참고: 로거 인스턴스 목록

| 로거 이름 | 로그 파일 | 모듈 | 상태 |
|-----------|-----------|------|------|
| head_pose_tracker | logs/headpose.log | core/head_pose_tracker.py | ✅ 적용됨 |
| monitor | logs/monitor.log | core/monitor.py | ✅ 적용됨 |
| app | logs/app.log | ui/app.py | ❌ 미적용 (추가 필요) |
| database | logs/database.log | core/database.py | ❌ 미적용 (추가 필요) |
| helpers | logs/helpers.log | utils/helpers.py | ❌ 미적용 (추가 필요) |
| calibration | logs/calibration.log | ui/dialogs/calibration.py | ❌ 미적용 (추가 필요) |
