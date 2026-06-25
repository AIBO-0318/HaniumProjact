package com.istudy.controller;

import com.istudy.config.WebConfig;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

import java.nio.file.Path;

/**
 * HTML 페이지 라우팅. FastAPI 의 @app.get("/main") 등 FileResponse 매핑과 동일.
 * 실제 파일은 ui_ux/web/pages/ 아래에 있다.
 */
@Controller
public class WebPageController {

    private final Path pagesDir;

    public WebPageController(@Value("${app.web-root}") String webRoot) {
        this.pagesDir = WebConfig.resolveWebRoot(webRoot).resolve("pages");
    }

    private ResponseEntity<Resource> page(String fileName) {
        Path file = pagesDir.resolve(fileName);
        Resource res = new FileSystemResource(file);
        if (!res.exists()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        }
        return ResponseEntity.ok().contentType(MediaType.TEXT_HTML).body(res);
    }

    @GetMapping("/")                  public ResponseEntity<Resource> root()             { return page("index.html"); }
    @GetMapping("/index.html")        public ResponseEntity<Resource> index()            { return page("index.html"); }
    @GetMapping("/signup")            public ResponseEntity<Resource> signup()            { return page("signup.html"); }
    @GetMapping("/main")              public ResponseEntity<Resource> main()              { return page("main.html"); }
    @GetMapping("/calibration")       public ResponseEntity<Resource> calibration()       { return page("calibration.html"); }
    @GetMapping("/whitelist")         public ResponseEntity<Resource> whitelist()         { return page("whitelist.html"); }
    @GetMapping("/stats")             public ResponseEntity<Resource> stats()             { return page("stats.html"); }
    @GetMapping("/schedule")          public ResponseEntity<Resource> schedule()          { return page("schedule.html"); }
    @GetMapping("/mypage")            public ResponseEntity<Resource> mypage()            { return page("mypage.html"); }
    @GetMapping("/dashboard")         public ResponseEntity<Resource> dashboard()         { return page("dashboard.html"); }
    @GetMapping("/gaze-settings")     public ResponseEntity<Resource> gazeSettings()      { return page("gaze-settings.html"); }
    @GetMapping("/teacher-whitelist") public ResponseEntity<Resource> teacherWhitelist()  { return page("teacher-whitelist.html"); }
    @GetMapping("/auto-login")        public ResponseEntity<Resource> autoLogin()         { return page("auto-login.html"); }
    @GetMapping("/admin-users")       public ResponseEntity<Resource> adminUsers()        { return page("admin-users.html"); }
    @GetMapping("/admin-stats")       public ResponseEntity<Resource> adminStats()        { return page("admin-stats.html"); }
    @GetMapping("/focus-mode")        public ResponseEntity<Resource> focusMode()         { return page("focus-mode.html"); }
    @GetMapping("/teacher-schedule")  public ResponseEntity<Resource> teacherSchedule()   { return page("teacher-schedule.html"); }
}
