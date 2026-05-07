#!/usr/bin/env python3
"""
I-Study - 얼굴 감지율 테스트 스크립트
얼굴 감지율을 실시간으로 측정합니다.
"""

import sys
import os
import time

# 프로젝트 루트를 경로에 추가 (tests/ 의 상위 폴더)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai_core.gaze_tracker import GazeTracker


def test_detection_rate(duration_seconds: int = 30):
    """
    감지율 테스트

    Args:
        duration_seconds: 테스트 지속 시간 (초)
    """
    print("=" * 60)
    print("I-Study 얼굴 감지율 테스트")
    print("=" * 60)
    print(f"테스트 시간: {duration_seconds}초")
    print("카메라를 켜고 얼굴을 카메라에 비춰주세요...")
    print("-" * 60)

    # GazeTracker 초기화
    tracker = GazeTracker()

    try:
        # 시선 추적 시작
        tracker.start(camera_index=0)
        print("카메라 시작됨")

        # 테스트 진행
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            time.sleep(1)

            # 현재 감지율 조회
            detection_rate = tracker.get_detection_rate()
            stats = tracker.get_detection_stats()

            elapsed = int(time.time() - start_time)
            print(f"[{elapsed:2d}s] 감지율: {detection_rate:5.1f}% | "
                  f"감지: {stats['detected_frames']:3d}/{stats['total_frames']:3d} 프레임")

        # 최종 통계
        print("-" * 60)
        final_stats = tracker.get_detection_stats()
        final_rate = tracker.get_detection_rate()

        print(f"\n최종 결과:")
        print(f"  총 프레임: {final_stats['total_frames']}")
        print(f"  감지된 프레임: {final_stats['detected_frames']}")
        print(f"  감지율: {final_rate:.1f}%")

        if final_rate >= 95:
            print(f"  등급: 매우 우수 (95% 이상)")
        elif final_rate >= 85:
            print(f"  등급: 우수 (85% 이상)")
        elif final_rate >= 75:
            print(f"  등급: 보통 (75% 이상)")
        elif final_rate >= 60:
            print(f"  등급: 미흡 (60% 이상)")
        else:
            print(f"  등급: 개선 필요 (60% 미만)")

        print("\n팁:")
        print("  - 밝은 환경에서 테스트하세요")
        print("  - 얼굴을 카메라 중앙에 오도록 하세요")
        print("  - 배경은 단조롭고 반사광이 적게 하세요")
        print("=" * 60)

    except Exception as e:
        print(f"오류: {e}")
    finally:
        # 정리
        tracker.stop()
        print("테스트 종료")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="I-Study 얼굴 감지율 테스트")
    parser.add_argument("--duration", type=int, default=30,
                       help="테스트 지속 시간 (초, 기본값: 30)")
    args = parser.parse_args()

    test_detection_rate(duration_seconds=args.duration)
