# -*- coding: utf-8 -*-
# pip install openai python-dotenv pydantic

import os
import re
import csv
import json
from typing import List, Dict, Optional, Any
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

from models_forms import (
    parse_csv_form_spec,
    parse_csv_update_plan,
)

load_dotenv()


# ------------------------------------------------------------
# 共通ユーティリティ
# ------------------------------------------------------------
def _ensure_outdir() -> Path:
    outdir = Path("./src/outputs")
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir

def _read_knowledge_csvs(knowledge_path: Path) -> List[Dict[str, str]]:
    """
    knowledge.txt から CSV テンプレ情報を抽出
    形式（例）:
      ### 【CSVテンプレ】ファイル名.csv
      保存先: ./src/outputs/避難者名簿.csv
      説明: 受付〜名簿の標準テンプレ
    """
    items = []
    if not knowledge_path.exists():
        return items
    text = knowledge_path.read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*###\s*", text)
    for b in blocks:
        if "【CSVテンプレ】" not in b:
            continue
        title_line = b.splitlines()[0] if b.splitlines() else ""
        m_title = re.search(r"【CSVテンプレ】(.+)", title_line)
        title = m_title.group(1).strip() if m_title else "(不明)"
        m_path = re.search(r"保存先:\s*(.+)", b)
        m_desc = re.search(r"説明:\s*(.+)", b)
        path = (m_path.group(1).strip() if m_path else "")
        desc = (m_desc.group(1).strip() if m_desc else "")
        if path and path.lower().endswith(".csv"):
            items.append({"title": title, "path": path, "description": desc})
    return items


# ------------------------------------------------------------
# CSV 作成（新規）
# ------------------------------------------------------------
def create_csv_file(
    *,
    filename: str = "data.csv",
    form_spec: Any = None,
    columns: Optional[List[str]] = None,
    rows: Optional[List[List[Any]]] = None,
    description: Optional[str] = None,
    delimiter: str = ",",
    quotechar: str = '"',
) -> str:
    """
    どちらでもOK:
      A) form_spec={"columns":[...], "rows":[...], "description":"...", "delimiter":",", "quotechar":"\""}
      B) columns=[...], rows=[...], description="...", delimiter=",", quotechar="\""
    """
    if form_spec is None:
        if not columns:
            raise ValueError("form_spec か columns のいずれかが必要です。")
        form_spec = {
            "columns": columns,
            "rows": rows or [],
            "description": description,
            "delimiter": delimiter,
            "quotechar": quotechar,
        }

    spec = parse_csv_form_spec(form_spec)  # バリデーション込み

    outdir = _ensure_outdir()
    path = outdir / filename

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=spec.get("delimiter", ","), quotechar=spec.get("quotechar", '"'))
        writer.writerow(spec["columns"])
        for row in spec.get("rows", []):
            if len(row) != len(spec["columns"]):
                raise ValueError(f"初期行の列数が columns と一致しません: {row}")
            writer.writerow(row)

    # knowledge に登録
    try:
        knowledge_path = Path("./src/functions/knowledge.txt")
        current = knowledge_path.read_text(encoding="utf-8") if knowledge_path.exists() else ""
        desc = spec.get("description") or "(説明なし)"
        new_entry = f"\n\n### 【CSVテンプレ】{filename}\n保存先: {str(path)}\n説明: {desc}"
        knowledge_path.write_text(current + new_entry, encoding="utf-8")
    except Exception:
        pass

    return str(path)


# ------------------------------------------------------------
# CSV 追記・列追加・セル更新：knowledge から対象選定 → 計画に基づき更新・保存
# ------------------------------------------------------------
def _read_csv_all(path: str, delimiter: str = ",", quotechar: str = '"') -> tuple[list[str], list[dict]]:
    rows: list[dict] = []
    header: list[str] = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=delimiter, quotechar=quotechar)
        header = reader.fieldnames or []
        for r in reader:
            rows.append(dict(r))
    return header, rows

def _write_csv_all(path: str, header: list[str], rows: list[dict], delimiter: str = ",", quotechar: str = '"'):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header, delimiter=delimiter, quotechar=quotechar)
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h, "") for h in header})

def _insert_col(header: list[str], name: str, *, position: Optional[str] = None, after: Optional[str] = None) -> list[str]:
    if after and after in header:
        i = header.index(after) + 1
        return header[:i] + [name] + header[i:]
    if position == "start":
        return [name] + header
    # default: end
    return header + [name]

