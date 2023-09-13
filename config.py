class Config:
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    # Rejects oversized uploads with 413 before the body is read into memory.
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    MAX_IMAGES_PER_KEYWORD = 10
