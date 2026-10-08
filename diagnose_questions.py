"""CP が読めない原因を、ライブラリ側か呼び方かで確定させる。

ライブラリは検索時に with_cp=true を渡している（_create_url_params_for_search）。
前回の生API診断はそれを付けていなかったので、latest=None は当然だった。
ここでは同じ問題に対して
  (1) ライブラリ経由の値
  (2) 詳細エンドポイント + with_cp=true
を並べ、どちらで値が出るかを見る。(2) で出るなら、問題ごとに詳細を引いて
埋め直せばよく、Benchmarker はそのまま使える。

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


def _probe(pid: int, headers: dict, params: dict) -> str:
    r = requests.get(f"https://www.metaculus.com/api/posts/{pid}/",
                     headers=headers, params=params, timeout=40)
    if r.status_code != 200:
        return f"HTTP {r.status_code}"
    agg = ((r.json().get("question") or {}).get("aggregations") or {})
    rw = agg.get("recency_weighted")
    if not isinstance(rw, dict):
        return "recency_weighted 無し"
    latest, hist = rw.get("latest"), rw.get("history")
    if isinstance(latest, dict) and latest.get("centers"):
        return f"latest.centers={json.dumps(latest['centers'])[:30]}"
    if isinstance(hist, list) and hist and isinstance(hist[-1], dict):
        return (f"latest=None / history[{len(hist)}][-1].centers="
                f"{json.dumps(hist[-1].get('centers'))[:30]}")
    return f"latest={type(latest).__name__} history={type(hist).__name__}"


async def main() -> None:
    client = MetaculusClient()
    questions = await client.get_questions_matching_filter(
        ApiFilter(
            allowed_statuses=["open"],
            allowed_types=["binary"],
            num_forecasters_gte=50,
            group_question_mode="exclude",
        ),
        num_questions=3,
        randomly_sample=True,
        error_if_question_target_missed=False,
    )
    headers = {"Authorization": f"Token {os.environ['METACULUS_TOKEN']}"}
    print("=" * 78)
    for q in questions:
        pid = getattr(q, "id_of_post", None) or getattr(q, "post_id", None)
        lib = getattr(q, "community_prediction_at_access_time", None)
        print(f"post {pid}  {str(getattr(q, 'question_text', ''))[:44]}")
        print(f"  (1) ライブラリ経由        : {lib}")
        print(f"  (2) with_cp なしの詳細    : {_probe(pid, headers, {})}")
        print(f"  (3) with_cp=true の詳細   : {_probe(pid, headers, {'with_cp': 'true'})}")
    print("=" * 78)
    print("(3) で値が出れば、問題ごとに詳細を引いて埋め直す方針で確定。")
    print("=" * 78)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
