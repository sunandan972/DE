"""Natural-language specification parser with optional OpenAI and offline fallback."""
from __future__ import annotations
import json, os, re
from typing import Any
from sympy import symbols, sympify
from sympy.logic.boolalg import And, Or, Not, Xor, Implies, Equivalent

SUPPORTED_OPS = {"AND", "OR", "NOT", "XOR", "IMPLIES", "EQUIVALENT"}

DEMO_SCENARIOS = {
    "Automobile Seatbelt & Ignition Safety (3 inputs)": {
        "description": "The ignition is enabled only when the driver is seated, the seatbelt is fastened, and the brake is pressed.",
        "inputs": [
            {"name":"A","label":"Driver seated","active_high":True},
            {"name":"B","label":"Seatbelt fastened","active_high":True},
            {"name":"C","label":"Brake pressed","active_high":True}],
        "outputs":[{"name":"Y","label":"Ignition enable"}],
        "rules":{"Y":"A AND B AND C"}
    },
    "Chemical Tank Overflow & Temperature Alarm (4 inputs)": {
        "description": "Trigger the alarm if the tank is full and the inlet valve is open, or if temperature is high and the cooling system has failed.",
        "inputs":[
            {"name":"A","label":"Tank full","active_high":True},
            {"name":"B","label":"Inlet valve open","active_high":True},
            {"name":"C","label":"Temperature high","active_high":True},
            {"name":"D","label":"Cooling failed","active_high":True}],
        "outputs":[{"name":"Y","label":"Safety alarm"}],
        "rules":{"Y":"(A AND B) OR (C AND D)"}
    },
    "Three-person Majority with Override (4 inputs)": {
        "description": "The decision is approved when at least two of three voters vote yes, or when the authorized override switch is active.",
        "inputs":[
            {"name":"A","label":"Voter 1 yes","active_high":True},
            {"name":"B","label":"Voter 2 yes","active_high":True},
            {"name":"C","label":"Voter 3 yes","active_high":True},
            {"name":"D","label":"Authorized override","active_high":True}],
        "outputs":[{"name":"Y","label":"Approved","active_high":True}],
        "rules":{"Y":"(A AND B) OR (A AND C) OR (B AND C) OR D"}
    }
}

