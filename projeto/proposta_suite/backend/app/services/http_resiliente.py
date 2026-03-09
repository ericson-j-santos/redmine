import time
from typing import Callable, Any
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class CircuitBreaker:
    def __init__(self, falhas_max: int = 3, janela_segundos: int = 60):
        self.falhas_max = falhas_max
        self.janela_segundos = janela_segundos
        self.falhas_consecutivas = 0
        self.ultimo_erro_ts = 0.0
        self.open_until = 0.0

    def pode_chamar(self) -> bool:
        agora = time.time()
        if agora < self.open_until:
            return False
        return True

    def registrar_sucesso(self):
        self.falhas_consecutivas = 0
        self.ultimo_erro_ts = 0.0
        self.open_until = 0.0

    def registrar_falha(self):
        agora = time.time()
        self.falhas_consecutivas += 1
        self.ultimo_erro_ts = agora
        if self.falhas_consecutivas >= self.falhas_max:
            self.open_until = agora + self.janela_segundos
            logger.warning("Circuit breaker OPEN")


cb_site_a = CircuitBreaker()
cb_sistema_b = CircuitBreaker()


async def chamar_com_retry(
    func: Callable[..., Any],
    *,
    max_tentativas: int = 3,
    backoff_base: float = 0.5,
    correlation_id: str,
    circuito: CircuitBreaker,
    descricao: str,
    **kwargs,
):
    if not circuito.pode_chamar():
        logger.error(
            f"Circuito OPEN para {descricao}, abortando chamada.",
            extra={"correlation_id": correlation_id},
        )
        raise RuntimeError(f"Serviço {descricao} indisponível (circuito aberto).")

    tentativas = 0
    while tentativas < max_tentativas:
        try:
            resultado = await func(**kwargs)
            circuito.registrar_sucesso()
            return resultado
        except Exception as e:
            tentativas += 1
            logger.error(
                f"Erro na chamada {descricao} (tentativa {tentativas}/{max_tentativas}): {e}",
                extra={"correlation_id": correlation_id},
            )
            circuito.registrar_falha()
            if tentativas >= max_tentativas:
                raise
            time.sleep(backoff_base * tentativas)

    raise RuntimeError(f"Falha ao chamar {descricao} após {max_tentativas} tentativas.")
