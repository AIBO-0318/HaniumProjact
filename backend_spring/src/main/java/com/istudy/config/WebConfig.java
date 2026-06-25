package com.istudy.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * 정적 웹(ui_ux/web) 서빙. FastAPI 의 StaticFiles 마운트와 동일한 경로 매핑.
 *   /static/pages → pages, /static/js → scripts, /static/css → styles, /static → web root
 */
@Configuration
public class WebConfig implements WebMvcConfigurer {

    private final String webRoot;

    public WebConfig(@Value("${app.web-root}") String webRoot) {
        this.webRoot = webRoot;
    }

    public static Path resolveWebRoot(String webRoot) {
        Path p = Paths.get(webRoot);
        if (!p.isAbsolute()) {
            p = Paths.get(System.getProperty("user.dir")).resolve(webRoot).normalize();
        }
        return p;
    }

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        Path root = resolveWebRoot(webRoot);
        String base = root.toUri().toString();          // file:/.../ui_ux/web/
        registry.addResourceHandler("/static/pages/**").addResourceLocations(base + "pages/");
        registry.addResourceHandler("/static/js/**").addResourceLocations(base + "scripts/");
        registry.addResourceHandler("/static/css/**").addResourceLocations(base + "styles/");
        registry.addResourceHandler("/static/**").addResourceLocations(base);
    }
}
