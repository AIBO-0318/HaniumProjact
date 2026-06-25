package com.istudy.repository;

import com.istudy.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface UserRepository extends JpaRepository<User, Integer> {
    Optional<User> findByLoginId(String loginId);
    boolean existsByLoginId(String loginId);

    // role 은 PostgreSQL enum(user_role). enum '=' 은 anyenum 다형성 연산자라
    // 바인딩 파라미터(character varying)와 직접 비교가 안 되고, 파생 쿼리(findBy...AndRole)는
    // cast 가 누락돼 "operator does not exist: user_role = character varying" 가 발생한다.
    // → role 비교는 네이티브 쿼리 + 명시적 CAST(:role AS user_role) 로 처리한다. (role 인자는 enum 이름 문자열)
    @Query(value = "SELECT * FROM users WHERE login_id = :loginId AND role = CAST(:role AS user_role)",
           nativeQuery = true)
    Optional<User> findByLoginIdAndRole(@Param("loginId") String loginId, @Param("role") String role);

    @Query(value = "SELECT * FROM users WHERE teacher_id = :teacherId AND role = CAST(:role AS user_role)",
           nativeQuery = true)
    List<User> findByTeacherIdAndRole(@Param("teacherId") Integer teacherId, @Param("role") String role);

    @Query(value = "SELECT count(*) FROM users WHERE role = CAST(:role AS user_role)",
           nativeQuery = true)
    long countByRole(@Param("role") String role);

    List<User> findAllByOrderByCreatedAtDesc();
    long countByIsActive(Integer isActive);
}
