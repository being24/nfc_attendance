from app.domain.time_utils import now_jst
from app.repositories.unknown_card_repository import UnknownCardRepository


def test_unknown_card_repository(db_session):
    repo = UnknownCardRepository(db_session)
    repo.create("CARDX", "reader-1", now_jst())
    records = repo.list()
    assert len(records) == 1
    assert records[0].card_id == "CARDX"
