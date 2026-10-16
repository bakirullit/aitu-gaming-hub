import csv
import io
import logging
from typing import Any
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.enums import StaffRole
from common.models.discipline import Discipline
from common.models.pending_staff import PendingStaffMember
from common.models.user import User
from services.user_service import UserService
from web.api.dependencies import get_current_admin, get_db_session, get_user_service

logger = logging.getLogger("web.api.staff")

staff_admin_router = APIRouter(prefix="/staff", tags=["Admin Staff"])


class PreCreateStaffRequest(BaseModel):
    first_name: str
    last_name: str
    academic_group: str | None = None
    barcode: str | None = None
    email: EmailStr | str | None = None
    corp_email: str | None = None
    phone_number: str | None = None
    username: str | None = None
    staff_role: StaffRole
    discipline_id: str | None = None


class PendingStaffResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    academic_group: str | None = None
    barcode: str | None = None
    email: str | None = None
    corp_email: str | None = None
    phone_number: str | None = None
    username: str | None = None
    staff_role: str
    discipline_id: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


ROLE_MAPPING: dict[str, StaffRole] = {
    "discipline_admin": StaffRole.DISCIPLINE_ADMIN,
    "дисциплинарный администратор": StaffRole.DISCIPLINE_ADMIN,
    "дисциплинарный админ": StaffRole.DISCIPLINE_ADMIN,
    "куратор": StaffRole.DISCIPLINE_ADMIN,
    "manager": StaffRole.MANAGER,
    "менеджер": StaffRole.MANAGER,
    "smm": StaffRole.SMM,
    "смм": StaffRole.SMM,
    "head_smm": StaffRole.HEAD_SMM,
    "дизайнер": StaffRole.DESIGNER,
    "designer": StaffRole.DESIGNER,
    "commentator": StaffRole.COMMENTATOR,
    "комментатор": StaffRole.COMMENTATOR,
    "кастер": StaffRole.COMMENTATOR,
    "streamer": StaffRole.STREAMER,
    "стример": StaffRole.STREAMER,
    "discord_admin": StaffRole.DISCORD_ADMIN,
    "дискорд админ": StaffRole.DISCORD_ADMIN,
    "head_admin": StaffRole.HEAD_ADMIN,
    "главный админ": StaffRole.HEAD_ADMIN,
    "none": StaffRole.NONE,
}


