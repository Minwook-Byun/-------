import streamlit as st
import sqlite3
import datetime
import re
import os

# --- DB 설정 ---
DB_NAME = "vc_pool_data.db"

def init_db():
    """데이터베이스를 초기화하고 필요한 테이블을 생성합니다."""
    # 앱 파일과 같은 디렉토리에 DB 파일 생성
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    # db_path = os.path.join(SCRIPT_DIR, DB_NAME)
    # conn = sqlite3.connect(db_path)
    
    conn = sqlite3.connect(DB_NAME) # 현재 작업 디렉토리에 DB 파일 생성/연결
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
    
    # 초기 방문자 수 설정 (없을 경우)
    cursor.execute("INSERT OR IGNORE INTO app_metrics (metric_name, value) VALUES ('visit_count', 0)")
    conn.commit()
    conn.close()

def add_recommendation(data):
    """추천 기업 정보를 데이터베이스에 추가합니다."""
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
        return True # 성공적으로 추가됨
    except sqlite3.IntegrityError: # UNIQUE constraint failed (raw_searched_name)
        return False # 이미 추천된 기업 (중복)
    finally:
        conn.close()

def get_visit_count():
    """현재 방문자 수를 데이터베이스에서 가져옵니다."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM app_metrics WHERE metric_name = 'visit_count'")
    count_row = cursor.fetchone()
    conn.close()
    return count_row[0] if count_row else 0

def increment_visit_count():
    """방문자 수를 1 증가시킵니다."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE app_metrics SET value = value + 1 WHERE metric_name = 'visit_count'")
    conn.commit()
    conn.close()

# --- 기존 참여 기업 리스트 ---
COMPANIES_2023 = [
    "다나씨엠", "씽즈", "에이치투케이", "이너프유", "자라나다", "휴브리스", "딱따구리",
    "스쿨버스", "이모티브", "해낸다컴퍼니", "나눔비타민", "도구공간", "윙윙", "로카101",
    "유알테크", "어뮤즈", "리브라이블리", "메디플렉서스", "복지유니온", "블루레오",
    "언어발전소", "원더풀플랫폼", "이모코그", "임팩터스", "포페런츠", "픽셀로",
    "쉘위파트너스", "웰더스스마트케어", "토끼와두꺼비", "안드레이아", "돌봄드림",
    "라이트하우스", "소리를보는통로", "알밤", "이디피랩", "코액터스",
    "파라스타엔터테인먼트", "하루하루움직임연구소", "휴카시스템", "기억산책", "세지아",
    "지아소프트", "마이베네핏", "레드슬리퍼스", "베이띵스", "우리동네히어로",
    "에스엠플래닛", "엠디스퀘어", "좋은운동장", "케이알지그룹", "핀휠", "홈체크",
    "그레이스케일", "다이노즈", "효돌"
]

COMPANIES_2024 = [
    "아이앤나", "카티어스", "모바일닥터", "디에이블", "그리니쉬", "디에이엘컴퍼니",
    "업드림코리아", "폴라이크", "키위스튜디오", "솔리브벤처스", "디엔엑스", "뷰니브랩",
    "아이윙티브이", "올디너리매직", "크리모", "마인드허브", "비바라비다", "솔닥",
    "야타브엔터", "엑스퍼트아이앤씨", "이엑스헬스케어", "인졀미", "인핸드플러스",
    "캥스터즈", "키뮤", "뉴힐링라이프재활운동센터", "디아앤코", "시공간", "힐링하트",
    "푸른나이", "내이루리", "스프링어게인", "로완", "빅디퍼", "큐라코", "코드블라썸",
    "투엔티닷", "고이장례연구소", "제이씨에프테크놀러지", "고수플러스", "마마품",
    "애스크밀리언스", "온전", "왕왕", "케어누리", "특수청소에버그린", "골든아워",
    "네오에이블", "정션메드", "딥비전스", "피지오", "엠디에스코트", "와우키키",
    "타이렐", "투아트", "잇마플", "뉴로아시스", "마인드풀커넥트", "사랑과선행",
    "인비저블컴퍼니", "제이엘스탠다드", "하이"
]

def normalize_company_name(name):
    """기업명에서 (주), 주식회사, 모든 공백을 제거하고 소문자로 변환합니다."""
    if not name:
        return ""
    name = name.lower() # 소문자로 변환
    name = name.replace("(주)", "").replace("주식회사", "") # 관련 문자열 제거
    name = re.sub(r'\s+', '', name) # 모든 종류의 공백 제거
    return name

