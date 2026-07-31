import asyncio
import os
from sqlalchemy import text
from app.database import async_session

async def get_db_info():
    try:
        async with async_session() as session:
            tables_res = await session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = [row[0] for row in tables_res.all()]
            
            for table in tables:
                print(f"Table: {table}")
                cols_res = await session.execute(text(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}'"))
                for col in cols_res.all():
                    print(f"  - {col[0]} ({col[1]})")
                count_res = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                print(f"  Rows: {count_res.scalar()}")
                print("")
    except Exception as e:
        print(f"Failed to connect to database: {e}")

asyncio.run(get_db_info())
