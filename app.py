import streamlit as st
import sqlite3
import datetime
import re
import os

# --- DB 설정 ---
DB_NAME = "vc_pool_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommended_companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            company_name TEXT NOT NULL,
            contact_person TEXT,
            contact_email TEXT,
            contact_phone TEXT,
            social_sector TEXT,
            investment_stage TEXT,
            intro_url TEXT,
            recommendation_reason TEXT,
            raw_searched_name TEXT UNIQUE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_metrics (
            metric_name TEXT PRIMARY KEY,
            value INTEGER
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO app_metrics (metric_name, value) VALUES ('visit_count', 0)")
    conn.commit()
    conn.close()

def add_recommendation(data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO recommended_companies 
            (timestamp, company_name, contact_person, contact_email, contact_phone, 
            social_sector, investment_stage, intro_url, recommendation_reason, raw_searched_name)
            VALUES (:timestamp, :company_name, :contact_person, :contact_email, :contact_phone,
            :social_sector, :investment_stage, :intro_url, :recommendation_reason, :raw_searched_name)
        """, data)
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_visit_count():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM app_metrics WHERE metric_name = 'visit_count'")
    count_row = cursor.fetchone()
    conn.close()
    return count_row[0] if count_row else 0

def increment_visit_count():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE app_metrics SET value = value + 1 WHERE metric_name = 'visit_count'")
    conn.commit()
    conn.close()

COMPANIES_2023 = [
    "다나씨엠", "씽즈", "에이치투케이", "이너프유", "자라나다", "휴브리스", "딱따구리", "스쿨버스", "이모티브", "해낸다컴퍼니", "나눔비타민", "도구공간", "윙윙", "로카101", "유알테크", "어뮤즈", "리브라이블리", "메디플렉서스", "복지유니온", "블루레오", "언어발전소", "원더풀플랫폼", "이모코그", "임팩터스", "포페런츠", "픽셀로", "쉘위파트너스", "웰더스스마트케어", "토끼와두꺼비", "안드레이아", "돌봄드림", "라이트하우스", "소리를보는통로", "알밤", "이디피랩", "코액터스", "파라스타엔터테인먼트", "하루하루움직임연구소", "휴카시스템", "기억산책", "세지아", "지아소프트", "마이베네핏", "레드슬리퍼스", "베이띵스", "우리동네히어로", "에스엠플래닛", "엠디스퀘어", "좋은운동장", "케이알지그룹", "핀휠", "홈체크", "그레이스케일", "다이노즈", "효돌"
]
COMPANIES_2024 = [
    "아이앤나", "카티어스", "모바일닥터", "디에이블", "그리니쉬", "디에이엘컴퍼니", "업드림코리아", "폴라이크", "키위스튜디오", "솔리브벤처스", "디엔엑스", "뷰니브랩", "아이윙티브이", "올디너리매직", "크리모", "마인드허브", "비바라비다", "솔닥", "야타브엔터", "엑스퍼트아이앤씨", "이엑스헬스케어", "인졀미", "인핸드플러스", "캥스터즈", "키뮤", "뉴힐링라이프재활운동센터", "디아앤코", "시공간", "힐링하트", "푸른나이", "내이루리", "스프링어게인", "로완", "빅디퍼", "큐라코", "코드블라썸", "투엔티닷", "고이장례연구소", "제이씨에프테크놀러지", "고수플러스", "마마품", "애스크밀리언스", "온전", "왕왕", "케어누리", "특수청소에버그린", "골든아워", "네오에이블", "정션메드", "딥비전스", "피지오", "엠디에스코트", "와우키키", "타이렐", "투아트", "잇마플", "뉴로아시스", "마인드풀커넥트", "사랑과선행", "인비저블컴퍼니", "제이엘스탠다드", "하이"
]

def normalize_company_name(name):
    if not name: return ""
    name = name.lower()
    name = name.replace("(주)", "").replace("주식회사", "")
    name = re.sub(r'\s+', '', name)
    return name

# --- Streamlit UI 구성 ---
def main():
    st.set_page_config(page_title="사회서비스 투자기업 추천", page_icon="🌱", layout="wide")

    # Custom CSS (토스 느낌을 위한 최소한의 스타일)
    st.markdown("""
        <style>
            /* Streamlit 1.29.0 이상에서 st.container(border=True)가 더 나은 옵션일 수 있음 */
            .stApp {
                background-color: #F0F2F5; /* 밝은 회색 배경 */
            }
            .main .block-container {
                padding-top: 2rem;
                padding-bottom: 2rem;
                padding-left: 3rem;
                padding-right: 3rem;
            }
            /* 카드 스타일 - st.container(border=True) 없을 경우 대비 */
            div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
                /* border: 1px solid #e0e0e0; */ /* border=True 사용 권장 */
                /* border-radius: 10px; */
                /* padding: 20px; */
                /* background-color: white; */
                /* box-shadow: 0 4px 12px rgba(0,0,0,0.05); */ /* border=True에 자체 그림자 효과 있을 수 있음 */
            }
            /* 버튼 스타일 - Streamlit 기본 버튼이 이미 깔끔함 */
            .stButton>button {
                border-radius: 8px; /* 버튼 모서리 약간 둥글게 */
                /* padding: 0.6em 1em; */
            }
            /* 입력 필드 스타일 - Streamlit 기본 사용 */
            .stTextInput input, .stTextArea textarea, .stSelectbox select {
                border-radius: 8px;
            }
            h1 { /* 페이지 제목 */
                font-size: 2.2em;
                font-weight: 600;
                color: #1A202C; /* 진한 회색 */
            }
            h2 { /* 섹션 제목 */
                font-size: 1.6em;
                font-weight: 600;
                color: #2D3748; /* 약간 연한 회색 */
                border-bottom: 2px solid #E2E8F0;
                padding-bottom: 0.3em;
                margin-top: 1.5em;
                margin-bottom: 1em;
            }
            .stAlert { /* 알림 메시지 모서리 */
                border-radius: 8px;
            }
        </style>
    """, unsafe_allow_html=True)

    init_db()

    if 'visited_this_session' not in st.session_state:
        increment_visit_count()
        st.session_state.visited_this_session = True
    current_visit_count = get_visit_count()

    # --- 헤더 ---
    st.title("🌱 사회서비스 투자기업 추천")
    st.caption(f"좋은 기업을 추천해주세요! 현재까지 {current_visit_count}번의 추천 세션이 있었어요.")
    st.divider()

    # --- 상태 초기화 (세션 간 유지) ---
    if 'show_new_form' not in st.session_state:
        st.session_state.show_new_form = False
    if 'searched_company_for_form' not in st.session_state:
        st.session_state.searched_company_for_form = ""

    # --- 섹션 1: 기업 검색 ---
    st.header("1. 추천할 기업을 검색해주세요")
    with st.container(border=True): # 카드 UI
        searched_company_name_input = st.text_input(
            "기업명",
            placeholder="예: 제미나이 (띄어쓰기, (주) 제외)",
            key="search_company_input",
            label_visibility="collapsed" # 레이블 숨김 (subheader로 대체)
        )

        if st.button("🔍 기업 검색", key="search_button", type="primary", use_container_width=True):
            if searched_company_name_input:
                st.session_state.searched_company_for_form = searched_company_name_input
                normalized_search_term = normalize_company_name(searched_company_name_input)

                found_2023 = any(normalize_company_name(c) == normalized_search_term for c in COMPANIES_2023)
                original_found_name_2023 = next((c for c in COMPANIES_2023 if normalize_company_name(c) == normalized_search_term), "") if found_2023 else ""
                
                found_2024 = any(normalize_company_name(c) == normalized_search_term for c in COMPANIES_2024)
                original_found_name_2024 = next((c for c in COMPANIES_2024 if normalize_company_name(c) == normalized_search_term), "") if found_2024 else ""

                if found_2023:
                    st.warning(f"'{original_found_name_2023}' 기업은 2023년 참여 기업입니다. 아쉽지만 본 사업 참여는 어렵습니다. 추천 감사합니다! 😊")
                    st.session_state.show_new_form = False
                elif found_2024:
                    st.warning(f"'{original_found_name_2024}' 기업은 2024년 참여 기업입니다. 아쉽지만 본 사업 참여는 어렵습니다. 추천 감사합니다! 😊")
                    st.session_state.show_new_form = False
                else:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("SELECT company_name FROM recommended_companies WHERE raw_searched_name = ?", (normalized_search_term,))
                    existing_recommendation = cursor.fetchone()
                    conn.close()

                    if existing_recommendation:
                        st.info(f"'{searched_company_name_input}' 기업은 이미 '{existing_recommendation[0]}' (으)로 추천 목록에 있습니다. 확인 감사합니다! 👍")
                        st.session_state.show_new_form = False
                    else:
                        st.success(f"'{searched_company_name_input}' 기업을 새로 추천할 수 있습니다. 아래 정보를 입력해주세요. 👇")
                        st.session_state.show_new_form = True
            else:
                st.error("기업명을 입력한 후 검색해주세요.")
                st.session_state.show_new_form = False
        
    st.write("") # 여백

    # --- 섹션 2: 신규 기업 추천 등록 폼 ---
    if st.session_state.show_new_form:
        st.header("2. 추천 기업 정보 입력")
        with st.container(border=True): # 카드 UI
            with st.form("new_company_form", clear_on_submit=False): # clear_on_submit=False로 두고 성공시 수동 초기화
                st.markdown("##### 아래 정보를 입력해주세요. (`*` 필수 항목)")
                
                company_name = st.text_input("기업명*", value=st.session_state.searched_company_for_form, help="검색한 기업명이 자동으로 입력됩니다.")
                
                col1, col2 = st.columns(2)
                with col1:
                    contact_person = st.text_input("담당자 이름*")
                    contact_phone = st.text_input("담당자 연락처*", placeholder="예: 010-1234-5678")
                with col2:
                    contact_email = st.text_input("담당자 이메일*")
                    investment_stage = st.selectbox("투자 희망 단계", [""] + ["Seed", "Pre-A", "Series A", "Series B", "Series C 이상"])

                social_service_sector_options = [""] + ["복지", "보건의료", "고용", "교육", "주거", "문화", "환경", "기타"]
                social_service_sector = st.selectbox("사회서비스 분야*", social_service_sector_options)
                
                other_sector_detail = ""
                if social_service_sector == "기타":
                    other_sector_detail = st.text_input("기타 사회서비스 분야 (구체적으로 명시)*")

                introduction_material_url = st.text_input("기업 소개 자료 URL (선택)")
                reason_for_recommendation = st.text_area("추천 사유*", height=120, placeholder="이 기업을 추천하는 이유를 알려주세요.")
                
                submitted = st.form_submit_button("✅ 추천 완료하기", type="primary", use_container_width=True)

                if submitted:
                    final_social_sector = other_sector_detail if social_service_sector == "기타" else social_service_sector
                    is_valid = True
                    error_messages = []

                    if not company_name.strip(): error_messages.append("기업명을 입력해주세요.")
                    if not contact_person.strip(): error_messages.append("담당자 이름을 입력해주세요.")
                    if not contact_email.strip(): error_messages.append("담당자 이메일을 입력해주세요.")
                    if not contact_phone.strip(): error_messages.append("담당자 연락처를 입력해주세요.")
                    if not social_service_sector: error_messages.append("사회서비스 분야를 선택해주세요.")
                    if social_service_sector == "기타" and not other_sector_detail.strip(): error_messages.append("기타 사회서비스 분야를 구체적으로 입력해주세요.")
                    if not reason_for_recommendation.strip(): error_messages.append("추천 사유를 입력해주세요.")
                    
                    if error_messages:
                        for msg in error_messages: st.error(msg)
                        is_valid = False
                    
                    if is_valid:
                        recommendation_data = {
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "company_name": company_name.strip(), "contact_person": contact_person.strip(),
                            "contact_email": contact_email.strip(), "contact_phone": contact_phone.strip(),
                            "social_sector": final_social_sector.strip(), "investment_stage": investment_stage,
                            "intro_url": introduction_material_url.strip(), "recommendation_reason": reason_for_recommendation.strip(),
                            "raw_searched_name": normalize_company_name(company_name)
                        }
                        
                        if add_recommendation(recommendation_data):
                            st.success(f"'{company_name}' 기업 추천이 완료되었습니다. 소중한 정보 감사합니다! ✨")
                            st.balloons()
                            # 성공 후 상태 초기화
                            st.session_state.show_new_form = False 
                            st.session_state.searched_company_for_form = ""
                            # 폼 초기화를 위해 rerun (선택적, form의 clear_on_submit=True와 유사 효과)
                            st.rerun() 
                        else:
                            st.error(f"'{company_name}' 기업은 이미 추천되었거나 저장 중 문제가 발생했습니다. 다시 확인해주세요.")
    
    st.divider()
    # --- 최근 추천 목록 ---
    st.header("최근 추천된 기업 목록")
    with st.container(border=True): # 카드 UI
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT timestamp, company_name, social_sector, contact_person FROM recommended_companies ORDER BY id DESC LIMIT 5")
            recs = cursor.fetchall()
            if recs:
                for i, rec in enumerate(recs):
                    col1, col2 = st.columns([3, 7]) # 비율 조정
                    with col1:
                        st.caption(f"`{rec[0]}`")
                    with col2:
                        st.markdown(f"**{rec[1]}** ({rec[2]}) - 담당: {rec[3]}")
                    if i < len(recs) - 1: st.markdown("---") # 항목 간 얇은 구분선
            else:
                st.info("아직 추천된 기업이 없습니다. 첫 번째 추천을 해주세요! 🚀")
        except sqlite3.Error as e:
            st.error(f"DB 조회 중 오류 발생: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    main()