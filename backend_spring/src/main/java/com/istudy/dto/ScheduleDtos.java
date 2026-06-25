package com.istudy.dto;

import com.istudy.entity.Schedule;
import jakarta.validation.constraints.*;

import java.time.LocalDateTime;

public class ScheduleDtos {

    public record CreateRequest(
            @NotBlank @Pattern(regexp = "^\\d{4}-\\d{2}-\\d{2}$")
            String date,
            @Pattern(regexp = "^\\d{2}:\\d{2}$")
            String start_time,
            @Pattern(regexp = "^\\d{2}:\\d{2}$")
            String end_time,
            @NotBlank @Size(min = 1, max = 200)
            String title,
            String memo,
            String color
    ) {}

    public record UpdateRequest(
            @Min(0) @Max(1) Integer is_done
    ) {}

    public record Response(
            Integer id,
            String date,
            String start_time,
            String end_time,
            String title,
            String memo,
            String color,
            Integer is_done,
            LocalDateTime created_at
    ) {
        public static Response of(Schedule s) {
            return new Response(s.getId(), s.getDate(), s.getStartTime(), s.getEndTime(),
                    s.getTitle(), s.getMemo(), s.getColor(), s.getIsDone(), s.getCreatedAt());
        }
    }
}
