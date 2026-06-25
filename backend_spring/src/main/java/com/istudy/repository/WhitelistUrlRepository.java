package com.istudy.repository;

import com.istudy.entity.WhitelistUrl;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface WhitelistUrlRepository extends JpaRepository<WhitelistUrl, Integer> {

    long count();

    List<WhitelistUrl> findAllByOrderByCreatedAtDesc();

    List<WhitelistUrl> findByUserIdIsNullOrderByCreatedAtDesc();

    List<WhitelistUrl> findByUserIdOrderByCreatedAtDesc(Integer userId);

    Optional<WhitelistUrl> findByUserIdAndUrl(Integer userId, String url);

    @Query("SELECT w FROM WhitelistUrl w WHERE w.userId IS NULL AND w.url = :url")
    Optional<WhitelistUrl> findDefaultByUrl(@Param("url") String url);

    @Query("""
            SELECT w FROM WhitelistUrl w
            WHERE w.userId IS NULL OR w.userId = :userId
            ORDER BY w.createdAt DESC
            """)
    List<WhitelistUrl> findEffectiveForUser(@Param("userId") Integer userId);
}
