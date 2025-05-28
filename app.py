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
    # 추천 기업 저장 테이블
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
    # 방문자 수 트래킹 테이블
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

def get_all_recommendations():
    """DB에서 모든 추천 기업 목록을 가져옵니다 (최신순)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 필요한 모든 컬럼을 명시적으로 선택
    cursor.execute("""
        SELECT id, timestamp, company_name, contact_person, contact_email, 
               contact_phone, social_sector, investment_stage, intro_url, 
               recommendation_reason, raw_searched_name 
        FROM recommended_companies 
        ORDER BY id DESC
    """)
    recommendations = cursor.fetchall() # 튜플의 리스트로 반환
    conn.close()
    return recommendations

# --- 기존 참여 기업 리스트 ---
COMPANIES_2023 = [
    "다나씨엠", "씽즈", "에이치투케이", "이너프유", "자라나다", "휴브리스", "딱따구리", "스쿨버스", "이모티브", "해낸다컴퍼니", "나눔비타민", "도구공간", "윙윙", "로카101", "유알테크", "어뮤즈", "리브라이블리", "메디플렉서스", "복지유니온", "블루레오", "언어발전소", "원더풀플랫폼", "이모코그", "임팩터스", "포페런츠", "픽셀로", "쉘위파트너스", "웰더스스마트케어", "토끼와두꺼비", "안드레이아", "돌봄드림", "라이트하우스", "소리를보는통로", "알밤", "이디피랩", "코액터스", "파라스타엔터테인먼트", "하루하루움직임연구소", "휴카시스템", "기억산책", "세지아", "지아소프트", "마이베네핏", "레드슬리퍼스", "베이띵스", "우리동네히어로", "에스엠플래닛", "엠디스퀘어", "좋은운동장", "케이알지그룹", "핀휠", "홈체크", "그레이스케일", "다이노즈", "효돌"
]
COMPANIES_2024 = [
    "아이앤나", "카티어스", "모바일닥터", "디에이블", "그리니쉬", "디에이엘컴퍼니", "업드림코리아", "폴라이크", "키위스튜디오", "솔리브벤처스", "디엔엑스", "뷰니브랩", "아이윙티브이", "올디너리매직", "크리모", "마인드허브", "비바라비다", "솔닥", "야타브엔터", "엑스퍼트아이앤씨", "이엑스헬스케어", "인졀미", "인핸드플러스", "캥스터즈", "키뮤", "뉴힐링라이프재활운동센터", "디아앤코", "시공간", "힐링하트", "푸른나이", "내이루리", "스프링어게인", "로완", "빅디퍼", "큐라코", "코드블라썸", "투엔티닷", "고이장례연구소", "제이씨에프테크놀러지", "고수플러스", "마마품", "애스크밀리언스", "온전", "왕왕", "케어누리", "특수청소에버그린", "골든아워", "네오에이블", "정션메드", "딥비전스", "피지오", "엠디에스코트", "와우키키", "타이렐", "투아트", "잇마플", "뉴로아시스", "마인드풀커넥트", "사랑과선행", "인비저블컴퍼니", "제이엘스탠다드", "하이"
]

# --- VC 제공 기업 리스트 (사용자 제공) ---
VC_PROVIDED_NAMES = [
    "유니크굿컴퍼니","에이트테크","루트에너지","에이트스튜디오","콘스텍츠",
    "지오그리드","어글리랩","널위한문화예술","플릭던","에스엠디솔루션",
    "티알","배럴아이","테스트웍스","스포잇","잼잼테라퓨릭스","케이비자",
    "엔바이오셀","널핏","펴냐니","레몬트리","공도","공감만세","저크","마들렌메모리"
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

    # Custom CSS (이전과 동일)
    st.markdown("""
        <style>
            .stApp { background-color: #F0F2F5; }
            .main .block-container { padding-top: 2rem; padding-bottom: 2rem; padding-left: 3rem; padding-right: 3rem; }
            .stButton>button { border-radius: 8px; }
            .stTextInput input, .stTextArea textarea, .stSelectbox select { border-radius: 8px; }
            h1 { font-size: 2.2em; font-weight: 600; color: #1A202C; }
            h2 { /* 섹션 제목 - st.header 사용 */
                font-size: 1.6em; font-weight: 600; color: #2D3748; 
                border-bottom: 2px solid #E2E8F0; padding-bottom: 0.3em;
                margin-top: 2em; margin-bottom: 1em;
            } 
            .stAlert { border-radius: 8px; }
            .list-item {
                padding: 0.5rem 0;
                border-bottom: 1px solid #e9ecef;
            }
            .list-item:last-child { border-bottom: none; }
            .company-name { font-weight: 600; color: #333; }
            .company-detail { font-size: 0.9em; color: #555; }
            .vc-list-item { /* VC 제공 리스트 아이템 전용 스타일 */
                padding: 0.4rem 0.8rem;
                margin-bottom: 0.3rem;
                background-color: #ffffff;
                border-left: 3px solid #4A90E2; /* 파란색 강조선 */
                border-radius: 4px;
            }
            .info-block { /* 긴 안내문구를 위한 스타일 */
                padding: 1.5rem; 
                background-color: #ffffff; /* 하얀 배경 */
                border-radius: 8px; 
                /* box-shadow: 0 2px 4px rgba(0,0,0,0.05); */ /* st.container(border=True)가 이미 그림자 포함할 수 있음 */
                line-height: 1.7; /* 줄 간격 개선 */
                font-size: 0.95em; /* 기본 텍스트보다 약간 크게 */
            }
            .info-block strong { /* 볼드체 강조 */
                color: #0072C6; /* 포인트 색상 (예: 파란색 계열) */
            }
        </style>
    """, unsafe_allow_html=True)

    init_db() # DB 초기화 (이전과 동일)

    # 방문자 수 트래킹 (이전과 동일)
    if 'visited_this_session' not in st.session_state:
        increment_visit_count()
        st.session_state.visited_this_session = True
    current_visit_count = get_visit_count()

    # --- 페이지 제목 ---
    st.title("🌱 사회서비스 투자기업 추천")
    
    # --- 긴 안내 문구 섹션 ---
    # st.caption(f"좋은 기업을 추천해주세요! 현재까지 {current_visit_count}번의 추천 세션이 있었어요.") # 이 위치에서 제거 또는 변경
    
    intro_text = """
보건복지부, 중앙사회서비스원, 그리고 엠와이소셜컴퍼니(MYSC)가 함께 하는 2025 사회서비스 투자 교류회는 사회서비스 분야의 혁신 기업들이 투자 유치 기회를 확대하고, 투자자 및 유관기관과의 긴밀한 네트워킹을 통해 실질적인 성장을 도모할 수 있도록 마련된 연결의 장입니다. 
다양한 사회서비스 기업을 발굴하고 임팩트 투자 연계를 통해 기업의 스케일업을 지원하며, 궁극적으로 국민 모두에게 고품질의 사회서비스가 제공될 수 있는 건강한 생태계 조성을 목표로 합니다. 
<br><br>
투자 교류회는 기업 IR 발표 및 라운드테이블 미팅, 제품 및 서비스 홍보 테이블 운영 등 다채로운 프로그램으로 구성되며, <strong>25년 1회 교류회는 국민의 삶의 질을 높이는 AI 사회서비스를 주제</strong>로 AI 기술을 활용하여 사회서비스의 효율성과 접근성을 혁신하는 기업을 위한 투자 교류의 장입니다. 
<strong> 투자 유치를 위해 VC 밋업/ 기관과의 OI를 위한 밋업이 필요한 기업을 추천 부탁드립니다. </strong> 
<br><br><hr style='border-top: 1px solid #eee; margin-top:1em; margin-bottom:1em;'>
■ 일시: 2025년 6월 25일(수) 13:30 <br> 
■ 주제: 국민의 삶의 질을 높이는 AI 사회서비스<br> 
■ 접수 기간: 6월 11일(금) 18시까지 <br> 
■ 상세 정보: <a href="https://invmeeting.streamlit.app/">링크</a><br>
■ 문의: mwbyun@mysc.co.kr.
"""
    # st.container(border=True)를 사용하여 카드 형태로 표시
    with st.container(border=True):
        st.markdown(f"<div class='info-block'>{intro_text}</div>", unsafe_allow_html=True)

    # 방문자 수 카운트는 다른 곳에 배치하거나, 이 안내문구 아래 작게 표시 가능
    st.caption(f"현재까지 {current_visit_count - 19}건의 방문이 있었어요. ")
    st.divider()

    init_db()

    if 'visited_this_session' not in st.session_state:
        increment_visit_count()
        st.session_state.visited_this_session = True
    current_visit_count = get_visit_count()


    if 'show_new_form' not in st.session_state: st.session_state.show_new_form = False
    if 'searched_company_for_form' not in st.session_state: st.session_state.searched_company_for_form = ""

    # --- 섹션 1: 기업 검색 ---
    st.header("1. 추천할 기업을 검색해주세요")
    with st.container(border=True):
        searched_company_name_input = st.text_input("기업명", placeholder="예: 제미나이 (띄어쓰기, (주) 제외)", key="search_company_input", label_visibility="collapsed")
        if st.button("🔍 기업 검색", key="search_button", type="primary", use_container_width=True):
            # (검색 로직은 이전과 동일)
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
    st.write("")

    # --- 섹션 2: 신규 기업 추천 등록 폼 ---
    if st.session_state.show_new_form:
        st.header("2. 추천 기업 정보 입력")
        with st.container(border=True):
            with st.form("new_company_form", clear_on_submit=False):
                # (폼 내용은 이전과 동일)
                st.markdown("##### 아래 정보를 입력해주세요. (`*` 필수 항목)")
                company_name = st.text_input("기업명*", value=st.session_state.searched_company_for_form)
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
                    is_valid = True; error_messages = []
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
                            st.session_state.show_new_form = False 
                            st.session_state.searched_company_for_form = ""
                            st.rerun() 
                        else:
                            st.error(f"'{company_name}' 기업은 이미 추천되었거나 저장 중 문제가 발생했습니다.")
    st.divider()

    # --- 섹션 3: VC 제공 주요 검토 리스트 ---
    st.header("🌟 지금까지 추천/Pooling된 기업입니다!") # 헤더 텍스트 변경
    with st.container(border=True):
        if VC_PROVIDED_NAMES:
            st.markdown("아래 기업들은 운영진에 의해서 Pooling된 기업들입니다. 참고 부탁드려용!")
            cols = st.columns(3) # 3열로 표시 (또는 2열, 4열 등 조절 가능)
            for i, company_name in enumerate(VC_PROVIDED_NAMES):
                with cols[i % 3]: # 열에 번갈아 가며 표시
                    st.markdown(f"""
                        <div class="vc-list-item">
                            <span class="company-name">{company_name}</span>
                        </div>
                    """, unsafe_allow_html=True)
            if len(VC_PROVIDED_NAMES) % 3 != 0 : # 홀수개일 경우 마지막 줄 채우기
                 for _ in range(3 - (len(VC_PROVIDED_NAMES) % 3)):
                      with cols[ (len(VC_PROVIDED_NAMES) % 3) + _]: # 빈칸 채우기
                           st.write("") # 빈 컨텐츠로 레이아웃 유지
        else:
            st.info("현재 VC 제공 주요 검토 대상 기업 리스트가 없습니다.")
    st.write("")

    # --- 섹션 4: 구성원 추천 기업 현황 ---
    st.header("👥 구성원 추천 기업 현황") # 헤더 텍스트 변경
    with st.container(border=True):
        all_recs = get_all_recommendations()
        if all_recs:
            st.caption(f"총 {len(all_recs)}개 기업이 추천되었습니다. (최근 10개 표시)")
            # 컬럼: 타임스탬프(일자), 기업명, 분야, 추천인(또는 담당자), 추천사유 요약
            # rec 튜플 인덱스: 0:id, 1:timestamp, 2:company_name, 3:contact_person, 4:contact_email, 
            #                 5:contact_phone, 6:social_sector, 7:investment_stage, 8:intro_url, 
            #                 9:recommendation_reason, 10:raw_searched_name
            for rec in all_recs[:10]: # 최근 10개
                rec_timestamp = rec[1]
                rec_company_name = rec[2]
                rec_social_sector = rec[6]
                rec_contact_person = rec[3] 
                rec_reason = rec[9]

                st.markdown(f"""
                    <div class="list-item">
                        <div><span class="company-name">{rec_company_name}</span> <span style="font-size:0.9em; color:#777;">({rec_social_sector})</span></div>
                        <div class="company-detail">추천일: {rec_timestamp.split()[0]} | 추천인(담당): {rec_contact_person}</div>
                        <div class="company-detail" style="margin-top:0.2rem;"><em>사유: {rec_reason[:70] + '...' if len(rec_reason) > 70 else rec_reason}</em></div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("아직 추천된 기업이 없습니다. 첫 번째 추천을 통해 목록을 채워주세요! 🚀")

if __name__ == "__main__":
    main()