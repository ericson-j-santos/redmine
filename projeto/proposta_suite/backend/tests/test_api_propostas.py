import pytest
from httpx import AsyncClient
from app.main import app
from app.db.session import engine
from app.db.base import Base


@pytest.fixture(autouse=True, scope="module")
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_criar_proposta_e_obter_status(client: AsyncClient):
    payload = {
        "cpf": "12345678901",
        "nome_cliente": "Teste Usuário",
        "email": "teste@exemplo.com",
        "telefone": "11999999999",
        "valor_solicitado": 350000.0,
        "prazo_meses": 360,
        "tipo_imovel": "RESIDENCIAL",
        "tipo_operacao": "PORTABILIDADE",
        "canal_origem": "SITE",
        "aceite_lgpd": True,
    }

    resp = await client.post(
        "/api/propostas",
        json=payload,
        headers={"X-User-Role": "analista"},
    )
    assert resp.status_code == 201
    body = resp.json()
    id_proposta = body["id_proposta"]

    resp_status = await client.get(
        f"/api/propostas/{id_proposta}/status",
        headers={"X-User-Role": "analista"},
    )
    assert resp_status.status_code == 200
    status_body = resp_status.json()
    assert status_body["id_proposta"] == id_proposta
    assert "status" in status_body
