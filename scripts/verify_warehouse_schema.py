"""Create the Task 3.5 warehouse tables or verify an existing schema against DDL.

The apply mode refuses to run if any target warehouse table already exists. It
never drops, alters, or truncates tables. Use --verify-only for an existing DB.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import os
import re
import sys
from pathlib import Path

import pymysql
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DDL_PATH = ROOT / "sql" / "02_warehouse_schema.sql"
EXPECTED_TABLES = {
    "dim_date", "dim_neighbourhood", "dim_listing",
    "fact_listing_snapshot", "fact_calendar", "fact_review",
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def split_sql(script: str) -> list[str]:
    """Split the DDL on semicolons outside quoted strings and SQL comments."""
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


def normalize_type(value: str) -> str:
    value = re.sub(r"\s+", "", str(value)).upper()
    value = value.replace("BOOLEAN", "TINYINT(1)").replace("BOOL", "TINYINT(1)")
    return value


def normalize_default(value) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
        text = text[1:-1].replace("''", "'")
    if text.upper().startswith("CURRENT_TIMESTAMP"):
        return text.upper()
    return text


def normalize_check(expression: str) -> tuple:
    """Normalize MySQL's quoting and redundant grouping in the current DDL checks."""
    tokens = re.findall(r"`[^`]+`|\d+(?:\.\d+)?|[a-z_]\w*|\S", expression, re.I)

    def canonical(parts):
        while parts and parts[0] == "(" and parts[-1] == ")":
            depth = 0
            for index, token in enumerate(parts):
                depth += (token == "(") - (token == ")")
                if depth == 0:
                    break
            if index != len(parts) - 1:
                break
            parts = parts[1:-1]
        depth = 0
        for index, token in enumerate(parts):
            depth += (token == "(") - (token == ")")
            if depth == 0 and token.upper() == "OR":
                return ("OR", canonical(parts[:index]), canonical(parts[index + 1:]))
        return tuple(
            str(Decimal(token).normalize()) if re.fullmatch(r"\d+(?:\.\d+)?", token)
            else token.strip("`").lower()
            for token in parts
        )

    return canonical(tokens)


def verify_checks(table, expected, rows):
    actual = {name: normalize_check(clause) for name, clause, enforced in rows
              if str(enforced).upper() == "YES"}
    if actual != expected:
        fail(f"{table}: CHECK expressions differ or are not enforced; actual={actual}; DDL={expected}.")


def parse_expected(script: str) -> dict[str, dict]:
    table_pattern = re.compile(
        r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)\s*\((.*?)\)\s*"
        r"ENGINE\s*=\s*(\w+)\s+DEFAULT\s+CHARSET\s*=\s*(\w+)\s+"
        r"COLLATE\s*=\s*(\w+)\s+COMMENT\s*=\s*'((?:[^']|'')*)'",
        re.I | re.S,
    )
    column_pattern = re.compile(
        r"^`?(\w+)`?\s+([A-Z]+(?:\(\s*\d+\s*(?:,\s*\d+\s*)?\))?(?:\s+UNSIGNED)?)\s+"
        r"(NOT\s+NULL|NULL)\b(.*)$", re.I,
    )
    expected: dict[str, dict] = {}
    for match in table_pattern.finditer(script):
        table, body, engine, charset, collation, comment = match.groups()
        columns, indexes, foreign_keys, checks = [], {}, {}, {}
        for raw_line in body.splitlines():
            line = raw_line.strip().rstrip(",")
            if not line:
                continue
            primary = re.match(r"CONSTRAINT\s+(\w+)\s+PRIMARY\s+KEY\s*\(([^)]+)\)", line, re.I)
            unique = re.match(r"CONSTRAINT\s+(\w+)\s+UNIQUE\s*\(([^)]+)\)", line, re.I)
            index = re.match(r"INDEX\s+(\w+)\s*\(([^)]+)\)", line, re.I)
            fk = re.match(r"CONSTRAINT\s+(\w+)\s+FOREIGN\s+KEY\s*\(([^)]+)\)\s+REFERENCES\s+(\w+)\s*\(([^)]+)\)", line, re.I)
            check = re.match(r"CONSTRAINT\s+(\w+)\s+CHECK\s*\((.*)\)", line, re.I)
            if primary:
                indexes["PRIMARY"] = (True, tuple(x.strip().strip("`") for x in primary.group(2).split(",")))
            elif unique:
                indexes[unique.group(1)] = (True, tuple(x.strip().strip("`") for x in unique.group(2).split(",")))
            elif index:
                indexes[index.group(1)] = (False, tuple(x.strip().strip("`") for x in index.group(2).split(",")))
            elif fk:
                name, cols, ref_table, ref_cols = fk.groups()
                foreign_keys[name] = (tuple(x.strip().strip("`") for x in cols.split(",")), ref_table,
                                      tuple(x.strip().strip("`") for x in ref_cols.split(",")))
            elif check:
                checks[check.group(1)] = normalize_check(check.group(2))
            else:
                col = column_pattern.match(line)
                if not col:
                    fail(f"Cannot parse DDL line for {table}: {line}")
                name, dtype, nullable, attrs = col.groups()
                default = re.search(r"\bDEFAULT\s+(CURRENT_TIMESTAMP(?:\(\d+\))?|NULL|'(?:[^']|'')*'|[^\s,]+)", attrs, re.I)
                comment_match = re.search(r"\bCOMMENT\s+'((?:[^']|'')*)'", attrs, re.I)
                columns.append({
                    "name": name,
                    "type": normalize_type(dtype),
                    "nullable": "NO" if nullable.upper().startswith("NOT") else "YES",
                    "default": normalize_default(default.group(1)) if default else None,
                    "auto_increment": "auto_increment" in attrs.lower(),
                    "comment": comment_match.group(1).replace("''", "'") if comment_match else "",
                })
        expected[table] = {
            "columns": columns, "indexes": indexes, "foreign_keys": foreign_keys, "checks": checks,
            "engine": engine.upper(), "charset": charset.lower(), "collation": collation.lower(),
            "comment": comment.replace("''", "'"),
        }
    if set(expected) != EXPECTED_TABLES:
        fail(f"DDL must define exactly the six warehouse tables; found {sorted(expected)}")
    return expected