def _validate_spec(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise ValueError("Specification must be a JSON object.")
    inputs, outputs, rules = spec.get("inputs"), spec.get("outputs"), spec.get("rules")
    if not isinstance(inputs, list) or not 1 <= len(inputs) <= 6:
        raise ValueError("Provide between 1 and 6 input variables.")
    if not isinstance(outputs, list) or not 1 <= len(outputs) <= 4:
        raise ValueError("Provide between 1 and 4 outputs.")
    if not isinstance(rules, dict):
        raise ValueError("Rules must map each output name to a Boolean expression.")
    names = []
    for item in inputs + outputs:
        if not isinstance(item, dict) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", str(item.get("name",""))):
            raise ValueError("Each input/output needs a simple uppercase name such as A or Y.")
        if item["name"] in names:
            raise ValueError(f"Duplicate variable name: {item['name']}")
        names.append(item["name"])
        item.setdefault("label", item["name"])
        item.setdefault("active_high", True)
    in_names = {x["name"] for x in inputs}
    out_names = {x["name"] for x in outputs}
    if set(rules) != out_names:
        raise ValueError("There must be exactly one Boolean rule for each declared output.")
    for out, expr in rules.items():
        if not isinstance(expr, str) or not expr.strip():
            raise ValueError(f"Rule for {out} must be a non-empty string.")
        tokens = set(re.findall(r"\b[A-Z][A-Z0-9_]*\b", expr.upper())) - {"AND", "OR", "NOT", "XOR", "TRUE", "FALSE"}
        unknown = tokens - in_names
        if unknown:
            raise ValueError(f"Rule for {out} references undeclared input(s): {', '.join(sorted(unknown))}")
    spec.setdefault("description", "Boolean decision specification")
    return spec

def parse_with_openai(text: str, api_key: str | None = None, model: str = "gpt-4o-mini") -> dict[str, Any]:
    """Ask an LLM for a schema; the result is still validated and truth-table checked."""
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    from openai import OpenAI
    client = OpenAI(api_key=key)
    schema = {
        "type":"object", "additionalProperties":False,
        "properties":{
            "description":{"type":"string"},
            "inputs":{"type":"array","items":{"type":"object","additionalProperties":False,"properties":{
                "name":{"type":"string"},"label":{"type":"string"},"active_high":{"type":"boolean"}},
                "required":["name","label","active_high"]}},
            "outputs":{"type":"array","items":{"type":"object","additionalProperties":False,"properties":{
                "name":{"type":"string"},"label":{"type":"string"},"active_high":{"type":"boolean"}},
                "required":["name","label","active_high"]}},
            "rules":{"type":"object","additionalProperties":{"type":"string"}}
        }, "required":["description","inputs","outputs","rules"]
    }
    response = client.chat.completions.create(
        model=model, temperature=0,
        messages=[
            {"role":"system","content":(
                "Convert a natural-language digital logic requirement into a Boolean specification. "
                "Use 1-6 input variables named A,B,C,D,E,F in order and output names Y,Z,... . "
                "Rules must be expressions using only declared input names, parentheses, AND, OR, NOT, XOR. "
                "Use explicit assumptions and put them in description. Do not invent inputs that are not needed. "
                "If the requirement is ambiguous, state assumptions in description. Never claim hardware safety certification."
            )},
            {"role":"user","content":text}],
        response_format={"type":"json_schema","json_schema":{"name":"logic_spec","strict":True,"schema":schema}}
    )
    return _validate_spec(json.loads(response.choices[0].message.content))

def parse_natural_language(text: str, use_llm: bool = False, api_key: str | None = None) -> dict[str, Any]:
    """Parse text with the configured LLM; otherwise support deterministic known-pattern fallback."""
    text = (text or "").strip()
    if not text:
        raise ValueError("Enter a natural-language requirement.")
    if use_llm:
        return parse_with_openai(text, api_key)
    lower = text.lower()
    # A clear, deterministic fallback for common alarm/enable phrasing.
    rules = []
    candidates = [
        (r"seatbelt.*(fastened|buckled).*ignition|ignition.*seatbelt", DEMO_SCENARIOS["Automobile Seatbelt & Ignition Safety (3 inputs)"]),
        (r"tank.*(overflow|full).*temperature|chemical tank", DEMO_SCENARIOS["Chemical Tank Overflow & Temperature Alarm (4 inputs)"]),
        (r"majority.*vot|three.person.*vot|three-person majority", DEMO_SCENARIOS["Three-person Majority with Override (4 inputs)"]),
        (r"vault.*alarm|key.*code.*motion|motion sensor.*night mode", {
            "description":"Alarm when key and code are both valid, or motion is detected while night mode is active.",
            "inputs":[{"name":"A","label":"Key valid","active_high":True},{"name":"B","label":"Code correct","active_high":True},{"name":"C","label":"Motion detected","active_high":True},{"name":"D","label":"Night mode active","active_high":True}],
            "outputs":[{"name":"Y","label":"Alarm siren","active_high":True}],
            "rules":{"Y":"(A AND B) OR (C AND D)"}})
    ]
    for pattern, spec in candidates:
        if re.search(pattern, lower):
            return _validate_spec(json.loads(json.dumps(spec)))
    # Explicit expression shortcut: "Y = A AND B OR NOT C" plus input names inferred from expression.
    match = re.search(r"(?:y|output)\s*=\s*(.+)", text, re.I)
    if match:
        expr = match.group(1).strip().upper().replace("&&"," AND ").replace("||"," OR ")
        expr = re.sub(r"(?<![A-Z0-9_])!([A-F])", r"NOT \1", expr)
        vars_found = sorted(set(re.findall(r"\b[A-F]\b", expr)), key="ABCDEF".index)
        if vars_found:
            spec = {"description":"Parsed Boolean expression supplied by user.",
                    "inputs":[{"name":v,"label":v,"active_high":True} for v in vars_found],
                    "outputs":[{"name":"Y","label":"Output Y","active_high":True}],
                    "rules":{"Y":expr}}
            return _validate_spec(spec)
    raise ValueError(
        "Offline fallback could not confidently map this scenario. Select a demo, provide an expression "
        "such as 'Y = (A AND B) OR NOT C', or enable the OpenAI parser with OPENAI_API_KEY."
    )

def expression_to_sympy(expr: str, variables: list[str]):
    """Parse safe Boolean syntax; accepts AND/OR/NOT, &, |, ~, apostrophe complements."""
    s = expr.strip().upper()
    s = re.sub(r"([A-F])\s*'", r"~\1", s)
    s = re.sub(r"\bAND\b", "&", s)
    s = re.sub(r"\bOR\b", "|", s)
    s = re.sub(r"\bNOT\s+([A-F])\b", r"~\1", s)
    s = re.sub(r"\bTRUE\b", "1", s)
    s = re.sub(r"\bFALSE\b", "0", s)
    # Reject anything except a small safe grammar.
    if not re.fullmatch(r"[\sA-F0-9&|~^()]+", s):
        raise ValueError("Unsupported expression syntax. Use variable names and AND/OR/NOT, &, |, ~, ^.")
    syms = symbols(" ".join(variables))
    if len(variables) == 1:
        syms = (syms,)
    env = {name: sym for name, sym in zip(variables, syms)}
    try:
        parsed = sympify(s, locals=env, evaluate=True)
    except Exception as exc:
        raise ValueError(f"Could not parse Boolean rule: {expr}") from exc
    if parsed.free_symbols - set(syms):
        raise ValueError("Expression contains an unknown variable.")
    return parsed
