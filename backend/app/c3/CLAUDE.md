# Rules for C3 work
- I am Gayantha, a beginner Python developer, owner of C3 only
  (Adaptive Multi-Objective Irrigation Optimisation Engine).
- Only edit backend/app/c3/, backend/tests/c3/, backend/c3_data/ and
  backend/requirements-c3.txt. Never edit shared files or other
  members' folders.
- Simple, readable Python with comments and type hints. Small functions.
- Every function gets a pytest test. Run "python -m pytest tests/c3"
  from backend/ before saying a task is done.
- Every agronomic or physical constant needs a comment naming its source
  (e.g. "FAO-56 Table 12"). If no source is known, stop and ask me.
- Never invent data, results or accuracy claims. Synthetic data must have
  "synthetic" in its file name and be described as synthetic.
- Put units in variable names or docstrings (mm/day, m3/m3, degC, MJ/m2/day).
- Do not commit or push unless I say so.
