import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.domain.time_utils import from_unix_seconds, to_unix_seconds
from app.models.attendance_event import AttendanceEvent
from app.models.student import Student

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/monthly.csv")
def export_monthly_csv(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
):
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    stmt = (
        select(AttendanceEvent, Student)
        .join(Student, Student.id == AttendanceEvent.student_id)
        .where(
            and_(
                AttendanceEvent.occurred_at >= to_unix_seconds(start),
                AttendanceEvent.occurred_at < to_unix_seconds(end),
            )
        )
        .order_by(AttendanceEvent.occurred_at)
    )
    rows = list(db.execute(stmt).all())

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["student_code", "name", "event_type", "occurred_at", "source", "reader_name"])
    for event, student in rows:
        writer.writerow(
            [
                student.student_code,
                student.name,
                event.event_type,
                from_unix_seconds(event.occurred_at).isoformat(),
                event.source,
                event.reader_name or "",
            ]
        )

    return Response(content=buffer.getvalue(), media_type="text/csv; charset=utf-8")
