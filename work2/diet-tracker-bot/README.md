# diet-tracker-bot

오프라인 다이어트 식단 기록/추천/리포트 CLI 도구입니다. 한국어 우선, 로컬 SQLite와 CSV/JSON 데이터를 사용합니다.

## 설치

```bash
make setup
```

## 빠른 시작

```bash
# 프로필 확인 (BMR/TDEE/목표/매크로)
python diet_bot.py profile show

# 기록 예시
python diet_bot.py log --text "계란 2개, 토마토 100g, 닭가슴살 150g"

# 일일 요약
python diet_bot.py summary --date $(python -c "import datetime; print(datetime.date.today().isoformat())")

# 추천 식단
python diet_bot.py recommend --meals 3 --deficit 0.15

# 주간 리포트
python diet_bot.py weekly-report --end $(python -c "import datetime; print(datetime.date.today().isoformat())")
```

## 프로필 설정

```bash
python diet_bot.py profile set --gender male --age 27 --height 175 --weight 70 --activity light --target-kcal 1800 --macro "0.4,0.3,0.3"
```

## 데이터 확장

- 식품 추가: `foods add --name "닭가슴살" --kcal 165 --protein 31 --fat 3.6 --carbs 0`
- CSV 가져오기: `foods import-csv data/food_db.csv`
- 동의어 추가: `data/synonyms.json` 편집 후 재실행

## 제한/주의

- 단위 변환은 근사치입니다. (예: 계란 1개=50g, 밥 1공기=210g)
- DB 영양정보는 100g 기준 단순화 값이며 브랜드별 차이가 있습니다.
- 모든 처리는 오프라인에서 수행됩니다.

## 스크린샷

`storage/reports/`에 생성되는 PNG 그래프 예시: `daily_bar_YYYY-MM-DD.png`, `weekly_trend_YYYY-MM-DD.png`

