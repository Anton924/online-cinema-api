import pytest

# 1 movie - Inception have been created in test_06_comment_reply_notification in test_accounts_flow.py
# 2 movie - E2E Test Movie have been created in test_09_add_to_cart for test_purchase_flow.py

@pytest.mark.asyncdio
@pytest.mark.e2e
@pytest.mark.order(14)
async def test_02_list_all(e2e_client):
    response = await e2e_client.get(f"/api/v1/movies")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["total"] == 2, "Expected all three seeded movies."


@pytest.mark.asyncdio
@pytest.mark.e2e
@pytest.mark.order(15)
async def test_03_search_filter(e2e_client, e2e_db_session):
    response = await e2e_client.get(f"/api/v1/movies?search=Inception")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert len(response.json()["items"]) == 1 and response.json()["items"][0]["name"] == "Inception", "Search did not narrow to the expected movie."