# --- Streamlit 앱 UI 구성 ---
def main():
    # 페이지 기본 설정
    st.set_page_config(page_title="투자 교류회 모집 Pool", page_icon="💼", layout="wide")

    # DB 초기화 (앱 실행 시 한 번)
    init_db()

    # 방문자 수 트래킹 (세션 당 한 번만 증가)
    if 'visited_this_session' not in st.session_state:
        increment_visit_count()
        st.session_state.visited_this_session = True
    
    current_visit_count = get_visit_count()

    # 제목 및 설명
    st.title("💼 사회서비스 투자 교류회 모집 Pool")
    st.caption(f"현재까지 **{current_visit_count}** 명의 사내기업가(세션 기준)분들이 방문해주셨어요! 🎉")
    st.markdown("---") # 구분선

    # 섹션 1: 기존 참여 기업 검색
    # Streamlit 1.29.0 이상에서는 border=True 사용 가능
    try:
        search_container = st.container(border=True) 
    except TypeError: # 이전 버전의 Streamlit에서는 border 인자 없음
        search_container = st.container()
        search_container.markdown("<hr style='margin-top:0.5em; margin-bottom:0.5em;'>", unsafe_allow_html=True)


    with search_container:
        st.subheader("🔍 1. 기존 참여 기업 검색")
        searched_company_name_input = st.text_input(
            "추천하려는 기업명을 입력해주세요:",
            placeholder="(주), 띄어쓰기는 제외하고 입력 부탁드립니다.",
            key="search_company_input"
        )

        # 세션 상태 초기화 (필요한 경우)
        if 'show_new_form' not in st.session_state:
            st.session_state.show_new_form = False
        if 'searched_company_for_form' not in st.session_state:
            st.session_state.searched_company_for_form = ""

        if st.button("검색하기", key="search_button", type="primary"):
            if searched_company_name_input:
                st.session_state.searched_company_for_form = searched_company_name_input # 원본 검색어 저장
                normalized_search_term = normalize_company_name(searched_company_name_input)

                # 2023년 리스트에서 검색
                found_2023 = False
                original_found_name_2023 = ""
                for company in COMPANIES_2023:
                    if normalize_company_name(company) == normalized_search_term:
                        found_2023 = True
                        original_found_name_2023 = company
                        break
                
                # 2024년 리스트에서 검색
                found_2024 = False
                original_found_name_2024 = ""
                if not found_2023: # 2023년에 없으면 2024년 검색
                    for company in COMPANIES_2024:
                        if normalize_company_name(company) == normalized_search_term:
                            found_2024 = True
                            original_found_name_2024 = company
                            break
                
                if found_2023:
                    st.warning(f"아쉽게도 '{original_found_name_2023}' 기업은 2023년에 투자교류회 참여 기업으로 본 사업 참여는 어렵습니다. 그렇지만 추천을 주셔서 감사드려용 :-)")
                    st.session_state.show_new_form = False
                elif found_2024:
                    st.warning(f"아쉽게도 '{original_found_name_2024}' 기업은 2024년에 투자교류회 참여 기업으로 본 사업 참여는 어렵습니다. 그렇지만 추천을 주셔서 감사드려용 :-)")
                    st.session_state.show_new_form = False
                else:
                    # SQLite DB에서 중복 추천인지 확인 (정규화된 이름 기준)
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("SELECT company_name FROM recommended_companies WHERE raw_searched_name = ?", (normalized_search_term,))
                    existing_recommendation = cursor.fetchone()
                    conn.close()

                    if existing_recommendation:
                        st.info(f"'{searched_company_name_input}' 기업은 이미 '{existing_recommendation[0]}' (으)로 추천 목록에 존재합니다. 확인 감사합니다. 😊")
                        st.session_state.show_new_form = False
                    else:
                        st.success(f"'{searched_company_name_input}' 기업은 신규 추천 대상입니다! 아래에 정보를 입력해주세요. 👇")
                        st.session_state.show_new_form = True
            else:
                st.error("기업명을 입력해주세요!")
                st.session_state.show_new_form = False
    
    st.write("") # 여백 추가

    # 섹션 2: 신규 기업 추천 등록
    if st.session_state.show_new_form:
        with st.expander("📝 2. 신규 기업 추천 등록 (클릭하여 펼치기)", expanded=True):
            # Streamlit 1.29.0 이상에서는 border=True 사용 가능
            try:
                form_container = st.form("new_company_form", clear_on_submit=True, border=True)
            except TypeError:
                form_container = st.form("new_company_form", clear_on_submit=True)
                form_container.markdown("<hr style='margin-top:0.5em; margin-bottom:0.5em;'>", unsafe_allow_html=True)

            with form_container:
                st.markdown("##### 새로운 투자 검토 기업 정보를 입력해주세요.")
                
                company_name = st.text_input("기업명*", value=st.session_state.searched_company_for_form, help="검색한 기업명이 자동으로 입력됩니다.")
                
                col1, col2 = st.columns(2)
                with col1:
                    contact_person = st.text_input("담당자 이름*")
                    contact_phone = st.text_input("담당자 연락처* (예: 010-1234-5678)")
                with col2:
                    contact_email = st.text_input("담당자 이메일*")
                    investment_stage = st.selectbox(
                        "투자 희망 단계",
                        ["", "Seed", "Pre-A", "Series A", "Series B", "Series C 이상"],
                    )

                social_service_sector_options = ["", "복지", "보건의료", "고용", "교육", "주거", "문화", "환경", "기타"]
                social_service_sector = st.selectbox(
                    "사회서비스 분야*",
                    social_service_sector_options,
                    help="복지, 보건의료, 고용, 교육, 주거, 문화, 환경 등"
                )
                other_sector_detail = ""
                if social_service_sector == "기타":
                    other_sector_detail = st.text_input("기타 사회서비스 분야 (구체적으로 명시)*")

                introduction_material_url = st.text_input("기업 소개 자료 URL (선택 사항)")
                reason_for_recommendation = st.text_area("추천 사유 (내부 검토용)*", height=100)
                
                st.markdown("<p style='font-size:0.9em; color:grey;'>*는 필수 입력 항목입니다.</p>", unsafe_allow_html=True)

                submitted = st.form_submit_button("✅ 추천 기업 정보 제출하기")

                if submitted:
                    final_social_sector = other_sector_detail if social_service_sector == "기타" else social_service_sector
                    # 필수 항목 검증
                    required_fields = [company_name, contact_person, contact_email, contact_phone, social_service_sector, reason_for_recommendation]
                    is_valid = True
                    if not all(field.strip() for field in [company_name, contact_person, contact_email, contact_phone, reason_for_recommendation]):
                        st.error("기업명, 담당자 정보, 추천 사유는 필수 입력 항목입니다.")
                        is_valid = False
                    if not social_service_sector:
                         st.error("사회서비스 분야를 선택해주세요.")
                         is_valid = False
                    if social_service_sector == "기타" and not other_sector_detail.strip():
                        st.error("기타 사회서비스 분야를 구체적으로 입력해주세요.")
                        is_valid = False
                    
                    if is_valid:
                        recommendation_data = {
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "company_name": company_name.strip(),
                            "contact_person": contact_person.strip(),
                            "contact_email": contact_email.strip(),
                            "contact_phone": contact_phone.strip(),
                            "social_sector": final_social_sector.strip(),
                            "investment_stage": investment_stage,
                            "intro_url": introduction_material_url.strip(),
                            "recommendation_reason": reason_for_recommendation.strip(),
                            "raw_searched_name": normalize_company_name(company_name) # 중복 체크용
                        }
                        
                        if add_recommendation(recommendation_data):
                            st.success(f"'{company_name}' 기업 정보가 성공적으로 DB에 저장되었습니다. 감사합니다! ✨")
                            st.balloons()
                            st.session_state.show_new_form = False 
                            st.session_state.searched_company_for_form = "" 
                            # st.experimental_rerun() # 필요시 페이지 새로고침 (폼 초기화를 위함)
                        else:
                            st.error(f"'{company_name}' 기업은 이미 추천 목록에 존재하거나 저장 중 오류가 발생했습니다. 확인 후 다시 시도해주세요.")
                            
    st.markdown("---")
    # (선택) 저장된 추천 목록 보기 (관리자용 기능으로 확장 가능)
    with st.expander("최근 추천된 기업 목록 보기 (DB 저장 내용 확인용)"):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT timestamp, company_name, social_sector, contact_person FROM recommended_companies ORDER BY id DESC LIMIT 10")
            recs = cursor.fetchall()
            if recs:
                for rec in recs:
                    st.markdown(f"- `{rec[0]}`: **{rec[1]}** ({rec[2]}) - 담당자: {rec[3]}")
            else:
                st.info("아직 추천된 기업이 없습니다.")
        except sqlite3.Error as e:
            st.error(f"DB 조회 중 오류 발생: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    main()