from __future__ import annotations

import ast
import re
from pathlib import Path

import models  # noqa: F401  # pyright: ignore[reportUnusedImport]

from models.base import Base

_ENABLE_RLS_PATTERN = re.compile(
    r"ALTER TABLE\s+([a-zA-Z0-9_]+)\s+ENABLE ROW LEVEL SECURITY",
    re.IGNORECASE,
)
_TENANT_POLICY_PATTERN = re.compile(
    r"CREATE POLICY\s+[a-zA-Z0-9_]+\s+ON\s+([a-zA-Z0-9_]+).*?current_setting\(\s*'app\.current_tenant_id'",
    re.IGNORECASE | re.DOTALL,
)


def _tenant_scoped_tables() -> set[str]:
    return {
        table.name
        for table in Base.metadata.tables.values()
        if table.name != "tenants" and "tenant_id" in table.c
    }


def _migration_texts() -> list[str]:
    versions_dir = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    return [path.read_text(encoding="utf-8") for path in versions_dir.glob("*.py")]


def _manifest_tables_with_helper_rls() -> set[str]:
    tables: set[str] = set()
    versions_dir = Path(__file__).resolve().parents[2] / "alembic" / "versions"

    for path in versions_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        manifest_values: dict[str, tuple[str, ...]] = {}
        helper_called = False

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and isinstance(node.value, (ast.Tuple, ast.List)):
                        values: list[str] = []
                        for element in node.value.elts:
                            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                                values.append(element.value)
                        if values:
                            manifest_values[target.id] = tuple(values)

            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "_enable_tenant_rls":
                    helper_called = True

        if helper_called and "_MULTI_TENANT_TABLES" in manifest_values:
            tables.update(manifest_values["_MULTI_TENANT_TABLES"])

    return tables


def _tables_with_enabled_rls() -> set[str]:
    tables = _manifest_tables_with_helper_rls()
    for text in _migration_texts():
        tables.update(match.group(1) for match in _ENABLE_RLS_PATTERN.finditer(text))
    return tables


def _tables_with_tenant_policy() -> set[str]:
    tables = _manifest_tables_with_helper_rls()
    for text in _migration_texts():
        tables.update(match.group(1) for match in _TENANT_POLICY_PATTERN.finditer(text))
    return tables


def test_all_multi_tenant_tables_have_rls_enabled_in_migrations() -> None:
    tenant_tables = _tenant_scoped_tables()
    missing_tables = sorted(tenant_tables - _tables_with_enabled_rls())
    assert missing_tables == [], (
        "As migrations precisam habilitar RLS para todas as tabelas com tenant_id. "
        f"Faltando: {missing_tables}"
    )


def test_all_multi_tenant_tables_have_tenant_policy_in_migrations() -> None:
    tenant_tables = _tenant_scoped_tables()
    missing_tables = sorted(tenant_tables - _tables_with_tenant_policy())
    assert missing_tables == [], (
        "As migrations precisam criar policy baseada em app.current_tenant_id para todas as "
        f"tabelas com tenant_id. Faltando: {missing_tables}"
    )