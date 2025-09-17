# -*- coding: utf-8 -*-
# pydantic v2 系を想定
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


# -----------------------------
# CSV template (form_spec)
# -----------------------------
class CSVFormSpec(BaseModel):
    columns: List[str]
    rows: Optional[List[List[Any]]] = None
    description: Optional[str] = None
    delimiter: str = ","
    quotechar: str = '"'

    @field_validator("columns")
    @classmethod
    def _columns_not_empty(cls, v):
        if not v:
            raise ValueError("columns は1列以上必要です。")
        return v

    @field_validator("rows")
    @classmethod
    def _rows_match_columns(cls, rows, info):
        if rows is None:
            return rows
        cols = info.data.get("columns") or []
        for r in rows:
            if len(r) != len(cols):
                raise ValueError(f"初期行の列数が columns と一致しません: {r}")
        return rows


def parse_csv_form_spec(obj: Any) -> Dict[str, Any]:
    """dict/JSON文字列などを受け取り、正規化した dict を返す"""
    import json
    if obj is None:
        raise ValueError("form_spec が必要です。")
    if isinstance(obj, str):
        data = json.loads(obj)
    elif isinstance(obj, dict):
        data = obj
    else:
        raise ValueError("form_spec は dict か JSON 文字列で渡してください。")
    spec = CSVFormSpec.model_validate(data)
    return spec.model_dump()


# -----------------------------
# CSV update plan
#   - add_columns: 列追加
#   - append_rows: 行追記（headers/rows または objects）
#   - set_cells : セル更新
#   いずれか1つ以上があれば有効
# -----------------------------
class CSVAddColumn(BaseModel):
    name: str
    default: Optional[Any] = ""
    position: Optional[str] = Field(default="end", description="start/end")
    after: Optional[str] = None

    @field_validator("position")
    @classmethod
    def _pos_ok(cls, v):
        if v is None:
            return "end"
        if v not in ("start", "end"):
            raise ValueError("position は start か end です。")
        return v


class CSVAppendRowsByHeaders(BaseModel):
    headers: List[str]
    rows: List[List[Any]]

    @field_validator("headers")
    @classmethod
    def _headers_ok(cls, v):
        if not v:
            raise ValueError("headers は1つ以上必要です。")
        return v

    @field_validator("rows")
    @classmethod
    def _rows_ok(cls, v):
        if not v:
            raise ValueError("rows は1行以上必要です。")
        return v


class CSVAppendRowsByObjects(BaseModel):
    objects: List[Dict[str, Any]]

    @field_validator("objects")
    @classmethod
    def _objects_ok(cls, v):
        if not v:
            raise ValueError("objects は1件以上必要です。")
        return v


CSVAppendBatch = Union[CSVAppendRowsByHeaders, CSVAppendRowsByObjects]


class CSVSetCell(BaseModel):
    row_index: int  # 0始まり（ヘッダ除く）
    column: str
    value: Any


class CSVUpdatePlan(BaseModel):
    # 対象の特定
    filename: Optional[str] = None
    select_by_description: Optional[str] = None

    # 書式（任意）
    delimiter: str = ","
    quotechar: str = '"'

    # 操作
    add_columns: Optional[List[CSVAddColumn]] = None
    append_rows: Optional[List[CSVAppendBatch]] = None
    set_cells: Optional[List[CSVSetCell]] = None

    # 出力
    save_as: Optional[str] = None

    @model_validator(mode="after")
    def _at_least_one_operation(self):
        has_add = bool(self.add_columns)
        has_app = bool(self.append_rows)
        has_set = bool(self.set_cells)
        if not (has_add or has_app or has_set):
            raise ValueError("add_columns / append_rows / set_cells のいずれか1つ以上を指定してください。")
        return self


def _coerce_append_batch(obj: Any) -> CSVAppendBatch:
    """headers/rows または objects を含む dict を CSVAppendBatch に変換"""
    if not isinstance(obj, dict):
        raise ValueError("append_rows の各要素は dict である必要があります。")
    if "headers" in obj or "rows" in obj:
        return CSVAppendRowsByHeaders.model_validate(obj)
    if "objects" in obj:
        return CSVAppendRowsByObjects.model_validate(obj)
    raise ValueError("append_rows の要素は 'headers/rows' か 'objects' を含めてください。")


def parse_csv_update_plan(obj: Any) -> Dict[str, Any]:
    """dict/JSON文字列などを受け取り、厳密化した dict を返す（列追加のみ等も許可）"""
    import json
    if obj is None:
        raise ValueError("update_spec が必要です。")
    if isinstance(obj, str):
        data = json.loads(obj)
    elif isinstance(obj, dict):
        data = obj
    else:
        raise ValueError("update_spec は dict か JSON 文字列で渡してください。")

    # append_rows を Union モデルに正規化
    if "append_rows" in data and data["append_rows"] is not None:
        data["append_rows"] = [ _coerce_append_batch(x) for x in data["append_rows"] ]

    plan = CSVUpdatePlan.model_validate(data)
    return plan.model_dump()
