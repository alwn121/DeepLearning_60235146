.PHONY: setup run log-sample recommend weekly test

setup:
	pip install -r requirements.txt

run:
	python diet_bot.py summary --date $(shell python -c "import datetime; print(datetime.date.today().isoformat())")

log-sample:
	python diet_bot.py log --text "계란 2개, 토마토 100g, 닭가슴살 150g"

recommend:
	python diet_bot.py recommend --meals 3 --deficit 0.15

weekly:
	python diet_bot.py weekly-report --end $(shell python -c "import datetime; print(datetime.date.today().isoformat())")

test:
	pytest -q

