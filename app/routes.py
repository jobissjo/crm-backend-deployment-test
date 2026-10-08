from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.auth import CurrentUser, Session
from app.models import Company, Contact, Deal, Task
from app.schemas import CompanyIn, CompanyOut, ContactIn, ContactOut, DealIn, DealOut, TaskIn, TaskOut

router = APIRouter()


async def owned(session, model, record_id, owner_id):
    record = await session.scalar(select(model).where(model.id == record_id, model.owner_id == owner_id))
    if record is None:
        raise HTTPException(404, "Record not found")
    return record


async def check_links(session, data, owner_id):
    for field, model in (("company_id", Company), ("contact_id", Contact), ("deal_id", Deal)):
        if data.get(field) is not None:
            # Lock references until commit so deletion cannot race this write.
            record = await session.scalar(select(model).where(model.id == data[field], model.owner_id == owner_id).with_for_update())
            if record is None:
                raise HTTPException(404, f"Related {field.removesuffix('_id')} not found")


async def commit(session):
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "Record conflicts with database constraints")


def resource_routes(path, model, input_schema, output_schema, search_field):
    resource = APIRouter(prefix=f"/{path}", tags=[path.title()])

    @resource.get("", response_model=list[output_schema])
    async def list_records(session: Session, user: CurrentUser, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), q: str | None = Query(None, max_length=200)):
        statement = select(model).where(model.owner_id == user.id)
        if q:
            statement = statement.where(getattr(model, search_field).icontains(q, autoescape=True))
        return (await session.scalars(statement.order_by(model.created_at.desc(), model.id).limit(limit).offset(offset))).all()

    # Explicit runtime schema annotation gives each route its own OpenAPI body.
    async def create_record(body, session: Session, user: CurrentUser):
        data = body.model_dump()
        await check_links(session, data, user.id)
        record = model(**data, owner_id=user.id)
        session.add(record)
        await commit(session)
        await session.refresh(record)
        return record

    create_record.__annotations__["body"] = input_schema
    resource.add_api_route("", create_record, methods=["POST"], response_model=output_schema, status_code=201)

    @resource.get("/{record_id}", response_model=output_schema)
    async def get_record(record_id: UUID, session: Session, user: CurrentUser):
        return await owned(session, model, record_id, user.id)

    async def replace_record(record_id: UUID, body, session: Session, user: CurrentUser):
        record = await owned(session, model, record_id, user.id)
        data = body.model_dump()
        await check_links(session, data, user.id)
        for key, value in data.items():
            setattr(record, key, value)
        await commit(session)
        await session.refresh(record)
        return record

    replace_record.__annotations__["body"] = input_schema
    resource.add_api_route("/{record_id}", replace_record, methods=["PUT"], response_model=output_schema)

    @resource.delete("/{record_id}", status_code=204)
    async def delete_record(record_id: UUID, session: Session, user: CurrentUser):
        record = await owned(session, model, record_id, user.id)
        await session.delete(record)
        await commit(session)
        return Response(status_code=204)

    return resource


for args in (("companies", Company, CompanyIn, CompanyOut, "name"), ("contacts", Contact, ContactIn, ContactOut, "name"), ("deals", Deal, DealIn, DealOut, "title"), ("tasks", Task, TaskIn, TaskOut, "title")):
    router.include_router(resource_routes(*args))


@router.get("/dashboard", tags=["Dashboard"])
async def dashboard(session: Session, user: CurrentUser):
    counts = {}
    for model in (Company, Contact, Deal, Task):
        counts[model.__tablename__] = await session.scalar(select(func.count()).select_from(model).where(model.owner_id == user.id))
    rows = (await session.execute(select(Deal.currency, Deal.stage, func.count(Deal.id), func.sum(Deal.value)).where(Deal.owner_id == user.id).group_by(Deal.currency, Deal.stage))).all()
    return {"counts": counts, "pipeline": [{"currency": currency, "stage": stage, "count": count, "value": str(value)} for currency, stage, count, value in rows]}
