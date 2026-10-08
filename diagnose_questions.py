"""ベンチマーク用の問題が0件になる原因を切り分ける。

get_benchmark_questions は、サーバー側で1,200件該当すると見積もったうえで
ローカルの絞り込みで0件にして落ちる。サーバーとローカルでこれだけ食い違う
のは「条件を満たす問題が無い」より「ローカル側の判定が現在のAPIの形と
噛み合っていない」を疑うべき差。どの条件が効いているかを1回で出す。

LLM は呼ばないので費用は0。
"""

from __future__ import annotations

import asyncio
import logging

from bot_helpers import silence_noisy_dependencies

silence_noisy_dependencies()

from forecasting_tools.helpers.metaculus_client import ApiFilter, MetaculusClient

logger = logging.getLogger(__name__)

WANT = 100


def _filter(**overrides) -> ApiFilter:
    base = dict(
        allowed_statuses=["open"],
        allowed_types=["binary"],
        num_forecasters_gte=10,
        includes_bots_in_aggregates=False,
        community_prediction_exists=True,
        group_question_mode="exclude",
    )
    base.update(overrides)
    return ApiFilter(**{k: v for k, v in base.items() if v is not None})


CASES = [
    ("既定に近い形（両方の条件あり）", _filter()),
    ("bot含む集計の条件を外す", _filter(includes_bots_in_aggregates=None)),
    ("コミュニティ予測の存在条件を外す", _filter(community_prediction_exists=None)),
    ("両方外す", _filter(includes_bots_in_aggregates=None,
                         community_prediction_exists=None)),
    ("両方外し、予測者数の下限も外す",
     _filter(includes_bots_in_aggregates=None,
             community_prediction_exists=None,
             num_forecasters_gte=None)),
    ("bot集計を True にしてみる", _filter(includes_bots_in_aggregates=True)),
]


async def main() -> None:
    client = MetaculusClient()
    print("=" * 74)
    for label, api_filter in CASES:
        try:
            qs = await client.get_questions_matching_filter(
                api_filter,
                num_questions=WANT,
                randomly_sample=True,
                error_if_question_target_missed=False,
            )
            n = len(qs)
            note = ""
            if n:
                q = qs[0]
                note = f"  例: {str(getattr(q, 'question_text', ''))[:52]}"
            print(f"  {n:>4} 件  {label}{note}")
        except Exception as e:
            print(f"  ERR     {label}  -> {type(e).__name__}: {str(e)[:110]}")
    print("=" * 74)
    print("件数が出た行の条件を、benchmark.py 側に採用する。")
    print("=" * 74)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
