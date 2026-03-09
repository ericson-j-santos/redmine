from fastapi import Header, HTTPException, status
from typing import List, Optional

ROLES_VALIDOS = {"analista", "gestor", "admin"}


def assert_role(
    papel_requerido: List[str],
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    if x_user_role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Papel do usuário não informado (X-User-Role).",
        )
    if x_user_role not in ROLES_VALIDOS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Papel inválido: {x_user_role}.",
        )
    if x_user_role not in papel_requerido:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acesso negado para o papel: {x_user_role}.",
        )
    return x_user_role
