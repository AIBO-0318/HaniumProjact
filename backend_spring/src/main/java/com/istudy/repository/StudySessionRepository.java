package com.istudy.repository;

import com.istudy.entity.StudySession;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface StudySessionRepository extends JpaRepository<StudySession, Integer> {

    /** 날짜 범위의 세션 (대상 미지정 시 전체) */
    @Query("""
            SELECT s FROM StudySession s
            WHERE s.date >= :start AND s.date <= :end
              AND (:uid IS NULL OR s.userId = :uid OR s.loginId = :lid)
            """)
    List<StudySession> findInRange(@Param("start") String start,
                                   @Param("end") String end,
                                   @Param("uid") Integer uid,
                                   @Param("lid") String lid);

    /** 특정 날짜의 세션 */
    @Query("""
            SELECT s FROM StudySession s
            WHERE s.date = :date
              AND (:uid IS NULL OR s.userId = :uid OR s.loginId = :lid)
            """)
    List<StudySession> findByDate(@Param("date") String date,
                                  @Param("uid") Integer uid,
                                  @Param("lid") String lid);

    /** 본인 세션 최신순 */
    @Query("""
            SELECT s FROM StudySession s
            WHERE s.userId = :uid OR s.loginId = :lid
            ORDER BY s.createdAt DESC
            """)
    List<StudySession> findOwnRecent(@Param("uid") Integer uid,
                                     @Param("lid") String lid,
                                     org.springframework.data.domain.Pageable pageable);

    /** 오늘 누적 집중 시간(초) */
    @Query("""
            SELECT COALESCE(SUM(s.focusTimeSeconds), 0) FROM StudySession s
            WHERE s.date = :date AND (s.userId = :uid OR s.loginId = :lid)
            """)
    Long sumFocusTimeToday(@Param("date") String date,
                           @Param("uid") Integer uid,
                           @Param("lid") String lid);
}
