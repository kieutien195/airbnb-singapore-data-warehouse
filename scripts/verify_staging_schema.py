"""Create-if-missing and verify the MySQL staging schema without deleting user data.

Schema DDL statements are intentionally outside a transaction (MySQL commits DDL).
The DML permission probe uses a transaction, identifies only rows it inserted by
raw_id, and rolls the transaction back even when a check fails.
"""
from __future__ import annotations

import os
import re
import sys
import uuid
from pathlib import Path

import pymysql
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DDL_PATH = ROOT / "sql" / "01_staging_schema.sql"
EXPECTED_TABLES = {
    "stg_neighbourhoods",
    "stg_calendar",
    "stg_reviews",
    "stg_listings",
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def split_sql_statements(script: str) -> list[str]:
    """Split this simple DDL file on semicolons outside quoted strings/comments."""
    statements: list[str] = []
    current: list[str] = []
    quote: str | None = None
    line_comment = False
    i = 0
    while i < len(script):
        char = script[i]
        nxt = script[i + 1] if i + 1 < len(script) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
                current.append(char)
            i += 1
            continue
        if quote:
            current.append(char)
            if char == "\\" and i + 1 < len(script):
                i += 1
                current.append(script[i])
            elif char == quote:
                if nxt == quote:
                    i += 1
                    current.append(script[i])
                else:
                    quote = None
            i += 1
            continue
        if char == "-" and nxt == "-":
            line_comment = True
            i += 2
            continue
        if char in ("'", '"', "`"):
            quote = char
            current.append(char)
        elif char == ";":
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(char)
        i += 1
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    if quote:
        fail("DDL contains an unclosed quoted string.")
    return statements


def parse_expected_ddl(script: str) -> dict[str, dict]:
    """Read columns, indexes, and table options directly from the reviewed DDL."""
    expected: dict[str, dict] = {}
    table_pattern = re.compile(
        r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)\s*\((.*?)\)\s*"
        r"ENGINE\s*=\s*(\w+)\s+DEFAULT\s+CHARSET\s*=\s*(\w+)\s+"
        r"COLLATE\s*=\s*(\w+)\s+COMMENT\s*=\s*'((?:[^']|'')*)'",
        re.IGNORECASE | re.DOTALL,
    )
    column_pattern = re.compile(
        r"^\s*(\w+)\s+"
        r"([A-Z]+(?:\(\s*\d+\s*(?:,\s*\d+\s*)?\))?(?:\s+UNSIGNED)?)\s+"
        r"(NOT\s+NULL|NULL)\b(.*?),?\s*$",
        re.IGNORECASE,
    )
    for match in table_pattern.finditer(script):
        table, body, engine, charset, collation, comment = match.groups()
        columns: list[dict] = []
        indexes: dict[str, tuple[bool, tuple[str, ...]]] = {}
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            primary = re.match(r"CONSTRAINT\s+\w+\s+PRIMARY\s+KEY\s*\(([^)]+)\)", line, re.I)
            index = re.match(r"(?:UNIQUE\s+)?INDEX\s+(\w+)\s*\(([^)]+)\)", line, re.I)
            if primary:
                indexes["PRIMARY"] = (True, tuple(x.strip().strip("`") for x in primary.group(1).split(",")))
                continue
            if index:
                unique = line.upper().startswith("UNIQUE")
                indexes[index.group(1)] = (unique, tuple(x.strip().strip("`") for x in index.group(2).split(",")))
                continue
            col = column_pattern.match(line)
            if not col:
                fail(f"Cannot parse DDL line for {table}: {line}")
            name, dtype, nullable, attrs = col.groups()
            default = re.search(r"\bDEFAULT\s+(CURRENT_TIMESTAMP(?:\(\d+\))?|NULL|'(?:[^']|'')*'|[^\s,]+)", attrs, re.I)
            comment_match = re.search(r"\bCOMMENT\s+'((?:[^']|'')*)'", attrs, re.I)
            columns.append({
                "name": name,
                "type": re.sub(r"\s+", " ", dtype.upper()).replace("( ", "(").replace(" )", ")"),
                "nullable": "NO" if nullable.upper().startswith("NOT") else "YES",
                "default": default.group(1) if default else None,
                "auto_increment": "auto_increment" in attrs.lower(),
                "comment": comment_match.group(1).replace("''", "'") if comment_match else "",
            })
        expected[table] = {
            "columns": columns,
            "indexes": indexes,
            "engine": engine.upper(),
            "charset": charset.lower(),
            "collation": collation.lower(),
            "comment": comment.replace("''", "'"),
        }
    if set(expected) != EXPECTED_TABLES:
        fail(f"DDL must define exactly the four expected staging tables; found {sorted(expected)}")
    return expected


