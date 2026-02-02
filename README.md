# GenAI Output Validator (Pydantic, fail-fast)

**context:**  
> LLMs are probabilistic components. I never trust raw outputs.  
> I enforce a strict contract with Pydantic, with controlled sanitization  
> and fail-fast validation, so the downstream system never breaks.

## Why this exists

LLM outputs are **non-deterministic**. Even with a “good prompt”, they can:
- hallucinate fields or values
- drift in format over time
- return invalid JSON
- produce the wrong types (e.g., `"0,87"` instead of `0.87`)
- add unexpected keys (`debug`, `internal_note`, etc.)

In production, raw LLM outputs can break:
- an API contract
- a database insert
- business logic thresholds

This repo demonstrates a production-minded approach: **strict validation + controlled sanitization + fail-fast rejection**.

---

## What this project does

Given a raw LLM output (a `dict` or a JSON string), the pipeline:

1. **Parses** JSON if needed
2. Applies **controlled sanitization** (mechanical fixes only, traceable)
3. Enforces a **strict Pydantic contract** (`extra="forbid"`)
4. Returns a structured verdict, without crashing the process:

python
{
  "status": "accepted" | "rejected",
  "data"?: FraudPredictionOutput,
  "errors"?: list[str]
}

## Repo structure:

genai-output-validator/

├── src/

│   ├── schemas.py 

│   ├── sanitizer.py 

│   ├── validator.py   

│   └── demo.py     

├── samples/

│   └── bad_outputs.py 

├── tests/

│   ├── conftest.py  

│   └── test_validator.py 

├── README.md

└── PROTOCOL.md

## How to run

1) Setup
python -m venv .venv


- Windows PowerShell:
"" .\.venv\Scripts\Activate.ps1 ""

- Linux/macOS:
"" source .venv/bin/activate ""


- "pip install -r requirements.txt"

2) Demo (never crashes, exit code 0) 
"python -m src.demo"


You will see accepted vs rejected verdicts for each intentionally bad case.

3) Tests 
"pytest -q"

**Failure catalogue (samples)**

- The repo includes realistic failure modes:

- invalid / non-parseable JSON

- missing required fields

- wrong types ("0,87", "87%")

- invalid labels

- out-of-range probability

- too-short reason

- invalid model_version

- unexpected fields (debug)

- invalid timestamps (regional formats)

- format drift (wrong key names)


## Conceptual FastAPI integration

In a FastAPI endpoint, treat the LLM output as untrusted input:


from fastapi import FastAPI, HTTPException

from src.validator import validate_output

app = FastAPI()

@app.post("/predict")

def predict():

    raw_llm_output = call_llm_somehow()  # dict or JSON string
    
    verdict = validate_output(raw_llm_output)

    if verdict["status"] == "rejected":
    
        raise HTTPException(status_code=422, detail=verdict["errors"])

    model = verdict["data"]
    
    return model.model_dump()
    
