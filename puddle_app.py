import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 페이지 설정 ---
st.set_page_config(page_title="웅덩이 매매법 전략 에이전트", layout="wide")

def get_puddle_data(ticker):
    try:
        # 1. 데이터 로드 (가장 표준적인 방식으로 수집)
        data = yf.download(ticker, period="2y", interval="1d")
        
        if data.empty or len(data) < 120:
            return None, None
        
        # 2. [핵심 수정] 멀티인덱스 및 컬럼 이름 구조 강제 평탄화
        # 최근 yfinance 이슈: 컬럼이 ('Close', 'TQQQ') 형태일 때 ('Close')만 남김
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        
        # 3. 데이터프레임 재구성 (안전하게 Close 컬럼 확보)
        df = pd.DataFrame(index=data.index)
        
        if 'Close' in data.columns:
            df['Close'] = data['Close']
        elif 'Adj Close' in data.columns:
            df['Close'] = data['Adj Close']
        else:
            # 둘 다 없을 경우 마지막 수단으로 첫 번째 컬럼 사용
            df['Close'] = data.iloc[:, 0]

        # 4. 지표 계산
        df['SMA20'] = ta.sma(df['Close'], length=20)
        df['SMA60'] = ta.sma(df['Close'], length=60)
        df['SMA120'] = ta.sma(df['Close'], length=120)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # 5. 빈 값 제거 (지표 계산에 필요한 초기 기간 제외)
        clean_data = df.dropna()
        
        if clean_data.empty:
            return None, None
            
        return clean_data.iloc[-1], df 
    except Exception as e:
        st.error(f"데이터 처리 중 기술적 오류 발생: {e}")
        return None, None

# --- UI 레이아웃 ---
st.title("🌊 웅덩이 매매법 전략 대시보드")
st.sidebar.header("설정 (Settings)")

ticker_input = st.sidebar.text_input("종목 티커 입력 (예: TQQQ, QLD)", value="TQQQ")
ticker = ticker_input.upper().strip() 
cash = st.sidebar.number_input("해당 종목 할당 가용 현금 ($)", min_value=0, value=10000)

if st.button("웅덩이 진단 실행"):
    with st.spinner('웅덩이 수심 측정 중...'):
        latest, full_data = get_puddle_data(ticker)
    
    if latest is not None:
        try:
            # 데이터 추출
            price = float(latest['Close'])
            sma20 = float(latest['SMA20'])
            sma60 = float(latest['SMA60'])
            sma120 = float(latest['SMA120'])
            rsi = float(latest['RSI'])
            
            # 웅덩이 단계 판정
            status, step, buy_amount, action_plan = "평시 (관망/현금 비축)", 0, 0, "현재는 매수 구간이 아닙니다."

            if price <= sma120 and rsi <= 35:
                step, status, buy_amount = 4, "4단계: 패닉셀 구간", cash
                action_plan = f"금일부터 5일간 매일 ${buy_amount/5:,.2f} 씩 분할 매수 (전량)"
            elif price <= sma120:
                step, status, buy_amount = 3, "3단계: 120일선 터치", cash * 0.5
                action_plan = f"금일부터 5일간 매일 ${buy_amount/5:,.2f} 씩 분할 매수"
            elif price <= sma60:
                step, status, buy_amount = 2, "2단계: 60일선 터치", cash * 0.5
                action_plan = f"금일부터 3일간 매일 ${buy_amount/3:,.2f} 씩 분할 매수"
            elif price <= sma20:
                step, status, buy_amount = 1, "1단계: 20일선 터치", cash * 0.1
                action_plan = f"지금 즉시 ${buy_amount:,.2f} 매수 수행"

            # --- 결과 리포트 출력 ---
            st.subheader(f"### [{ticker}] 웅덩이 진단 리포트")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("현재가", f"${price:,.2f}")
            c2.metric("20일선", f"${sma20:,.2f}", f"{price-sma20:,.2f}")
            c3.metric("60일선", f"${sma60:,.2f}", f"{price-sma60:,.2f}")
            c4.metric("120일선", f"${sma120:,.2f}", f"{price-sma120:,.2f}")
            
            st.info(f"**현재 상태:** {status} / **RSI(14):** {rsi:.2f}")
            
            if step > 0:
                st.success(f"**🎯 매수 전략:** {action_plan}")
            else:
                st.warning(f"**💡 매수 전략:** {action_plan}")

            # 차트 시각화
            st.line_chart(full_data[['Close', 'SMA20', 'SMA60', 'SMA120']])

        except Exception as e:
            st.error(f"결과 출력 중 오류가 발생했습니다: {e}")
    else:
        st.error(f"'{ticker}' 데이터를 가져올 수 없습니다. 티커가 정확한지 확인해 주세요.")