def verify_schema(connection, database: str, expected: dict[str, dict]) -> None:
    placeholders = ",".join(["%s"] * len(EXPECTED_TABLES))
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT TABLE_NAME, ENGINE, TABLE_COLLATION, TABLE_COMMENT FROM information_schema.TABLES "
            f"WHERE TABLE_SCHEMA=%s AND TABLE_NAME IN ({placeholders})",
            (database, *sorted(EXPECTED_TABLES)),
        )
        actual_tables = {row[0]: row[1:] for row in cursor.fetchall()}
    if set(actual_tables) != EXPECTED_TABLES:
        fail(f"Missing warehouse tables: {sorted(EXPECTED_TABLES - set(actual_tables))}")

    for table in sorted(EXPECTED_TABLES):
        spec = expected[table]
        engine, collation, comment = actual_tables[table]
        if (engine or "").upper() != spec["engine"] or (collation or "").lower() != spec["collation"]:
            fail(f"{table}: engine/collation differs from DDL (actual={engine}/{collation}).")
        if comment != spec["comment"]:
            fail(f"{table}: table comment differs from DDL.")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA, COLUMN_COMMENT "
                "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION",
                (database, table),
            )
            rows = cursor.fetchall()
        actual_columns = [{
            "name": r[0], "type": normalize_type(r[1]), "nullable": r[2],
            "default": normalize_default(r[3]), "auto_increment": "auto_increment" in r[4].lower(), "comment": r[5],
        } for r in rows]
        if len(actual_columns) != len(spec["columns"]):
            fail(f"{table}: column count actual={len(actual_columns)}, expected={len(spec['columns'])}.")
        for position, (actual, wanted) in enumerate(zip(actual_columns, spec["columns"]), 1):
            mismatch = [key for key in wanted if actual[key] != wanted[key]]
            if mismatch:
                fail(f"{table} column #{position} {wanted['name']}: mismatch {mismatch}; actual={actual}; DDL={wanted}.")

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY INDEX_NAME, SEQ_IN_INDEX", (database, table),
            )
            index_rows = cursor.fetchall()
        grouped: dict[str, list] = {}
        for name, non_unique, seq, column in index_rows:
            grouped.setdefault(name, []).append((seq, column, non_unique))
        actual_indexes = {name: (not bool(parts[0][2]), tuple(x[1] for x in sorted(parts)))
                          for name, parts in grouped.items()}
        if actual_indexes != spec["indexes"]:
            fail(f"{table}: indexes differ; actual={actual_indexes}; DDL={spec['indexes']}.")

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME, ORDINAL_POSITION "
                "FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s "
                "AND REFERENCED_TABLE_NAME IS NOT NULL ORDER BY CONSTRAINT_NAME, ORDINAL_POSITION", (database, table),
            )
            fk_rows = cursor.fetchall()
            cursor.execute(
                "SELECT tc.CONSTRAINT_NAME, cc.CHECK_CLAUSE, tc.ENFORCED FROM information_schema.TABLE_CONSTRAINTS tc "
                "JOIN information_schema.CHECK_CONSTRAINTS cc ON cc.CONSTRAINT_SCHEMA=tc.CONSTRAINT_SCHEMA "
                "AND cc.CONSTRAINT_NAME=tc.CONSTRAINT_NAME WHERE tc.TABLE_SCHEMA=%s AND tc.TABLE_NAME=%s "
                "AND tc.CONSTRAINT_TYPE='CHECK'", (database, table),
            )
            check_rows = cursor.fetchall()
        actual_fks: dict[str, tuple[tuple[str, ...], str, tuple[str, ...]]] = {}
        for name, col, ref_table, ref_col, _ in fk_rows:
            prior = actual_fks.get(name, ((), ref_table, ()))
            actual_fks[name] = (prior[0] + (col,), ref_table, prior[2] + (ref_col,))
        if actual_fks != spec["foreign_keys"]:
            fail(f"{table}: foreign keys differ; actual={actual_fks}; DDL={spec['foreign_keys']}.")
        verify_checks(table, spec["checks"], check_rows)
        print(f"[SCHEMA PASS] {table}: {len(actual_columns)} columns; exact types, nullability, defaults, PK/indexes, FKs, and enforced CHECK expressions")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", help="Override MYSQL_DATABASE for an isolated test schema.")
    parser.add_argument("--verify-only", action="store_true", help="Verify existing tables without executing DDL.")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    required = ("MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE")
    missing = [key for key in required if not os.getenv(key, "").strip()]
    if missing:
        fail("Missing environment variables: " + ", ".join(missing) + ". Copy .env.example to .env and fill local values.")
    database = (args.database or os.environ["MYSQL_DATABASE"]).strip()
    if not re.fullmatch(r"[A-Za-z0-9_]+", database):
        fail("Database name may contain only letters, digits, and underscores.")
    ddl = DDL_PATH.read_text(encoding="utf-8")
    expected = parse_expected(ddl)
    statements = split_sql(ddl)
    if len(statements) != len(EXPECTED_TABLES) or any(
        not re.match(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(dim_|fact_)", s, re.I) for s in statements
    ):
        fail("DDL must contain exactly six CREATE TABLE IF NOT EXISTS statements for dim_*/fact_* tables.")

    connection = None
    try:
        connection = pymysql.connect(
            host=os.environ["MYSQL_HOST"].strip(), port=int(os.environ["MYSQL_PORT"]),
            user=os.environ["MYSQL_USER"].strip(), password=os.environ["MYSQL_PASSWORD"],
            database=database, charset="utf8mb4", autocommit=True, connect_timeout=5,
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION(), DATABASE()")
            version, actual_database = cursor.fetchone()
            cursor.execute(
                "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME IN (" +
                ",".join(["%s"] * len(EXPECTED_TABLES)) + ")",
                (database, *sorted(EXPECTED_TABLES)),
            )
            existing = {row[0] for row in cursor.fetchall()}
        if actual_database != database:
            fail(f"Connected to {actual_database!r}, expected {database!r}.")
        print(f"[CONNECTION PASS] MySQL {version}; database={actual_database}")
        if args.verify_only:
            if existing != EXPECTED_TABLES:
                fail(f"--verify-only requires all six warehouse tables; found {sorted(existing)}.")
            print("[INFO] Verify-only mode; no DDL was executed.")
        else:
            if existing:
                fail(f"Refusing to apply DDL because target tables already exist: {sorted(existing)}. Use --verify-only.")
            for statement in statements:
                with connection.cursor() as cursor:
                    cursor.execute(statement)
                print(f"[DDL PASS] {statement.splitlines()[0].strip()}")
        verify_schema(connection, database, expected)
        print("[PASS] Warehouse DDL and full schema comparison succeeded.")
        return 0
    except Exception as exc:
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
