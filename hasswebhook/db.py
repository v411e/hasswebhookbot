from typing import Optional, Iterator, Dict, List
from datetime import datetime
import logging
import pytz
from attr import dataclass
from sqlalchemy import (Column, String, Integer, Text, DateTime, ForeignKey, Table, MetaData,
                        select, and_)
from sqlalchemy.engine.base import Engine

from mautrix.types import UserID, EventID, RoomID


@dataclass
class LifetimeEnd:
    id: int = None
    end_date: datetime = None
    room_id: RoomID = None
    event_id: EventID = None


class LifetimeDatabase:
    lifetime_ends: Table
    db: Engine

    def __init__(self, db: Engine) -> None:
        self.db = db

        meta = MetaData()
        meta.bind = db

        self.lifetime_ends = Table("lifetime_ends", meta,
                              Column("id", Integer, primary_key=True, autoincrement=True),
                              Column("end_date", DateTime, nullable=False),
                              Column("room_id", String(255), nullable=False),
                              Column("event_id", String(255), nullable=False))

        meta.create_all()

    def insert(self, lifetime_end: LifetimeEnd) -> None:
        logging.getLogger("maubot").info(f"Inserted event {lifetime_end.event_id} into database.")
        self.db.execute(self.lifetime_ends.insert()
                        .values(end_date=lifetime_end.end_date, room_id=lifetime_end.room_id,
                                event_id=lifetime_end.event_id))

    def get_older_than(self, end_date: datetime) -> Iterator[LifetimeEnd]:
        where = [self.lifetime_ends.c.end_date < end_date]
        rows = self.db.execute(select([self.lifetime_ends]).where(and_(*where)))
        for row in rows:
            yield LifetimeEnd(id=row[0], end_date=row[1].replace(tzinfo=pytz.UTC), room_id=row[2],
                               event_id=row[3])

    def remove(self, lifetime_end: LifetimeEnd) -> None:
        self.db.execute(self.lifetime_ends.delete().where(
            and_(self.lifetime_ends.c.event_id == lifetime_end.event_id)))
