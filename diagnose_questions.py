"""取得した問題に、採点基準となるコミュニティ予測が実際に入っているかを見る。

community_prediction_exists=True が1,200件を0件にする原因になっている。
判定は question.community_prediction_at_access_time is not None を見るだけ
なので、値が本当に無いのか、パーサが現在のAPIの形から読めていないのかを
区別する必要がある。Benchmarker はこの値を採点基準に使うので、ここが埋まって
いなければ CP 基準の A/B は成立しない。

LLM は呼ばない。費用0。
"""

from __future__ import annotations

import asyncio
import logging

from bot_helpers import silence_noisy_dependencies

silence_noisy_dependencies()

from forecasting_tools.helpers.metaculus_client import ApiFilter, MetaculusClient

logger = logging.getLogger(__name__)


async def main() -> None:
    client = MetaculusClient()
    api_filter = ApiFilter(
        allowed_statuses=["open"],
        allowed_types=["binary"],
        num_forecasters_gte=10,
        group_question_mode="exclude",
    )
    questions = await client.get_questions_matching_filter(
        api_filter,
        num_questions=30,
        randomly_sample=True,
        error_if_question_target_missed=False,
    )
    print("=" * 76)
    print(f"取得 {len(questions)} 問。採点基準の有無を見る。")
    print("=" * 76)
    have_cp = 0
    for q in questions[:30]:
        cp = getattr(q, "community_prediction_at_access_time", None)
        reveal = getattr(q, "cp_reveal_time", None)
        bots = getattr(q, "includes_bots_in_aggregates", None)
        nf = getattr(q, "num_forecasters", None)
        if cp is not None:
            have_cp += 1
        print(f"  cp={str(cp):<10} reveal={str(reveal)[:19]:<19} "
              f"bots={str(bots):<5} forecasters={str(nf):<5} "
              f"{str(getattr(q, 'question_text', ''))[:40]}")
    print("=" * 76)
    print(f"コミュニティ予測が入っていた: {have_cp} / {len(questions)} 問")
    if have_cp == 0:
        print("→ 値が1件も読めていない。パーサ側か、公開時刻前の問題ばかりか。")
        print("→ CP を基準にした A/B は、このままでは成立しない。")
    else:
        print("→ この件数で A/B が成立する。benchmark.py 側の条件を合わせる。")
    print("=" * 76)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
