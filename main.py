import csv
import os # [추가] 파일 경로를 찾기 위한 도구
import random # [추가] 랜덤 기능을 위해 필요한 도구
from flask import Flask, render_template, request, send_from_directory # [추가] send_from_directory
from thefuzz import fuzz 

app = Flask(__name__)

# [추가] 프론트엔드에서도 필터링을 적용하기 위한 키워드 목록
KEYWORDS_FILTER = ["수어", "수화", "Sign Language"]

# 1. CSV 파일에서 영상 목록 읽어오기
video_list = []
try:
    with open('videos.csv', 'r', encoding='utf-8-sig') as file:
        reader = csv.reader(file)
        header = next(reader) 
        for row in reader:
            if len(row) >= 3:
                title = row[0]

                # [수정] 키워드 필터링 로직 (데이터 읽을 때 1차 검증)
                # 제목에 키워드가 포함되어 있는지 확인
                is_relevant = any(keyword.lower() in title.lower() for keyword in KEYWORDS_FILTER)

                # 키워드가 있는 영상만 리스트에 담음
                if is_relevant:
                    video_list.append({
                        'title': title, 
                        'video_id': row[1], 
                        'published_at': row[2]
                    })
except FileNotFoundError:
    print("[오류] 'videos.csv' 파일이 없습니다.")

@app.route('/')
def index():
    query = request.args.get('query', '')
    # 검색어가 있으면 '정확도순', 없으면 '최신순'을 기본값으로 설정
    default_sort = 'accuracy' if query else 'latest'
    sort_by = request.args.get('sort', default_sort)

    display_videos = []

    if query:
        # [검색 시 로직] - 가중치 계산
        search_results = []
        query_lower = query.lower().strip()

        for video in video_list:
            title = video['title']
            title_lower = title.lower().strip()
            score = 0

            if query_lower == title_lower:
                score = 300 
            elif title_lower.startswith(query_lower):
                score = 200
            elif query_lower in title_lower:
                score = 100 - len(title_lower)
            else:
                similarity = fuzz.partial_ratio(query_lower, title_lower)
                if similarity >= 90:
                    score = similarity - 20

            if score > 0:
                video['score'] = score
                search_results.append(video)

        display_videos = search_results

        # --- [수정된 정렬 로직] ---
        if sort_by == 'latest':
            # 사용자가 '최신순'을 클릭했다면: 점수 무시하고 날짜만 기준으로 정렬
            display_videos.sort(key=lambda x: x['published_at'], reverse=True)
        else:
            # 기본값(정확도순)일 때: 점수(1순위) + 날짜(2순위)로 정렬
            display_videos.sort(key=lambda x: (x.get('score', 0), x['published_at']), reverse=True)
        # -------------------------

    else:
        # [홈 화면 로직] - 기존과 동일
        if 'sort' not in request.args: 
            sample_count = min(len(video_list), 50)
            display_videos = random.sample(video_list, sample_count)
        else:
            display_videos = list(video_list)
            if sort_by == 'latest':
                display_videos.sort(key=lambda x: x['published_at'], reverse=True)
            display_videos = display_videos[:50]

    return render_template('index.html', videos=display_videos, query=query, sort_by=sort_by)


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

# [수정됨] ads.txt 인증 코드를 올바르게 넣은 부분
# 이 코드는 반드시 함수 안에서 return "..." 형태로 작성되어야 합니다.
@app.route('/ads.txt')
def ads_txt():
    return "google.com, pub-6253533406925884, DIRECT, f08c47fec0942fa0"

# [수정됨] sitemap.xml 경로 설정
# render_template 대신 send_from_directory를 사용해 현재 폴더(root)의 파일을 보냅니다.
@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(os.getcwd(), 'sitemap.xml')

# [추가] robots.txt도 같은 원리로 처리 (만약 만드셨다면)
@app.route('/robots.txt')
def robots():
    return "User-agent: *\nAllow: /"



if __name__ == '__main__':
    # Render가 주는 PORT 환경변수를 가져오고, 없으면 5000번 사용
    port = int(os.environ.get("PORT", 5000))
    # 0.0.0.0으로 외부 접속 허용, 동적 포트 할당
    app.run(host="0.0.0.0", port=port)
