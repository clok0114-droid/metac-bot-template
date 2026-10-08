"""aggregations.recency_weighted の history から CP を読む経路を確定させる。

直前の診断で latest が None、history は存在と分かった。ライブラリは latest を
読もうとして空振りしている。history の最後の要素の形を見て、どのキーを使えば
二値問題のコミュニティ予測になるかを確定させる。

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
    for q in questions:
        pid = getattr(q, "id_of_post", None) or getattr(q, "post_id", None)
        r = requests.get(f"https://www.metaculus.com/api/posts/{pid}/",
                         headers=headers, timeout=40)
        if r.status_code != 200:
            print(f"post {pid}: HTTP {r.status_code}")
            continue
        agg = ((r.json().get("question") or {}).get("aggregations") or {})
        print("=" * 76)
        print(f"post_id={pid}  {str(getattr(q, 'question_text', ''))[:52]}")
        for name in ("recency_weighted", "metaculus_prediction"):
            body = agg.get(name)
            if not isinstance(body, dict):
                print(f"  [{name}] 無し")
                continue
            hist = body.get("history")
            print(f"  [{name}] latest={type(body.get('latest')).__name__} "
                  f"history={type(hist).__name__} "
                  f"len={len(hist) if isinstance(hist, list) else 'n/a'}")
            if isinstance(hist, list) and hist:
                last = hist[-1]
                if isinstance(last, dict):
                    print(f"    history[-1] のキー: {sorted(last.keys())}")
                    for k in ("centers", "means", "medians", "forecast_values",
                              "forecaster_count", "end_time"):
                        if k in last:
                            print(f"      {k} = {json.dumps(last[k])[:76]}")
                else:
                    print(f"    history[-1] の型: {type(last).__name__}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
