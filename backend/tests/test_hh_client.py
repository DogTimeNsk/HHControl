from unittest.mock import AsyncMock, Mock

import pytest

from app.core.config import Settings
from app.services.hh_client import HHClient, HHError


@pytest.mark.asyncio
async def test_ensure_applicant_rejects_employer_token() -> None:
    client = HHClient(Settings())
    response = Mock()
    response.json.return_value = {"is_applicant": False, "is_employer": True}
    client._request = AsyncMock(return_value=response)  # type: ignore[method-assign]

    with pytest.raises(HHError, match="не имеет роли соискателя"):
        await client.ensure_applicant()


@pytest.mark.asyncio
async def test_my_resumes_uses_url_provided_by_hh_profile() -> None:
    profile_response, resumes_response = Mock(), Mock()
    profile_response.json.return_value = {"is_applicant": True, "resumes_url": "https://api.hh.ru/resumes/mine"}
    resumes_response.json.return_value = {"items": [{"id": "resume-1"}]}
    client = HHClient(Settings())
    client._request = AsyncMock(side_effect=[profile_response, resumes_response])  # type: ignore[method-assign]

    assert await client.my_resumes() == [{"id": "resume-1"}]
    assert client._request.await_args_list[1].args == ("GET", "https://api.hh.ru/resumes/mine")
