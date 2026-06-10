import re
import sqlglot
from sqlglot import expressions as exp
from app.config import settings

FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "COPY", "GRANT", "REVOKE", "CALL", "DO",
    "EXECUTE", "MERGE", "SET",
]


class SQLValidationError(Exception):
    pass


def _extract_tables(parsed: exp.Expression) -> list[str]:
    return [
        table.name.lower()
        for table in parsed.find_all(exp.Table)
        if table.name
    ]


def validate_sql(sql: str) -> str:
    if not sql or not sql.strip():
        raise SQLValidationError("La requête SQL ne peut pas être vide.")

    sql = sql.strip()

    # Strip trailing semicolon
    if sql.endswith(";"):
        sql = sql[:-1].rstrip()

    # Block multiple statements
    if ";" in sql:
        raise SQLValidationError("Les requêtes multiples (séparées par ;) sont interdites.")

    # Block SQL comments
    if "--" in sql or re.search(r"/\*.*?\*/", sql, re.DOTALL):
        raise SQLValidationError("Les commentaires SQL sont interdits.")

    # Block forbidden keywords (word-boundary match, case-insensitive)
    upper_sql = sql.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper_sql):
            raise SQLValidationError(f"Le mot-clé '{keyword}' est interdit.")

    # Parse with sqlglot in postgres dialect
    try:
        parsed = sqlglot.parse_one(sql, dialect="postgres")
    except Exception as e:
        raise SQLValidationError(f"Erreur de parsing SQL : {e}")

    # Must be a SELECT statement
    if not isinstance(parsed, exp.Select):
        raise SQLValidationError("Seules les requêtes SELECT sont autorisées.")

    # Check all referenced tables are in allowed views
    allowed = [v.lower() for v in settings.allowed_views_list]
    tables = _extract_tables(parsed)

    if not tables:
        raise SQLValidationError("Aucune table ou vue détectée dans la requête.")

    for table in tables:
        if table not in allowed:
            raise SQLValidationError(
                f"La table ou vue '{table}' n'est pas autorisée. "
                f"Vues autorisées : {', '.join(allowed)}"
            )

    # Add LIMIT if not present
    if parsed.find(exp.Limit) is None:
        parsed = parsed.limit(settings.default_limit)

    return parsed.sql(dialect="postgres")
