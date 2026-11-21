install:
	pip install -r requirements.txt

demo:      ## full pipeline on synthetic data (no internet needed)
	python scripts/run_pipeline.py --mode demo --steps all

real:      ## full pipeline on real data (see README for credentials)
	python scripts/run_pipeline.py --mode real --steps all

test:
	pytest -q

dashboard:
	streamlit run app/dashboard.py
