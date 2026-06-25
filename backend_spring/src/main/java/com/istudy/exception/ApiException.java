package com.istudy.exception;

import org.springframework.http.HttpStatus;

/** FastAPI 의 HTTPException(status_code, detail) 에 대응하는 예외. */
public class ApiException extends RuntimeException {
    private final HttpStatus status;

    public ApiException(HttpStatus status, String detail) {
        super(detail);
        this.status = status;
    }

    public HttpStatus getStatus() { return status; }

    public static ApiException badRequest(String detail)   { return new ApiException(HttpStatus.BAD_REQUEST, detail); }
    public static ApiException unauthorized(String detail) { return new ApiException(HttpStatus.UNAUTHORIZED, detail); }
    public static ApiException forbidden(String detail)    { return new ApiException(HttpStatus.FORBIDDEN, detail); }
    public static ApiException notFound(String detail)     { return new ApiException(HttpStatus.NOT_FOUND, detail); }
}
