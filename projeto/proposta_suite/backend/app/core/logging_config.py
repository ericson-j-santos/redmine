import logging
import sys


def mascarar_cpf(cpf: str) -> str:
    if not cpf or len(cpf) != 11:
        return cpf
    return f"***{cpf[3:8]}**{cpf[-2:]}"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | cid=%(correlation_id)s | %(name)s | %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
