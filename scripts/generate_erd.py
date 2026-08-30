"""Generate an ERD Editor (.erd.json) document from the SQLAlchemy metadata."""

from __future__ import annotations

import importlib
import json
import pkgutil
import sys
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Column,
    ColumnDefault,
    DefaultClause,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.schema import ForeignKeyConstraint

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import src.infra.db.models as models_pkg
from src.infra.db.models.base import Base

POSTGRES = postgresql.dialect()

ENTITY_META: dict[str, int] = {
    "updateAt": int(time.time() * 1000),
    "createAt": 0,
}

# column option bits (autoIncrement 1 | primaryKey 2 | unique 4 | notNull 8)
OPT_AUTO_INCREMENT = 1
OPT_PRIMARY_KEY = 2
OPT_UNIQUE = 4
OPT_NOT_NULL = 8

# column ui.keys bits (primaryKey 1 | foreignKey 2)
KEY_PRIMARY = 1
KEY_FOREIGN = 2

# relationshipType bits (ZeroOne 2 | ZeroN 4 | OneOnly 8 | OneN 16)
REL_ONE_N = 16
REL_ZERO_N = 4

# startRelationshipType bits (ring 1 | dash 2)
RING = 1

# direction bits (left 1 | right 2 | top 4 | bottom 8)
DIR_LEFT = 1
DIR_RIGHT = 2

# layout constants
COLS_PER_LAYER = 5
CELL_W, CELL_H = 420, 320

type JsonDict = dict[str, Any]
type Position = tuple[int, int]


def register_all_models() -> None:
    """Import every model module so all tables land on Base.metadata."""
    for mod in pkgutil.iter_modules(models_pkg.__path__):
        if not mod.name.startswith("_"):
            importlib.import_module(f"{models_pkg.__name__}.{mod.name}")


def render_datatype(column: Column[Any]) -> str:
    """Render a column's type for the PostgreSQL dialect."""
    try:
        return str(column.type.compile(dialect=POSTGRES))
    except Exception:
        return str(column.type)


def _render_default_arg(arg: Any) -> str:
    if isinstance(arg, str):
        return arg
    text = getattr(arg, "text", None)
    return text if isinstance(text, str) else str(arg)


def render_default(column: Column[Any]) -> str:
    """Render a column's default value as a string."""
    server_default = column.server_default
    if isinstance(server_default, DefaultClause):
        return _render_default_arg(server_default.arg)
    default = column.default
    if isinstance(default, ColumnDefault):
        return _render_default_arg(default.arg)
    return ""


def column_options(column: Column[Any]) -> int:
    """Compute the vuerd column option bits for a column."""
    options = 0
    if column.primary_key:
        options |= OPT_PRIMARY_KEY
    if column.unique:
        options |= OPT_UNIQUE
    if not column.nullable:
        options |= OPT_NOT_NULL
    if column.autoincrement not in (False, "auto") and not column.primary_key:
        options |= OPT_AUTO_INCREMENT
    return options


def referenced_table(fk: ForeignKeyConstraint) -> Table:
    """The table a foreign key points at."""
    return fk.elements[0].column.table


def compute_layers(tables: dict[str, Table]) -> dict[str, int]:
    """Place referenced tables on earlier layers than referencing ones."""
    parents: dict[str, set[str]] = defaultdict(set)
    for table in tables.values():
        for fk in table.foreign_key_constraints:
            parent = referenced_table(fk)
            if parent is not table:
                parents[table.name].add(parent.name)

    layers: dict[str, int] = {}
    seen: set[str] = set()
    current = [name for name in tables if not parents[name]]
    for name in current:
        layers[name] = 0
        seen.add(name)

    while current:
        nxt: list[str] = []
        for name in current:
            for other in sorted(tables):
                if other in seen:
                    continue
                if parents[other] <= seen:
                    layers[other] = layers[name] + 1
                    seen.add(other)
                    nxt.append(other)
        current = nxt

    base = max(layers.values(), default=-1) + 1
    for name in sorted(tables):
        if name not in layers:
            layers[name] = base
    return layers


