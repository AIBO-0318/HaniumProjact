package com.istudy.repository;

import com.istudy.entity.WhitelistUrl;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface WhitelistUrlRepository extends JpaRepository<WhitelistUrl, Integer> {

    long count();

    List<WhitelistUrl> findAllByOrderByCreatedAtDesc();

    List<WhitelistUrl> findByUserIdIsNullOrderByCreatedAtDesc();

    List<WhitelistUrl> findByUserIdOrderByCreatedAtDesc(Integer userId);

    // 중복 검사: 끝 '/' 만 다른 URL(https://a.com 과 https://a.com/)은 같은 URL 로 본다.
    // url 인자는 withoutTrailingSlash() 로 끝 '/' 를 뗀 값을 넘긴다.
    @Query("""
            SELECT CASE WHEN COUNT(w) > 0 THEN true ELSE false END FROM WhitelistUrl w
            WHERE w.userId = :userId AND (w.url = :url OR w.url = CONCAT(:url, '/'))
            """)
    boolean existsByUserIdAndUrl(@Param("userId") Integer userId, @Param("url") String url);

    @Query("""
            SELECT CASE WHEN COUNT(w) > 0 THEN true ELSE false END FROM WhitelistUrl w
            WHERE w.userId IS NULL AND (w.url = :url OR w.url = CONCAT(:url, '/'))
            """)
    boolean existsDefaultByUrl(@Param("url") String url);

    static String withoutTrailingSlash(String url) {
        String u = url.strip();
        while (u.endsWith("/")) u = u.substring(0, u.length() - 1);
        return u;
    }

    @Query("""
            SELECT w FROM WhitelistUrl w
            WHERE w.userId IS NULL OR w.userId = :userId
            ORDER BY w.createdAt DESC
            """)
    List<WhitelistUrl> findEffectiveForUser(@Param("userId") Integer userId);
}
