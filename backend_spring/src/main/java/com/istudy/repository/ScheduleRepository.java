package com.istudy.repository;

import com.istudy.entity.Schedule;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface ScheduleRepository extends JpaRepository<Schedule, Integer> {

    Optional<Schedule> findByIdAndUserId(Integer id, Integer userId);

    @Query("""
            SELECT s FROM Schedule s
            WHERE s.userId = :userId
              AND (:dateFrom IS NULL OR s.date >= :dateFrom)
              AND (:dateTo IS NULL OR s.date <= :dateTo)
            ORDER BY s.date ASC, s.startTime ASC
            """)
    List<Schedule> findInRange(@Param("userId") Integer userId,
                               @Param("dateFrom") String dateFrom,
                               @Param("dateTo") String dateTo);
}
