"""どのトーナメントに、いま何問出ているかを無料で確認する。

get_all_open_questions_from_tournament は同期メソッド。await を付けると
「object list can't be used in await expression」で全件落ちる（一度やった）。

ライブラリの CURRENT_MARKET_PULSE_ID は market-pulse-26q2 を指していて、
四半期に追いついていない。Q4 を明示して確かめる。

LLM は呼ばない。費用0。
"""

from __future__ import annotations

import collections
import logging

from bot_helpers import silence_noisy_dependencies

silence_noisy_dependencies()

from forecasting_tools import MetaculusClient

logger = logging.getLogger(__name__)


def main() -> None:
    client = MetaculusClient()
    print(f"ライブラリの CURRENT_MARKET_PULSE_ID = {client.CURRENT_MARKET_PULSE_ID}")
    print(f"ライブラリの CURRENT_AI_COMPETITION_ID = {client.CURRENT_AI_COMPETITION_ID}")
    targets = [
        ("FutureEval 本戦", client.CURRENT_AI_COMPETITION_ID),
        ("MiniBench", client.CURRENT_MINIBENCH_ID),
        ("Market Pulse 26q4", "market-pulse-26q4"),
        ("Market Pulse 26q3", "market-pulse-26q3"),
        ("Market Pulse 26q2", "market-pulse-26q2"),
        ("bot-testing-area", "bot-testing-area"),
    ]
    print("=" * 78)
    for label, tid in targets:
        for mode in ("exclude", "unpack_subquestions"):
            try:
                qs = client.get_all_open_questions_from_tournament(
                    tid, group_question_mode=mode
                )
                kinds = collections.Counter(type(q).__name__ for q in qs)
                print(f"  {label:<20} {str(tid):<20} {mode:<20} "
                      f"{len(qs):>4} 問  {dict(kinds)}")
            except Exception as exc:
                print(f"  {label:<20} {str(tid):<20} {mode:<20} "
                      f"ERR {type(exc).__name__}: {str(exc)[:55]}")
    print("=" * 78)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    main()