def normalized_type(value: str) -> str:
    return re.sub(r"\s+", "", str(value)).upper()


def normalized_default(value) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
        text = text[1:-1].replace("''", "'")
    return text.upper() if text.upper().startswith("CURRENT_TIMESTAMP") else text


def execute_ddl(connection, statements: list[str]) -> None:
    for statement in statements:
        if not re.match(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+stg_", statement, re.I):
            fail("Refusing to execute a statement other than CREATE TABLE IF NOT EXISTS stg_*.")
        with connection.cursor() as cursor:
            cursor.execute(statement)
        print(f"[DDL OK] {statement.splitlines()[0].strip()}")


def verify_schema(connection, database: str, expected: dict[str, dict]) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT TABLE_NAME, ENGINE, TABLE_COLLATION, TABLE_COMMENT "
            "FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME IN (%s,%s,%s,%s)",
            (database, *sorted(EXPECTED_TABLES)),
        )
        actual_tables = {row[0]: row[1:] for row in cursor.fetchall()}
    if set(actual_tables) != EXPECTED_TABLES:
        fail(f"Missing staging tables in {database}: {sorted(EXPECTED_TABLES - set(actual_tables))}")

    for table in sorted(EXPECTED_TABLES):
        spec = expected[table]
        engine, table_collation, table_comment = actual_tables[table]
        if (engine or "").upper() != spec["engine"]:
            fail(f"{table}: actual ENGINE={engine!r}; DDL={spec['engine']!r}")
        if (table_collation or "").lower() != spec["collation"]:
            fail(f"{table}: actual COLLATION={table_collation!r}; DDL={spec['collation']!r}")
        if table_comment != spec["comment"]:
            fail(f"{table}: table comment differs from DDL.")

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA, "
                "ORDINAL_POSITION, COLUMN_COMMENT FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION",
                (database, table),
            )
            rows = cursor.fetchall()
        actual_columns = [
            {"name": r[0], "type": normalized_type(r[1]), "nullable": r[2],
             "default": normalized_default(r[3]), "auto_increment": "auto_increment" in r[4].lower(),
             "comment": r[6]}
            for r in rows
        ]
        if len(actual_columns) != len(spec["columns"]):
            fail(f"{table}: actual column count={len(actual_columns)}; DDL={len(spec['columns'])}.")
        for position, (actual, wanted) in enumerate(zip(actual_columns, spec["columns"]), 1):
            wanted_type = normalized_type(wanted["type"])
            actual_type = normalized_type(actual["type"])
            fields = ("name", "nullable", "default", "auto_increment", "comment")
            mismatch = [
                field for field in fields
                if actual[field] != (normalized_default(wanted[field]) if field == "default" else wanted[field])
            ]
            if actual_type != wanted_type:
                mismatch.append("type")
            if mismatch:
                fail(
                    f"{table} column #{position} {wanted['name']}: mismatch {mismatch}; "
                    f"actual={actual}; DDL={wanted}."
                )
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME "
                "FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s "
                "ORDER BY INDEX_NAME, SEQ_IN_INDEX",
                (database, table),
            )
            index_rows = cursor.fetchall()
        actual_indexes: dict[str, tuple[bool, tuple[str, ...]]] = {}
        grouped: dict[str, list] = {}
        for name, non_unique, seq, column in index_rows:
            grouped.setdefault(name, []).append((seq, column, non_unique))
        for name, parts in grouped.items():
            actual_indexes[name] = (not bool(parts[0][2]), tuple(x[1] for x in sorted(parts)))
        if actual_indexes != spec["indexes"]:
            fail(f"{table}: indexes differ; actual={actual_indexes}; DDL={spec['indexes']}")
        print(f"[SCHEMA PASS] {table}: {len(actual_columns)} columns; type, precision, scale, nullability, default, auto_increment, comments, and indexes match DDL")


