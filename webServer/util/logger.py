import logging

LOGGER_NAME = "employee_recognition"


def get_logger() -> logging.Logger:
    """應用程式共用的 logger，輸出到標準錯誤，與 uvicorn 的紀錄並列"""
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
