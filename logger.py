import logging
import sys


def get_logger(name: str = "agent", level: int = logging.INFO) -> logging.Logger:
    """获取彩色 Logger；若 colorlog 不可用则回退到标准 logging。"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    try:
        import colorlog

        formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
    except Exception:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


# 默认导出一个 logger
logger = get_logger()