def compute_layout(
    tables: dict[str, Table], layers: dict[str, int]
) -> dict[str, Position]:
    """Compute on-canvas coordinates for every table."""
    layout: dict[str, Position] = {}
    for layer in sorted(set(layers.values())):
        names = sorted(n for n in tables if layers[n] == layer)
        for pos, name in enumerate(names):
            x = (pos % COLS_PER_LAYER) * CELL_W
            y = layer * CELL_H + (pos // COLS_PER_LAYER) * CELL_H
            layout[name] = (x, y)
    return layout


def main() -> None:
    """Generate schema.erd.json from the SQLAlchemy metadata."""
    register_all_models()

    tables = dict(sorted(Base.metadata.tables.items()))
    layers = compute_layers(tables)
    layout = compute_layout(tables, layers)

    table_entities: dict[str, JsonDict] = {}
    column_entities: dict[str, JsonDict] = {}
    relationship_entities: dict[str, JsonDict] = {}
    index_entities: dict[str, JsonDict] = {}
    index_column_entities: dict[str, JsonDict] = {}

    table_ids: list[str] = []
    relationship_ids: list[str] = []
    index_ids: list[str] = []

    table_id_by_name: dict[str, str] = {}
    col_id_by_table: dict[str, dict[str, str]] = {}

    fk_columns: dict[str, set[str]] = {
        name: {
            c.name for fk in table.foreign_key_constraints for c in fk.columns
        }
        for name, table in tables.items()
    }

    for name, table in tables.items():
        table_id = str(uuid.uuid4())
        table_id_by_name[name] = table_id
        table_ids.append(table_id)

        column_ids: list[str] = []
        col_id_by_table[name] = {}
        for column in table.columns:
            col_id = str(uuid.uuid4())
            column_ids.append(col_id)
            col_id_by_table[name][column.name] = col_id

            keys = 0
            if column.primary_key:
                keys |= KEY_PRIMARY
            if column.name in fk_columns[name]:
                keys |= KEY_FOREIGN

            column_entities[col_id] = {
                "id": col_id,
                "tableId": table_id,
                "name": column.name,
                "comment": column.comment or "",
                "dataType": render_datatype(column),
                "default": render_default(column),
                "options": column_options(column),
                "ui": {
                    "keys": keys,
                    "widthName": 150,
                    "widthComment": 120,
                    "widthDataType": 130,
                    "widthDefault": 120,
                },
                "meta": ENTITY_META,
            }

        x, y = layout[name]
        table_entities[table_id] = {
            "id": table_id,
            "name": table.name,
            "comment": table.comment or "",
            "columnIds": column_ids,
            "seqColumnIds": list(column_ids),
            "ui": {
                "x": x,
                "y": y,
                "zIndex": 0,
                "widthName": 150,
                "widthComment": 120,
                "color": "",
            },
            "meta": ENTITY_META,
        }

        # relationships
        pk_names = {c.name for c in table.primary_key.columns}
        for fk in sorted(
            table.foreign_key_constraints,
            key=lambda f: f.name if isinstance(f.name, str) else "",
        ):
            parent_table = referenced_table(fk)
            parent_name = parent_table.name
            if parent_name not in table_id_by_name:
                continue

            child_ids = [col_id_by_table[name][c.name] for c in fk.columns]
            parent_ids = [
                col_id_by_table[parent_name][e.column.name]
                for e in fk.elements
            ]
            nullable = any(c.nullable for c in fk.columns)
            identifying = all(c.name in pk_names for c in fk.columns)

            child_x, child_y = layout[name]
            parent_x, parent_y = layout[parent_name]
            if parent_x >= child_x:
                start_dir, end_dir = DIR_RIGHT, DIR_LEFT
            else:
                start_dir, end_dir = DIR_LEFT, DIR_RIGHT

            rel_id = str(uuid.uuid4())
            relationship_ids.append(rel_id)
            relationship_entities[rel_id] = {
                "id": rel_id,
                "identification": identifying,
                "relationshipType": REL_ZERO_N if nullable else REL_ONE_N,
                "startRelationshipType": RING,
                "start": {
                    "tableId": table_id,
                    "columnIds": child_ids,
                    "x": child_x,
                    "y": child_y,
                    "direction": start_dir,
                },
                "end": {
                    "tableId": table_id_by_name[parent_name],
                    "columnIds": parent_ids,
                    "x": parent_x,
                    "y": parent_y,
                    "direction": end_dir,
                },
                "meta": ENTITY_META,
            }

        # indexes
        for idx in table.indexes:
            idx_id = str(uuid.uuid4())
            index_ids.append(idx_id)
            idx_col_ids = [col_id_by_table[name][c.name] for c in idx.columns]
            index_entities[idx_id] = {
                "id": idx_id,
                "name": idx.name or "",
                "tableId": table_id,
                "indexColumnIds": idx_col_ids,
                "seqIndexColumnIds": list(idx_col_ids),
                "unique": idx.unique,
                "meta": ENTITY_META,
            }
            for c in idx.columns:
                ic_id = str(uuid.uuid4())
                index_column_entities[ic_id] = {
                    "id": ic_id,
                    "indexId": idx_id,
                    "columnId": col_id_by_table[name][c.name],
                    "orderType": 1,
                    "meta": ENTITY_META,
                }

        # unique constraints rendered as unique indexes
        for constraint in table.constraints:
            if not isinstance(constraint, UniqueConstraint):
                continue
            cols = list(constraint.columns)
            idx_id = str(uuid.uuid4())
            index_ids.append(idx_id)
            idx_col_ids = [col_id_by_table[name][c.name] for c in cols]
            index_entities[idx_id] = {
                "id": idx_id,
                "name": constraint.name or "",
                "tableId": table_id,
                "indexColumnIds": idx_col_ids,
                "seqIndexColumnIds": list(idx_col_ids),
                "unique": True,
                "meta": ENTITY_META,
            }
            for c in cols:
                ic_id = str(uuid.uuid4())
                index_column_entities[ic_id] = {
                    "id": ic_id,
                    "indexId": idx_id,
                    "columnId": col_id_by_table[name][c.name],
                    "orderType": 1,
                    "meta": ENTITY_META,
                }

    doc: JsonDict = {
        "version": "3.0.0",
        "settings": {
            "width": 12000,
            "height": 12000,
            "scrollTop": 0,
            "scrollLeft": 0,
            "zoomLevel": 1,
            "show": 511,
            "database": 16,
            "databaseName": "Nightcore",
            "canvasType": "ERD",
            "language": 256,
            "tableNameCase": 1,
            "columnNameCase": 1,
            "bracketType": 1,
            "relationshipDataTypeSync": False,
            "relationshipOptimization": False,
            "columnOrder": [1, 2, 4, 8, 16, 32, 64],
            "maxWidthComment": 0,
            "ignoreSaveSettings": 1,
        },
        "doc": {
            "tableIds": table_ids,
            "relationshipIds": relationship_ids,
            "indexIds": index_ids,
            "memoIds": [],
        },
        "collections": {
            "tableEntities": table_entities,
            "tableColumnEntities": column_entities,
            "relationshipEntities": relationship_entities,
            "indexEntities": index_entities,
            "indexColumnEntities": index_column_entities,
            "memoEntities": {},
        },
    }

    out = Path(__file__).resolve().parents[1] / "schema.erd.json"
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    print(
        f"tables={len(table_entities)} "
        f"columns={len(column_entities)} "
        f"relationships={len(relationship_entities)} "
        f"indexes={len(index_entities)}"
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
