import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

security = HTTPBearer()


def get_current_crm_user(
    token: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Valida o token de sessão emitido pelo CRM (backend-fastapi).

    Só verifica assinatura e expiração via o JWT_SECRET compartilhado — não
    consulta a tabela de usuários do CRM, que fica em outro banco. Retorna o
    id do usuário (claim "sub") só para fins de log/auditoria.
    """
    try:
        payload = jwt.decode(
            token.credentials, settings.JWT_SECRET, algorithms=["HS256"]
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    return sub
