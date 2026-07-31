# -*- coding: utf-8 -*-
"""
매일 아침 실행되는 종목 스크리닝 메인 스크립트. (네이버 증권 전용 버전)

조건 (전일 종가 기준):
1) 일봉 RSI(14) <= 30
2) 최근 3거래일 연속 외국인 + 기관 모두 순매수 (네이버 증권 기준, 수량 단위)
3) 이격도(20일선 기준)가 최근 3일간 연속 감소(수렴) 중

* KRX(pykrx)는 GitHub Actions 등 해외 서버에서 접속이 차단되는 경우가 있어
  사용하지 않고, 시세/수급/종목목록 모두 네이버 증권에서 가져온다.
* 이로 인해 '투신' 세부 구분은 제공되지 않으며, 외국인+기관 합계 기준으로 판단한다.

결과: docs/results.json 에 저장 (GitHub Pages가 이 폴더를 서빙)
"""
import os
import json
import datetime
import traceback

import pandas as pd

from indicators import calc_rsi, calc_disparity, is_disparity_decreasing
from naver_price import get_daily_ohlcv, get_stock_name
from naver_investor import get_foreign_institution_net, has_3day_consecutive_net_buy
from naver_universe import get_top_market_cap_universe
from retry_util import retry_call

# ----------------------------------------------------------------------------
# 설정값 (필요시 조정)
# ----------------------------------------------------------------------------
RSI_THRESHOLD = 30          # RSI 이 값 이하
DISPARITY_MA_PERIOD = 20    # 이격도 기준 이동평균 기간
PRICE_HISTORY_DAYS = 40     # RSI/이격도 계산에 필요한 최소 시세 일수
INVESTOR_HISTORY_DAYS = 10  # 수급 데이터 조회 일수(영업일 기준 여유있게)
TOP_N_BY_MARKETCAP = 300    # 전종목 대신 시가총액 상위 N개만 스캔 (성능/속도 고려)
RESULT_COUNT = 10           # 최종 표시할 종목 수
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "docs", "results.json")


def get_label_date() -> str:
    """
    화면 표시용 기준일(YYYYMMDD). 주말만 건너뛰는 단순 근사치이며,
    실제 계산은 각 종목의 네이버 시세에 있는 실제 최근 거래일을 사용하므로
    이 값은 라벨(표시) 목적으로만 쓰인다.
    """
    d = datetime.date.today()
    while d.weekday() >= 5:  # 5=토요일, 6=일요일
        d -= datetime.timedelta(days=1)
    return d.strftime("%Y%m%d")


def screen_stock(code: str) -> dict | None:
    """개별 종목이 3개 조건을 모두 만족하는지 확인하고, 만족 시 결과 dict 반환."""
    try:
        price_df = get_daily_ohlcv(code, days=PRICE_HISTORY_DAYS)
        if len(price_df) < DISPARITY_MA_PERIOD + 3:
            return None

        close = price_df["close"]
        rsi = calc_rsi(close, period=14)
        disparity = calc_disparity(close, ma_period=DISPARITY_MA_PERIOD)

        latest_rsi = rsi.iloc[-1]
        if pd.isna(latest_rsi) or latest_rsi > RSI_THRESHOLD:
            return None

        if not is_disparity_decreasing(disparity, lookback=2):
            return None

        investor_df = get_foreign_institution_net(code, days=INVESTOR_HISTORY_DAYS)
        if not has_3day_consecutive_net_buy(investor_df):
            return None

        name = get_stock_name(code)
        return {
            "code": code,
            "name": name,
            "rsi": round(float(latest_rsi), 2),
            "disparity": round(float(disparity.iloc[-1]), 2),
            "close": float(close.iloc[-1]),
            "foreign_net_3d": int(investor_df["foreign_net"].tail(3).sum()),
            "institution_net_3d": int(investor_df["institution_net"].tail(3).sum()),
        }
    except Exception:
        # 개별 종목 에러는 전체 스크리닝을 막지 않도록 무시하고 로그만 출력
        print(f"[WARN] {code} 처리 중 오류:\n{traceback.format_exc()}")
        return None


def main():
    base_date = get_label_date()
    print(f"기준일(라벨): {base_date}")

    universe = retry_call(
        get_top_market_cap_universe, TOP_N_BY_MARKETCAP, retries=3, delay=3.0
    )
    print(f"스캔 대상 종목 수: {len(universe)}")

    matched = []
    for idx, code in enumerate(universe, start=1):
        result = screen_stock(code)
        if result:
            matched.append(result)
        if idx % 50 == 0:
            print(f"진행 상황: {idx}/{len(universe)} (현재 조건 충족: {len(matched)}개)")

    matched.sort(key=lambda x: x["rsi"])
    top_matches = matched[:RESULT_COUNT]

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    output = {
        "base_date": base_date,
        "generated_at": datetime.datetime.now().isoformat(),
        "conditions": {
            "rsi_threshold": RSI_THRESHOLD,
            "disparity_ma_period": DISPARITY_MA_PERIOD,
            "consecutive_days": 3,
            "data_source": "naver",
        },
        "count": len(top_matches),
        "stocks": top_matches,
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"완료: {len(top_matches)}개 종목 저장 -> {OUTPUT_PATH}")
    return output


if __name__ == "__main__":
    main()
