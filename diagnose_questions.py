"""コミュニティ予測が現行APIのどこに入っているかを生の JSON で特定する。

直前の診断で、公開時刻を過ぎて予測者が11〜182人いる問題30件すべてについて
community_prediction_at_access_time が None だった。値が無いのではなく
forecasting-tools が読めていない。Benchmarker はこの値を採点基準に使うので、
どこから読み直せばよいかを確定させる。

LLM は呼ばない。費用0。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

import requests

from bot_helpers import silence_noisy_dependencies

silence_noisy_dependencies()

from forecasting_tools.helpers.metaculus_client import ApiFilter, MetaculusClient

logger = logging.getLogger(__name__)
API = "https://www.metaculus.com/api"


def _walk(obj, path="", depth=0, out=None):
    """数値が入っている葉のうち、確率らしいものを集める。"""
    if out is None:
        out = []
    if depth > 6:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            _walk(v, f"{path}.{k}", depth + 1, out)
    elif isinstance(obj, list):
        if obj and isinstance(obj[-1], (dict, list)):
            _walk(obj[-1], f"{path}[-1]", depth + 1, out)
        elif obj and isinstance(obj[-1], (int, float)):
            out.append((f"{path}[-1]", obj[-1]))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        if 0.0 <= float(obj) <= 1.0:
            out.append((path, obj))
    return out


async def main() -> None:
    client = MetaculusClient()
    questions = await client.get_questions_matching_filter(
        ApiFilter(
            allowed_statuses=["open"],
            allowed_types=["binary"],
            num_forecasters_gte=50,
            group_question_mode="exclude",
        ),
        num_questions=2,
        randomly_sample=True,
        error_if_question_target_missed=False,
    )
    headers = {"Authorization": f"Token {os.environ['METACULUS_TOKEN']}"}
    for q in questions:
        pid = getattr(q, "id_of_post", None) or getattr(q, "post_id", None)
        print("=" * 76)
        print(f"post_id={pid}  forecasters={getattr(q, 'num_forecasters', None)}")
        print(f"  {str(getattr(q, 'question_text', ''))[:66]}")
        r = requests.get(f"{API}/posts/{pid}/", headers=headers, timeout=40)
        print(f"  HTTP {r.status_code}")
        if r.status_code != 200:
            print("  " + r.text[:200])
            continue
        data = r.json()
        print(f"  トップレベルのキー: {sorted(data.keys())}")
        qd = data.get("question") or {}
        print(f"  question 内のキー : {sorted(qd.keys())}")
        agg = qd.get("aggregations") or data.get("aggregations") or {}
        print(f"  aggregations のキー: {sorted(agg.keys()) if isinstance(agg, dict) else type(agg)}")
        if isinstance(agg, dict):
            for name, body in agg.items():
                if not isinstance(body, dict):
                    continue
                keys = sorted(body.keys())
                print(f"    [{name}] {keys}")
                latest = body.get("latest")
                if isinstance(latest, dict):
                    print(f"      latest のキー: {sorted(latest.keys())}")
                    for probe in ("centers", "means", "forecast_values", "medians"):
                        if probe in latest:
                            print(f"      latest[{probe}] = "
                                  f"{json.dumps(latest[probe])[:90]}")
        print("  -- 0〜1 の数値が入っている経路（上位12件）--")
        for path, val in _walk(data)[:12]:
            print(f"     {path} = {val}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