def _append_rows_by_headers(header: list[str], rows: list[dict], batch_headers: list[str], values: list[list[Any]]):
    """headersを指定して列名マッピングで追記"""
    index = {h: i for i, h in enumerate(batch_headers)}
    for r in values:
        new = {h: "" for h in header}
        for h in header:
            if h in index and index[h] < len(r):
                new[h] = r[index[h]]
        rows.append(new)

def _append_rows_by_objects(header: list[str], rows: list[dict], objects: list[dict]):
    for obj in objects:
        # 未知カラムは末尾に追加
        for k in obj.keys():
            if k not in header:
                header.append(k)
                for rr in rows:
                    rr[k] = rr.get(k, "")
        new = {h: "" for h in header}
        for h in header:
            if h in obj:
                new[h] = obj[h]
        rows.append(new)

def _apply_update_plan_csv_full(path: str, plan: Dict[str, Any]) -> str:
    delimiter = plan.get("delimiter", ",")
    quotechar = plan.get("quotechar", '"')

    # 空ファイルは作らない前提（knowledge登録CSVを更新）。無ければエラー
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        raise FileNotFoundError(f"CSVが空か存在しません: {path}")

    header, rows = _read_csv_all(path, delimiter=delimiter, quotechar=quotechar)
    if not header:
        raise ValueError("CSVのヘッダ行が見つかりません。")

    # 1) 列追加
    for col in plan.get("add_columns", []) or []:
        name = col.get("name")
        if not name:
            continue
        if name in header:
            # 既存列には default だけ適用
            default = col.get("default", "")
            for r in rows:
                if r.get(name) in (None, ""):
                    r[name] = default
            continue
        header = _insert_col(header, name, position=col.get("position"), after=col.get("after"))
        default = col.get("default", "")
        for r in rows:
            r[name] = default

    # 2) 行追記
    for b in plan.get("append_rows", []) or []:
        headers_spec = b.get("headers")
        objects_spec = b.get("objects")
        values = b.get("rows", [])

        if headers_spec:
            # 未知カラムが headers に含まれるなら追加してからマッピング
            for h in headers_spec:
                if h not in header:
                    header.append(h)
                    for rr in rows:
                        rr[h] = rr.get(h, "")
            _append_rows_by_headers(header, rows, headers_spec, values)
        if objects_spec:
            _append_rows_by_objects(header, rows, objects_spec)

    # 3) セル更新（行インデックスはデータ行の0始まり。DictReader基準）
    for sc in plan.get("set_cells", []) or []:
        idx = sc.get("row_index")
        col = sc.get("column")
        val = sc.get("value")
        if idx is None or col is None:
            continue
        if col not in header:
            header.append(col)
            for r in rows:
                r[col] = r.get(col, "")
        if 0 <= idx < len(rows):
            rows[idx][col] = val

    # 保存
    _write_csv_all(path, header, rows, delimiter=delimiter, quotechar=quotechar)

    # save_as（別名保存）オプション
    save_as = plan.get("save_as")
    out_path = path if not save_as else save_as
    if save_as and save_as != path:
        data = Path(path).read_bytes()
        Path(save_as).parent.mkdir(parents=True, exist_ok=True)
        Path(save_as).write_bytes(data)
        out_path = save_as

    return out_path


