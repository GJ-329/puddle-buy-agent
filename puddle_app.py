import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 페이지 설정 ---
st.set_page_config(page_title="웅덩이 매매법 전략 에이전트", layout="wide")

# [핵심 추가] 데이터를 1시간(3600초) 동안 저장하여 야후 서버 부하 감소
@st.cache_data(ttl=3600)
def get_puddle_data(ticker):
    try:
        # 데이터 로드
        data = yf.download(ticker, period="2y", interval="1d")
        
        if data.empty or len(data) < 120:
            return None, None
        
        # 멀티인덱스 대응
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        
        df = pd.DataFrame(index=data.index)
        df['Close'] = data['Close']

        # 지표 계산
        df['SMA20'] = ta.sma(df['Close'], length=20)
        df['SMA60'] = ta.sma(df['Close'], length=60)
        df['SMA120'] = ta.sma(df['Close'], length=120)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        clean_data = df.dropna()
        if clean_data.empty:
            return None, None
            
        return clean_data.iloc[-1], df 
    except Exception as e:
        return None, None

# --- UI 레이아웃 ---
st.title("🌊 웅덩이 매매법 전략 대시보드")
st.sidebar.header("설정 (Settings)")

ticker_input = st.sidebar.text_input("종목 티커 입력", value="TQQQ")
ticker = ticker_input.upper().strip() 
cash = st.sidebar.number_input("가용 현금 ($)", min_value=0, value=10000)

# [팁] 캐시를 강제로 비우고 싶을 때 사용하는 버튼
if st.sidebar.button("데이터 새로고침 (캐시 삭제)"):
    st.cache_data.clear()
    st.rerun()

if st.button("웅덩이 진단 실행"):
    with st.spinner('웅덩이 데이터를 불러오는 중...'):
        latest, full_data = get_puddle_data(ticker)
    
    if latest is not None:
        try:
            price, sma20, sma60, sma120, rsi = float(latest['Close']), float(latest['SMA20']), float(latest['SMA60']), float(latest['SMA120']), float(latest['RSI'])
            
            status, step, action_plan = "평시 (관망)", 0, "현재는 매수 구간이 아닙니다."
            if price <= sma120 and rsi <= 35:
                step, status, action_plan = 4, "4단계: 패닉셀 구간", f"5일 분할 매수 (총 ${cash:,.2f})"
            elif price <= sma120:
                step, status, action_plan = 3, "3단계: 120일선 터치", f"5일 분할 매수 (총 ${cash*0.5:,.2f})"
            elif price <= sma60:
                step, status, action_plan = 2, "2단계: 60일선 터치", f"3일 분할 매수 (총 ${cash*0.5:,.2f})"
            elif price <= sma20:
                step, status, action_plan = 1, "1단계: 20일선 터치", f"즉시 매수 (${cash*0.1:,.2f})"

            st.subheader(f"### [{ticker}] 웅덩이 진단 리포트")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("현재가", f"${price:,.2f}")
            c2.metric("20일선", f"${sma20:,.2f}")
            c3.metric("60일선", f"${sma60:,.2f}")
            c4.metric("120일선", f"${sma120:,.2f}")
            
            st.info(f"**상태:** {status} / **RSI:** {rsi:.2f}")
            st.success(f"**🎯 전략:** {action_plan}")
            st.line_chart(full_data[['Close', 'SMA20', 'SMA60', 'SMA120']])

        except Exception as e:
            st.error(f"오류 발생: {e}")
    else:
        st.error("야후 파이낸스 차단 또는 데이터 부족. 잠시 후 다시 시도해 주세요.")