@staff_admin_router.get("/pending", response_model=list[PendingStaffResponse])
async def list_pending_staff(
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
) -> list[PendingStaffResponse]:
    """List all pending staff members waiting for registration."""
    stmt = select(PendingStaffMember).order_by(PendingStaffMember.created_at.desc())
    result = await session.execute(stmt)
    records = result.scalars().all()
    return [
        PendingStaffResponse(
            id=r.id,
            first_name=r.first_name,
            last_name=r.last_name,
            academic_group=r.academic_group,
            barcode=r.barcode,
            email=r.email,
            corp_email=r.corp_email,
            phone_number=r.phone_number,
            username=r.username,
            staff_role=r.staff_role.value if hasattr(r.staff_role, "value") else str(r.staff_role),
            discipline_id=r.discipline_id,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in records
    ]


@staff_admin_router.post("/pending", status_code=status.HTTP_201_CREATED)
async def pre_create_staff(
    data: PreCreateStaffRequest,
    user_service: UserService = Depends(get_user_service),
    admin: User = Depends(get_current_admin),
) -> dict[str, Any]:
    """Manually pre-creates a single staff member entry."""
    pending = await user_service.precreate_staff_member(
        first_name=data.first_name,
        last_name=data.last_name,
        staff_role=data.staff_role,
        academic_group=data.academic_group,
        barcode=data.barcode,
        email=str(data.email) if data.email else None,
        corp_email=data.corp_email,
        phone_number=data.phone_number,
        username=data.username,
        discipline_id=data.discipline_id,
    )
    return {
        "status": "success",
        "pending_id": pending.id,
        "first_name": pending.first_name,
        "last_name": pending.last_name,
        "staff_role": pending.staff_role.value if hasattr(pending.staff_role, "value") else str(pending.staff_role),
    }


@staff_admin_router.delete("/pending/{pending_id}", status_code=status.HTTP_200_OK)
async def delete_pending_staff(
    pending_id: int,
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
) -> dict[str, Any]:
    """Deletes a pending staff member record."""
    pending = await session.get(PendingStaffMember, pending_id)
    if not pending:
        raise HTTPException(status_code=404, detail="Pending staff member not found")
    await session.delete(pending)
    await session.commit()
    return {"status": "success", "deleted_id": pending_id}


class ImportStaffTextRequest(BaseModel):
    raw_text: str


async def parse_and_import_staff_records(
    content_text: str,
    session: AsyncSession,
    user_service: UserService,
) -> dict[str, Any]:
    content_text = content_text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not content_text:
        raise HTTPException(status_code=400, detail="Предоставленные данные пусты.")

    # Fetch available discipline slugs for resolution
    stmt_disc = select(Discipline.slug, Discipline.name)
    disc_res = await session.execute(stmt_disc)
    disciplines_map: dict[str, str] = {}
    for slug, name in disc_res.all():
        disciplines_map[slug.lower()] = slug
        disciplines_map[name.lower()] = slug

    lines = [l for l in content_text.split("\n") if l.strip()]
    if not lines:
        raise HTTPException(status_code=400, detail="Предоставленные данные пусты.")

    # Sniff delimiter from the first lines
    sample_lines = "\n".join(lines[:10])
    tab_count = sample_lines.count("\t")
    semi_count = sample_lines.count(";")
    comma_count = sample_lines.count(",")

    if tab_count > semi_count and tab_count > comma_count:
        delimiter = "\t"
    elif semi_count > comma_count:
        delimiter = ";"
    else:
        delimiter = ","

    # Parse rows using csv.reader with fallback to split
    rows: list[list[str]] = []
    try:
        reader = csv.reader(io.StringIO(content_text, newline=""), delimiter=delimiter)
        rows = [row for row in reader if row and any(cell.strip() for cell in row)]
    except Exception as exc:
        logger.warning(f"csv.reader failed ({exc}), falling back to string split")
        rows = [[c.strip() for c in line.split(delimiter)] for line in lines if line.strip()]

    if not rows:
        raise HTTPException(status_code=400, detail="Не удалось распознать строки данных.")

    header = [h.strip().lower() for h in rows[0]]
    field_indexes: dict[str, int] = {}

    for idx, col_name in enumerate(header):
        if col_name in ["имя", "first_name", "firstname", "name", "фио"] or col_name.startswith("имя") or col_name.startswith("first"):
            field_indexes.setdefault("first_name", idx)
        elif col_name in ["фамилия", "last_name", "lastname", "surname"] or col_name.startswith("фамил") or col_name.startswith("last"):
            field_indexes.setdefault("last_name", idx)
        elif col_name in ["группа", "group", "academic_group"] or col_name.startswith("груп"):
            field_indexes.setdefault("academic_group", idx)
        elif col_name in ["barcode", "баркод", "id_карт", "id_карта", "id"] or col_name.startswith("барк"):
            field_indexes.setdefault("barcode", idx)
        elif col_name in ["телефон", "phone", "тел", "phone_number"] or col_name.startswith("тел"):
            field_indexes.setdefault("phone_number", idx)
        elif col_name in ["почта", "email", "mail", "корп_почта"] or "@" in col_name:
            field_indexes.setdefault("email", idx)
        elif col_name in ["корп", "corp_email", "корпоративная почта"]:
            field_indexes.setdefault("corp_email", idx)
        elif col_name in ["никнейм", "username", "tag", "тег", "telegram", "тг", "user"]:
            field_indexes.setdefault("username", idx)
        elif col_name in ["роль", "role", "должность", "staff_role"]:
            field_indexes.setdefault("staff_role", idx)
        elif col_name in ["дисциплина", "discipline"]:
            field_indexes.setdefault("discipline", idx)

    if "first_name" not in field_indexes:
        # Fallback to positional columns if header missing
        field_indexes = {
            "first_name": 0,
            "last_name": 1,
            "academic_group": 2,
            "barcode": 3,
            "phone_number": 4,
            "email": 5,
            "username": 6,
            "staff_role": 7,
            "discipline": 8,
        }
        data_rows = rows
    else:
        data_rows = rows[1:]

    created_count = 0
    errors: list[str] = []

    for row_idx, row in enumerate(data_rows, start=1 if "first_name" not in field_indexes else 2):
        if not row or not any(row):
            continue

        def get_val(field: str) -> str | None:
            idx = field_indexes.get(field)
            if idx is not None and idx < len(row):
                val = row[idx].strip()
                return val if val else None
            return None

        first_name = get_val("first_name")
        last_name = get_val("last_name") or ""
        if not first_name:
            continue

        academic_group = get_val("academic_group")
        barcode = get_val("barcode")
        phone = get_val("phone_number")
        email = get_val("email")
        corp_email = get_val("corp_email")
        username = get_val("username")
        role_raw = get_val("staff_role") or "none"
        discipline_raw = get_val("discipline")

        # Map role
        norm_role = role_raw.lower().strip()
        matched_role = ROLE_MAPPING.get(norm_role, StaffRole.NONE)

        # Map discipline
        discipline_id: str | None = None
        if discipline_raw:
            d_key = discipline_raw.lower().strip()
            discipline_id = disciplines_map.get(d_key, d_key)

        # Check if email is corporate
        if email and ("@astanait.edu.kz" in email.lower() or "@aitu.edu.kz" in email.lower()) and not corp_email:
            corp_email = email

        try:
            await user_service.precreate_staff_member(
                first_name=first_name,
                last_name=last_name,
                staff_role=matched_role,
                academic_group=academic_group,
                barcode=barcode,
                email=email,
                corp_email=corp_email,
                phone_number=phone,
                username=username,
                discipline_id=discipline_id,
            )
            created_count += 1
        except Exception as exc:
            await session.rollback()
            detail = exc.detail if hasattr(exc, "detail") else str(exc)
            errors.append(f"Строка {row_idx} ({first_name} {last_name}): {detail}")

    return {
        "status": "success",
        "total_rows": len(data_rows),
        "created": created_count,
        "errors": errors[:50],
    }


@staff_admin_router.post("/pending/import-csv", status_code=status.HTTP_200_OK)
async def import_staff_csv(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
    admin: User = Depends(get_current_admin),
) -> dict[str, Any]:
    """
    Imports participants table from CSV or TSV file.
    Expected columns: Имя, Фамилия, Группа, Barcode, Телефон, Почта, Никнейм, Роль, Дисциплина
    """
    content_bytes = await file.read()
    try:
        content_text = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        content_text = content_bytes.decode("latin-1")

    return await parse_and_import_staff_records(content_text, session, user_service)


@staff_admin_router.post("/pending/import-text", status_code=status.HTTP_200_OK)
async def import_staff_text(
    payload: ImportStaffTextRequest,
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends(get_user_service),
    admin: User = Depends(get_current_admin),
) -> dict[str, Any]:
    """
    Imports participants table from raw copy-pasted text (TSV or CSV).
    """
    return await parse_and_import_staff_records(payload.raw_text, session, user_service)
