"""이동평균/RSI 등 기술적 지표 계산 유틸리티. crypto/stocks_kr/stocks_us fetch 스크립트가 공용으로 사용한다."""
import pandas as pd


def moving_averages(closes: list[float]) -> dict:
    s = pd.Series(closes, dtype="float64")
    result = {}
    for window in (5, 20, 60):
        if len(s) >= window:
            result[f"ma{window}"] = round(float(s.tail(window).mean()), 4)
        else:
            result[f"ma{window}"] = None
    return result


def rsi(closes: list[float], period: int = 14) -> float | None:
    s = pd.Series(closes, dtype="float64")
    if len(s) < period + 1:
        return None
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean().iloc[-1]
    avg_loss = loss.rolling(period).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(float(100 - 100 / (1 + rs)), 2)
