from make_admin import promote_to_admin
from tests.conftest import make_user


def test_promotes_existing_user(client, session_factory):
    make_user(client, "Sam Student", "sam@buffs.wtamu.edu")
    with session_factory() as db:
        user = promote_to_admin(db, "sam@buffs.wtamu.edu")
        assert user is not None
        assert user.role == "admin"


def test_promoted_user_gets_admin_access(client, session_factory):
    headers = make_user(client, "Sam Student", "sam@buffs.wtamu.edu")
    assert client.get("/moderation/pending", headers=headers).status_code == 403
    with session_factory() as db:
        promote_to_admin(db, "sam@buffs.wtamu.edu")
    assert client.get("/moderation/pending", headers=headers).status_code == 200


def test_email_is_case_insensitive(client, session_factory):
    make_user(client, "Sam Student", "sam@buffs.wtamu.edu")
    with session_factory() as db:
        assert promote_to_admin(db, "  SAM@Buffs.WTAMU.edu ") is not None


def test_unknown_email_returns_none(session_factory):
    with session_factory() as db:
        assert promote_to_admin(db, "nobody@buffs.wtamu.edu") is None
