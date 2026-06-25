package com.istudy.controller;

import com.istudy.entity.HeadPoseData;
import com.istudy.repository.HeadPoseDataRepository;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/** /headpose — 데스크톱 앱 호환: 머리/시선 좌표 저장 (익명) */
@RestController
public class HeadPoseController {

    private final HeadPoseDataRepository repo;

    public HeadPoseController(HeadPoseDataRepository repo) {
        this.repo = repo;
    }

    public record HeadPoseCreate(String student_id, Double x, Double y) {}

    @PostMapping("/headpose")
    public Map<String, Object> save(@RequestBody HeadPoseCreate data) {
        HeadPoseData record = new HeadPoseData();
        record.setStudentId(data.student_id());
        record.setX(data.x());
        record.setY(data.y());
        repo.save(record);
        return Map.of("status", "ok");
    }
}
