"""「本戦は0問」が『止まっている』のか『問題が短時間しか開かない』のかを確定させる。

背反検証から「FutureEval の問題は一度に最大5問、1回1.5時間しか開かない。
0問は平常状態」と指摘された。open だけ数えても区別がつかない。status を問わず
総数を数えれば、トーナメントに問題が存在するかが分かる。

LLM は呼ばない。費用0。
"""

from __future__ import annotations

import asyncio
import logging

from bot_helpers import silence_noisy_dependencies

silence_noisy_dependencies()

from forecasting_tools.helpers.metaculus_client import ApiFilter, MetaculusClient

logger = logging.getLogger(__name__)

TOURNAMENTS = [
    ("Fall 2026 FutureEval", "fall-futureeval-2026"),
    ("Fall 2026 (数値ID)", 33022),
    ("MiniBench", "minibench"),
    ("Market Pulse 26q4", "market-pulse-26q4"),
]
STATUSES = ["open", "closed", "resolved"]


async def count(client: MetaculusClient, tid, status: str):
    try:
        questions = await client.get_questions_matching_filter(
            ApiFilter(
                allowed_tournaments=[tid],
                allowed_statuses=[status],
                group_question_mode="unpack_subquestions",
            ),
            error_if_question_target_missed=False,
        )
        return len(questions), questions
    except Exception as exc:
        return f"ERR {type(exc).__name__}: {str(exc)[:40]}", []


async def main() -> None:
    client = MetaculusClient()
    print("=" * 80)
    print(f"{'トーナメント':<24} {'ID':<22} open / closed / resolved")
    print("-" * 80)
    spans = []
    for label, tid in TOURNAMENTS:
        cells = []
        for status in STATUSES:
            n, qs = await count(client, tid, status)
            cells.append(str(n))
            if status in ("closed", "resolved") and "futureeval" in str(tid):
                spans.extend(qs)
        print(f"  {label:<22} {str(tid):<22} {' / '.join(cells)}")
    print("=" * 80)

    print("\n開いていた時間の実例（Fall 2026 の closed / resolved から最大10件）")
    shown = 0
    for q in spans:
        open_time = getattr(q, "open_time", None)
        close_time = getattr(q, "close_time", None)
        if not (open_time and close_time):
            continue
        hours = (close_time - open_time).total_seconds() / 3600
        print(f"   open={str(open_time)[:16]}  close={str(close_time)[:16]}  {hours:7.2f} 時間")
        shown += 1
        if shown >= 10:
            break
    if shown == 0:
        print("   （時刻が取れる問題がなかった）")
    print("=" * 80)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
