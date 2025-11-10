# database/quick_check.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, inspect
from database.config import settings

async def main():
    print("ASYNC DSN:", settings.async_dsn)
    eng = create_async_engine(settings.async_dsn)
    async with eng.begin() as conn:
        # Кто мы и куда подключены
        meta = await conn.exec_driver_sql(
            "select current_database(), current_user, current_schema"
        )
        print("DB/User/Schema:", meta.fetchone())

        # Все таблицы в public
        res = await conn.exec_driver_sql(
            "select table_name from information_schema.tables "
            "where table_schema='public' order by 1"
        )
        print("public tables:", [r[0] for r in res.fetchall()])

        # Есть ли users?
        res2 = await conn.exec_driver_sql(
            "select count(*) from information_schema.tables "
            "where table_schema='public' and table_name='users'"
        )
        print("users exists:", bool(res2.fetchone()[0]))

        # Какую ревизию видит БД?
        res3 = await conn.exec_driver_sql(
            "select table_name from information_schema.tables "
            "where table_schema='public' and table_name='alembic_version'"
        )
        has_alembic = bool(res3.fetchone())
        print("alembic_version exists:", has_alembic)
        if has_alembic:
            ver = await conn.exec_driver_sql("select version_num from alembic_version")
            print("alembic version:", [v[0] for v in ver.fetchall()])

    await eng.dispose()

if __name__ == "__main__":
    asyncio.run(main())
