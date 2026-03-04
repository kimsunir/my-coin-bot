import streamlit as st

# 1. 화면 설정
st.title("💰 코인 엔진 생존 테스트")

# 2. 아주 단순한 숫자 표시
st.write("### 현재 자산: 10,000,000원")

# 3. 작동 확인용 버튼
if st.button("여기를 눌러보세요"):
    st.balloons()
    st.success("와! 화면이 드디어 떴어요! 언니 성공이에요!")

st.write("이 화면이 보인다면 이제 기능을 추가해도 됩니다.")