def update_csv_from_knowledge(
    *,
    instruction: Optional[str] = None,
    update_spec: Optional[Any] = None
) -> str:
    """
    knowledge.txt を読み、対象CSVを選び、指示に基づいて更新（列追加/行追記/セル更新）を実行。
    - instruction: 自然文。LLMで更新計画(JSON)を合成（update_spec が無い場合のみ）
    - update_spec: 直接JSON計画を渡す場合（CSVUpdatePlan）
    返り値: 保存パス
    """
    knowledge_path = Path("./src/functions/knowledge.txt")
    items = _read_knowledge_csvs(knowledge_path)
    if not items:
        raise RuntimeError("knowledge.txt に CSV テンプレの記録がありません。")

    # 計画を決定
    if update_spec:
        plan = parse_csv_update_plan(update_spec)
    else:
        if not instruction:
            raise ValueError("instruction か update_spec のいずれかが必要です。")

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        sys_prompt = (
            "あなたはCSV更新プランナーです。与えられた候補一覧と指示から、"
            "どのファイルを更新し、どの操作（列追加/行追記/セル更新）を行うかを厳密なJSONで返してください。"
            "JSONスキーマ例:\n"
            "{\n"
            '  "filename": "<候補の path 文字列>",\n'
            '  "select_by_description": "<説明キーワード（省略可）>",\n'
            '  "add_columns": [\n'
            '     {"name":"担当者","default":"","position":"end","after":"在庫数"}\n'
            '  ],\n'
            '  "append_rows": [\n'
            '     {"headers":["品目","数量"], "rows":[["水",10]]},\n'
            '     {"objects":[{"品目":"毛布","数量":5,"担当者":"A"}]}\n'
            '  ],\n'
            '  "set_cells": [\n'
            '     {"row_index":0,"column":"数量","value":15}\n'
            '  ],\n'
            '  "delimiter": ",",\n'
            '  "quotechar": "\\""\n'
            "}\n"
            "注意: 候補以外のパスを出さないこと。headers を使う場合は既存CSVのカラム名に合わせること。"
        )
        summary = "\n".join(
            [f"- path: {it['path']}\n  title: {it['title']}\n  desc: {it['description']}" for it in items]
        )
        user_prompt = (
            "【候補一覧】\n" + summary + "\n\n"
            "【指示】\n" + instruction + "\n\n"
            "制約: 曖昧なら説明やタイトルで最も一致するものを選んでください。"
        )
        resp = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        try:
            plan = json.loads(resp.choices[0].message.content)
        except Exception:
            plan = parse_csv_update_plan(resp.choices[0].message.content)

    # 対象パスを resolve
    target_path = None
    if plan.get("filename"):
        target_path = plan["filename"]
    else:
        key = (plan.get("select_by_description") or "").strip()
        if key:
            matches = [it for it in items if key in (it["description"] or "") or key in (it["title"] or "")]
            if matches:
                target_path = matches[0]["path"]
    if not target_path:
        target_path = items[-1]["path"]

    # 計画のバリデーション（ゆるめに通しつつ、必須型は確認）
    plan_norm = parse_csv_update_plan(plan)

    # 実適用
    save_path = _apply_update_plan_csv_full(target_path, plan_norm)

    # knowledge にログ追記
    try:
        log = f"更新対象: {target_path}\n保存先: {save_path}\n計画: {json.dumps(plan_norm, ensure_ascii=False)}"
        current = knowledge_path.read_text(encoding="utf-8") if knowledge_path.exists() else ""
        new_entry = f"\n\n### 【CSV更新】{Path(save_path).name}\n{log}"
        (knowledge_path).write_text(current + new_entry, encoding="utf-8")
    except Exception:
        pass

    return save_path


# ------------------------------------------------------------
# RAG 検索：FAISSから上位5件、章・節・ページ＋本文抜粋を返し、knowledgeに追記
# ------------------------------------------------------------
def rag_read(query: str) -> str:
    """
    rag_db_maker.load_retriever を用い、config.constants の
    VECTOR_DB_PATH / HIRAKATA_JISIN_VECTOR を参照して検索。
    戻り値は整形済みテキスト（章・節・ページ＋抜粋）。
    """
    try:
        # パス解決と import
        import sys
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        from rag_db_maker import load_retriever
        from config.constants import VECTOR_DB_PATH, HIRAKATA_JISIN_VECTOR

        db_path = os.path.join(VECTOR_DB_PATH, HIRAKATA_JISIN_VECTOR)
        if not os.path.exists(db_path):
            return "ベクトルデータベースが見つかりません。先に rag_db_maker.py を実行して作成してください。"

        if not query.strip():
            query = "災害対応の基本情報"

        retriever, _ = load_retriever(db_path)
        results = retriever.invoke(query)

        blocks = []
        for i, doc in enumerate(results[:5], 1):  # 上位5件
            m = getattr(doc, "metadata", {}) or {}
            chapter = m.get('chapter') or ''
            section = m.get('section') or ''
            page_s = m.get('page_start', '?')
            page_e = m.get('page_end', '?')
            head = " / ".join([x for x in [chapter, section] if x]).strip()
            text = (doc.page_content or "").replace("\n", " ")
            snippet = text
            blocks.append(f"#{i} [{head}] p.{page_s}-{page_e}\n{snippet}")

        if not blocks:
            return f"該当なし: {query}"

        return f"Query: {query}\n\n" + "\n\n".join(blocks)

    except Exception as e:
        return f"ベクトル検索エラー: {str(e)}"


