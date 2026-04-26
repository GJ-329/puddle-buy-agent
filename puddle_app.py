import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 페이지 설정 ---
st.set_page_config(page_title="웅덩이 매매법 멀티 대시보드", layout="wide")

@st.cache_data(ttl=3600)
def get_puddle_data(ticker):
    try:
        data = yf.download(ticker, period="2y", interval="1d", progress=False)
        if data.empty or len(data) < 120: return None, None
        
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        
        df = pd.DataFrame(index=data.index)
        df['Close'] = data['Close']
        df['SMA20'] = ta.sma(df['Close'], length=20)
        df['SMA60'] = ta.sma(df['Close'], length=60)
        df['SMA120'] = ta.sma(df['Close'], length=120)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        clean_data = df.dropna()
        return clean_data.iloc[-1], df 
    except:
        return None, None

# --- UI 레이아웃 ---
st.title("🌊 웅덩이 매매법 멀티 전략 대시보드")

with st.sidebar:
    st.header("📋 포트폴리오 설정")
    # 여러 종목 입력 (쉼표로 구분)
    ticker_list = st.text_input("조회할 티커들 (쉼표 구분)", value="TQQQ, QLD, SOXL")
    tickers = [t.strip().upper() for t in ticker_list.split(",")]
    
    cash_per_ticker = st.number_input("종목당 할당 현금 ($)", min_value=0, value=5000)
    
    if st.button("새로고침 (캐시 삭제)"):
        st.cache_data.clear()
        st.rerun()

if st.button("🔄 전 종목 웅덩이 진단"):
    summary_data = []
    
    # 각 종목별 진단 루프
    for ticker in tickers:
        latest, full_data = get_puddle_data(ticker)
        
        if latest is not None:
            price, sma20, sma60, sma120, rsi = float(latest['Close']), float(latest['SMA20']), float(latest['SMA60']), float(latest['SMA120']), float(latest['RSI'])
            
            # 단계 판정
            step = 0
            if price <= sma120 and rsi <= 35: step = 4
            elif price <= sma120: step = 3
            elif price <= sma60: step = 2
            elif price <= sma20: step = 1
            
            summary_data.append({
                "티커": ticker,
                "현재가": f"${price:,.2f}",
                "RSI": round(rsi, 1),
                "진단 단계": f"{step}단계 웅덩이",
                "상태": "🔴 매수구간" if step > 0 else "⚪ 관망",
                "데이터": (latest, full_data) # 상세 출력을 위해 저장
            })
    
    # --- 상단 요약 테이블 ---
    st.subheader("📊 한눈에 보는 웅덩이 현황")
    if summary_data:
        summary_df = pd.DataFrame(summary_data).drop(columns=['데이터'])
        st.table(summary_df)
        
        st.divider()
        
        # --- 하단 개별 상세 리포트 (Expander 활용) ---
        st.subheader("🔍 종목별 상세 리포트")
        for item in summary_data:
            ticker = item["티커"]
            latest, full_data = item["데이터"]
            
            with st.expander(f"📌 {ticker} 상세 분석 및 차트 보기"):
                p, s20, s60, s120, r = float(latest['Close']), float(latest['SMA20']), float(latest['SMA60']), float(latest['SMA120']), float(latest['RSI'])
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.write(f"**현재가:** ${p:,.2f}")
                    st.write(f"**20일선:** ${s20:,.2f}")
                    st.write(f"**60일선:** ${s60:,.2f}")
                    st.write(f"**120일선:** ${s120:,.2f}")
                    
                    # 액션 플랜 계산
                    action = "현재는 매수 구간이 아닙니다."
                    if item["진단 단계"] == "1단계 웅덩이": action = f"지금 즉시 ${cash_per_ticker*0.1:,.2f} 매수"
                    elif item["진단 단계"] == "2단계 웅덩이": action = f"3일간 매일 ${cash_per_ticker*0.5/3:,.2f} 분할 매수"
                    elif item["진단 단계"] == "3단계 웅덩이": action = f"5일간 매일 ${cash_per_ticker*0.5/5:,.2f} 분할 매수"
                    elif item["진단 단계"] == "4단계 웅덩이": action = f"5일간 매일 ${cash_per_ticker/5:,.2f} 분할 매수"
                    
                    st.success(f"**전략:** {action}")
                
                with col2:
                    st.line_chart(full_data[['Close', 'SMA20', 'SMA60', 'SMA120']])
    else:
        st.error("입력한 티커에서 데이터를 불러올 수 없습니다.")