def verify_dml_permissions(connection) -> None:
    """Exercise INSERT/SELECT/UPDATE/DELETE on just-created rows then roll back."""
    marker = "smoke-" + uuid.uuid4().hex
    probes = {
        "stg_neighbourhoods": ("INSERT INTO stg_neighbourhoods (neighbourhood_group, neighbourhood, source_file) VALUES (%s,%s,%s)", ("Smoke", "Smoke", marker)),
        "stg_calendar": ("INSERT INTO stg_calendar (available, source_file) VALUES (%s,%s)", ("t", marker)),
        "stg_reviews": ("INSERT INTO stg_reviews (reviewer_name, source_file) VALUES (%s,%s)", ("Smoke", marker)),
        "stg_listings": ("INSERT INTO stg_listings (name, source_file) VALUES (%s,%s)", ("Smoke", marker)),
    }
    inserted_ids: dict[str, int] = {}
    try:
        with connection.cursor() as cursor:
            for table, (insert_sql, values) in probes.items():
                cursor.execute(insert_sql, values)
                raw_id = cursor.lastrowid
                if cursor.rowcount != 1 or not raw_id:
                    fail(f"{table}: INSERT probe did not create exactly one row.")
                inserted_ids[table] = raw_id
                cursor.execute(f"SELECT raw_id, source_file FROM {table} WHERE raw_id=%s", (raw_id,))
                row = cursor.fetchone()
                if not row or row[0] != raw_id or row[1] != marker:
                    fail(f"{table}: SELECT did not find the inserted row by raw_id={raw_id}.")
                updated_marker = marker + "-updated"
                cursor.execute(f"UPDATE {table} SET source_file=%s WHERE raw_id=%s AND source_file=%s", (updated_marker, raw_id, marker))
                if cursor.rowcount != 1:
                    fail(f"{table}: UPDATE did not affect exactly raw_id={raw_id}.")
                cursor.execute(f"SELECT source_file FROM {table} WHERE raw_id=%s", (raw_id,))
                if cursor.fetchone()[0] != updated_marker:
                    fail(f"{table}: updated value did not read back correctly.")
                cursor.execute(f"DELETE FROM {table} WHERE raw_id=%s AND source_file=%s", (raw_id, updated_marker))
                if cursor.rowcount != 1:
                    fail(f"{table}: DELETE did not affect exactly raw_id={raw_id}.")
                cursor.execute(f"SELECT 1 FROM {table} WHERE raw_id=%s", (raw_id,))
                if cursor.fetchone() is not None:
                    fail(f"{table}: probe row remains after DELETE inside the transaction.")
                print(f"[DML PASS] {table}: INSERT/SELECT/UPDATE/DELETE targeted only raw_id={raw_id}; not committed")
    finally:
        connection.rollback()
    # The next reads run after ROLLBACK, so they cannot see the probe inserts.
    with connection.cursor() as cursor:
        for table, raw_id in inserted_ids.items():
            cursor.execute(f"SELECT 1 FROM {table} WHERE raw_id=%s", (raw_id,))
            if cursor.fetchone() is not None:
                fail(f"{table}: probe raw_id={raw_id} still exists after ROLLBACK.")
    print("[ROLLBACK PASS] Probe rows are absent after rollback; pre-existing rows were not targeted.")


def main() -> int:
    load_dotenv(ROOT / ".env")
    required = ("MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE")
    missing = [name for name in required if not os.getenv(name, "").strip()]
    if missing:
        fail("Missing environment variables: " + ", ".join(missing) + ". Copy .env.example to .env and fill the local values.")
    database = os.environ["MYSQL_DATABASE"].strip()
    if not re.fullmatch(r"[A-Za-z0-9_]+", database):
        fail("MYSQL_DATABASE may contain only letters, digits, and underscores.")
    ddl = DDL_PATH.read_text(encoding="utf-8")
    expected = parse_expected_ddl(ddl)
    statements = split_sql_statements(ddl)
    if len(statements) != len(EXPECTED_TABLES):
        fail(f"Expected {len(EXPECTED_TABLES)} CREATE TABLE statements; found {len(statements)}.")

    connection = None
    try:
        connection = pymysql.connect(
            host=os.environ["MYSQL_HOST"].strip(),
            port=int(os.environ["MYSQL_PORT"]),
            user=os.environ["MYSQL_USER"].strip(),
            password=os.environ["MYSQL_PASSWORD"],
            database=database,
            charset="utf8mb4",
            autocommit=False,
            connect_timeout=5,
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION(), DATABASE()")
            version, connected_database = cursor.fetchone()
        if connected_database != database:
            fail(f"Connected to {connected_database!r}, which differs from MYSQL_DATABASE={database!r}.")
        print(f"[CONNECTION PASS] MySQL {version}; database={connected_database}")
        print("[INFO] Only CREATE TABLE IF NOT EXISTS statements run; MySQL commits DDL automatically.")
        execute_ddl(connection, statements)
        verify_schema(connection, database, expected)
        verify_dml_permissions(connection)
        print("[PASS] DDL, complete schema/indexes, and DML permissions verified; probe rows rolled back.")
        return 0
    except Exception as exc:
        if connection:
            connection.rollback()
        print(f"[FAIL] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[FAIL] {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