# ------------------------------------------------------------
# メイン：チャット（ツール：作成/検索/更新）
# ------------------------------------------------------------
class ChatWithMemory:
    def __init__(self):
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        self.client = OpenAI(api_key=api_key)
        self.conversation_history: List[Dict[str, str]] = []
        self.knowledge_path = Path("./src/functions/knowledge.txt")

        knowledge_content = self.knowledge()
        self.base_system_content = f"""
あなたはUSERと一緒に災害対応の仕事を行う枚方市の災害対応職員（人間）です。
地震を想定した避難訓練をUSERと二人で行っています。あなたは相手の話を聞き、求められたときだけ簡潔に返答します。

厳格なルール：
- 知らないことは推測せず「分かりません。調べましょうか？」と確認し、了承が得られた場合のみ `read_document` を使います。
- CSVテンプレ作成は、会話から `form_spec`（JSON：columns/rows）を設計するか、`columns/rows` を直接受け取り、`create_csv_file` を1回だけ呼びます。
- 追記依頼が来たら、`update_csv_from_knowledge` を1回だけ呼び、knowledge に保存されたCSVの中から適切なファイルを選び、計画に基づき更新を行います。
- 作成・更新・検索の結果は、knowledge にパスと説明/計画や検索ログを追記します。
- 自分から話題を広げない。質問されたことにだけ短く答える。
- 箇条書き禁止。音声会話を想定した自然な口調で。

## あなたが知っている知識（参考程度）
{knowledge_content}
"""

    def add_message(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})

    def clear_history(self):
        self.conversation_history = []

    def get_conversation_history(self) -> List[Dict[str, str]]:
        return self.conversation_history.copy()

    def knowledge(self) -> str:
        try:
            return self.knowledge_path.read_text(encoding='utf-8')
        except Exception as e:
            return f"(knowledge読み込みエラー: {e})"

    def add_to_knowledge(self, title: str, content: str):
        try:
            current_knowledge = self.knowledge()
            new_entry = f"\n\n### {title}\n{content}"
            updated_knowledge = current_knowledge + new_entry
            self.knowledge_path.write_text(updated_knowledge, encoding='utf-8')
            print(f"📝 知識ベースに追加しました: {title}")
        except Exception as e:
            print(f"知識ベース追加エラー: {e}")

    # --- RAG 検索（実装版） ---
    def read_document(self, query: str = "") -> str:
        result = rag_read(query)
        # knowledge に検索ログを追記
        try:
            self.add_to_knowledge(f"【検索】{query}", result)
        except Exception:
            pass
        return result

    def get_function_definitions(self, mode: str = "all") -> List[Dict]:
        defs = []

        # CSV作成
        defs.append({
            "type": "function",
            "function": {
                "name": "create_csv_file",
                "description": "form_spec(JSON: columns/rows) もしくは columns/rows を直接指定して CSV を生成し、保存パスを返す。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "保存ファイル名。日本語名可", "default": "data.csv"},
                        "form_spec": {"type": "object", "description": "CSVテンプレのスキーマ（columns/rows/description/delimiter/quotechar）"},
                        "columns": {"type": "array", "items": {"type": "string"}, "description": "ヘッダ行（form_spec の代替）"},
                        "rows": {"type": "array", "items": {"type": "array", "items": {}}, "description": "初期データ行（任意）"},
                        "description": {"type": "string", "description": "knowledge.txt 用の説明（任意）"},
                        "delimiter": {"type": "string", "description": "区切り文字（既定 ,）"},
                        "quotechar": {"type": "string", "description": "クォート文字（既定 \")"}
                    },
                    "required": []
                }
            }
        })

        # CSV更新（列追加/行追記/セル更新）
        defs.append({
            "type": "function",
            "function": {
                "name": "update_csv_from_knowledge",
                "description": "knowledge.txt に記録されたCSVから対象を選び、指示に基づく更新（列追加/行追記/セル更新）を行って保存する。update_spec を直接渡してもよい。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "instruction": {
                            "type": "string",
                            "description": "自然文の指示。例: 『在庫台帳に列「担当者」を追加して、今日の入庫分を1行追記』"
                        },
                        "update_spec": {
                            "type": "object",
                            "description": "更新計画。LLMが自動設計して渡すことを想定。",
                            "properties": {
                                "filename": {"type": "string", "description": "更新対象CSVのフルパス。knowledgeの候補以外は不可。"},
                                "select_by_description": {"type": "string", "description": "説明/タイトルから選ぶキーワード（filenameが無い場合）"},
                                "delimiter": {"type": "string"},
                                "quotechar": {"type": "string"},
                                "add_columns": {
                                    "type": "array",
                                    "description": "列の追加。全既存行に default を埋める。",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "default": {"description": "既存行に入れる既定値", "nullable": True},
                                            "position": {"type": "string", "enum": ["start","end"], "default": "end"},
                                            "after": {"type": "string", "description": "この列の直後に挿入（positionより優先）"}
                                        },
                                        "required": ["name"]
                                    }
                                },
                                "append_rows": {
                                    "type": "array",
                                    "description": "行の追記。headers/rows または objects のいずれか（両方可）。",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "headers": {"type": "array", "items": {"type": "string"}},
                                            "rows": {"type": "array", "items": {"type": "array", "items": {}}},
                                            "objects": {"type": "array", "items": {"type": "object"}}
                                        }
                                    }
                                },
                                "set_cells": {
                                    "type": "array",
                                    "description": "任意セルを書き換え（行インデックス基準）。",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "row_index": {"type": "integer", "description": "0始まりでヘッダーを除いたデータ行のインデックス"},
                                            "column": {"type": "string", "description": "列名"},
                                            "value": {"description": "書き込む値"}
                                        },
                                        "required": ["row_index","column","value"]
                                    }
                                },
                                "save_as": {"type": "string", "description": "別名保存先（任意）"}
                            }
                        }
                    },
                    "required": []
                }
            }
        })

        # RAG検索
        defs.append({
            "type": "function",
            "function": {
                "name": "read_document",
                "description": "RAG検索。枚方市の地震災害関連ドキュメントから、章・節・ページを含む根拠付きの抜粋を返す。",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "検索クエリ"}},
                    "required": ["query"]
                }
            }
        })

        return defs

    def send_message(self, user_message: str) -> str:
        self.add_message("user", user_message)

        system_prompt = {"role": "system", "content": self.base_system_content}
        messages = [system_prompt] + self.conversation_history

        response = self.client.chat.completions.create(
            model="gpt-5-mini",
            messages=messages + [
                {"role": "system", "content":
                 "CSVの作成依頼なら create_csv_file、更新依頼なら update_csv_from_knowledge、"
                 "調査許可があるなら read_document を1回だけ呼び出す。"}
            ],
            tools=self.get_function_definitions(mode="all"),
            tool_choice="auto"
        )

        response_message = response.choices[0].message

        if getattr(response_message, "tool_calls", None):
            tool_call = response_message.tool_calls[0]
            fname = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")

            if fname == "create_csv_file":
                filepath = create_csv_file(**args)
                assistant_message = f"CSVテンプレートを作成しました。保存先は「{filepath}」です。"

            elif fname == "update_csv_from_knowledge":
                saved = update_csv_from_knowledge(**args)
                assistant_message = f"CSVを更新しました。保存先は「{saved}」です。"

            elif fname == "read_document":
                query = (args.get("query") or "").strip()
                print(f"📚 調べています... (キーワード: {query})")
                result = self.read_document(query)
                assistant_message = result  # 根拠付きの全文（抜粋）をそのまま返す

            else:
                assistant_message = "未対応のツールが呼ばれました。"
        else:
            assistant_message = response_message.content

        self.add_message("assistant", assistant_message)
        return assistant_message


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------
def main():
    print("commanda:")
    print("   /clear   - 会話履歴をクリア")
    print("   /history - 会話履歴を表示")
    print("   /exit    - 終了")

    try:
        chat = ChatWithMemory()
    except Exception as e:
        print(f"error: {e}")
        return

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() == "/exit":
                print("bie")
                break
            elif user_input.lower() == "/clear":
                chat.clear_history()
                print("🧹 会話履歴をクリアしました")
                continue
            elif user_input.lower() == "/history":
                history = chat.get_conversation_history()
                if history:
                    print("\n📖 会話履歴:")
                    for i, msg in enumerate(history, 1):
                        role = msg["role"].upper()
                        if role != "SYSTEM":
                            print(f"{role}: {msg['content']}")
                else:
                    print("会話履歴はありません")
                print()
                continue
            elif user_input:
                print("assitant ", end="", flush=True)
                response = chat.send_message(user_input)
                print(response)
                print()

        except KeyboardInterrupt:
            print("\nbie")
            break
        except Exception as e:
            print(f"error: {e}")


if __name__ == "__main__":
    main()
