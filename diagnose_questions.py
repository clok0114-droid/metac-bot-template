"""どのトーナメントに、いま何問出ているかを無料で確認する。

Market Pulse は bot が賞金対象（$7,500）で、FutureEval とは別のプール。
ただし「数値のグループ問題を扱えること」「問題の生存中に予測を更新し続けること」
が条件とされている。テンプレートは tournament モードで
skip_previously_forecasted_questions=True なので、更新し続ける作りになっていない。

まず母数と問題の種類を見る。LLM は呼ばない。費用0。
"""

from __future__ import annotations

import asyncio
import collections
import logging

from bot_helpers import silence_noisy_dependencies

silence_noisy_dependencies()

from forecasting_tools import MetaculusClient

logger = logging.getLogger(__name__)


async def main() -> None:
    client = MetaculusClient()
    targets = [
        ("FutureEval 本戦", client.CURRENT_AI_COMPETITION_ID),
        ("MiniBench", client.CURRENT_MINIBENCH_ID),
        ("Market Pulse (current)", client.CURRENT_MARKET_PULSE_ID),
        ("Market Pulse 26q3", "market-pulse-26q3"),
        ("Metaculus Cup (練習用)", client.CURRENT_METACULUS_CUP_ID),
        ("bot-testing-area", "bot-testing-area"),
    ]
    print("=" * 78)
    for label, tid in targets:
        for mode in ("exclude", "unpack_subquestions"):
            try:
                qs = await client.get_all_open_questions_from_tournament(
                    tid, group_question_mode=mode
                )
                kinds = collections.Counter(type(q).__name__ for q in qs)
                print(f"  {label:<24} id={str(tid):<12} group={mode:<20} "
                      f"{len(qs):>4} 問  {dict(kinds)}")
            except Exception as exc:
                print(f"  {label:<24} id={str(tid):<12} group={mode:<20} "
                      f"ERR {type(exc).__name__}: {str(exc)[:60]}")
    print("=" * 78)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
