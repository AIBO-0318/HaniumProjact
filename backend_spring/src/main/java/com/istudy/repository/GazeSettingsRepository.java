package com.istudy.repository;

import com.istudy.entity.GazeSettings;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface GazeSettingsRepository extends JpaRepository<GazeSettings, Integer> {
    Optional<GazeSettings> findByUserId(Integer userId);
    Optional<GazeSettings> findFirstByCalibratedOrderByUpdatedAtDesc(Integer calibrated);
}
