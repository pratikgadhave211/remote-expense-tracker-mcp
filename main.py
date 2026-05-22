
from fastmcp import FastMCP
import os 
import sqlite3
import aiosqlite
import tempfile 
import asyncio
TEMP_PATH = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_PATH,"expense_db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__),"categories.json")
mcp = FastMCP("Expense Tracker")
def init():
  with sqlite3.connect(DB_PATH) as c:
     c.execute('''
        CREATE TABLE IF NOT EXISTS expenses(
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           date TEXT NOT NULL,
           amount REAL NOT NULL,
            Category TEXT NOT NULL,
            subcategory TEXT DEFAULT'',
            note TEXT DEFAULT ''
        )
               '''
     )
      
init()

@mcp.tool()
async def add_expense(date, amount, category, subcategory="", note=""):
    '''Add a new expense entry to the database.'''
    async with aiosqlite.connect(DB_PATH) as c:
        cur = await c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
            (date, amount, category, subcategory, note)
        )
        expense_id = cur.lastrowid
        await c.commit()
        return {"status": "ok", "id": expense_id}
    
@mcp.tool()
async def list_expenses(start_date, end_date):
    '''List expense entries within an inclusive date range.'''
    async   with aiosqlite.connect(DB_PATH) as c:
        cur = await c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )
        cols = [d[0]  for d in  cur.description]
        return [dict(zip(cols, r)) for r in await cur.fetchall()]

@mcp.tool()
async def summarize(start_date, end_date, category=None):
    '''Summarize expenses by category within an inclusive date range.'''
    async  with aiosqlite.connect(DB_PATH) as c:
        query = (
            """
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
            """
        )
        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " GROUP BY category ORDER BY category ASC"

        cur = await c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in await cur.fetchall()]
@mcp.tool()
async def update_expense(id, date=None, amount=None, category=None, subcategory=None, note=None):
    '''Update an existing expense entry by ID. Only provided fields will be updated.'''
    fields = []
    params = []

    if date is not None:
        fields.append("date = ?")
        params.append(date)
    if amount is not None:
        fields.append("amount = ?")
        params.append(amount)
    if category is not None:
        fields.append("category = ?")
        params.append(category)
    if subcategory is not None:
        fields.append("subcategory = ?")
        params.append(subcategory)
    if note is not None:
        fields.append("note = ?")
        params.append(note)

    if not fields:
        return {"status": "error", "message": "No fields provided to update."}

    params.append(id)
    query = f"UPDATE expenses SET {', '.join(fields)} WHERE id = ?"

    async with aiosqlite.connect(DB_PATH) as c:
        cur = await c.execute(query, params)
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No expense found with id {id}."}
        return {"status": "ok", "updated_id": id, "rows_affected": cur.rowcount}
@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    # Read fresh each time so you can edit the file without restarting
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    mcp.run(transport="http",host="0.0.0.0",port="8000")
