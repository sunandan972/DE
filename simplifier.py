"""Exact Boolean minimization utilities for 4–6 variable functions.

Uses Quine–McCluskey prime implicant generation and Petrick's method for
minimum-cost cover selection. Variable order is most-significant to least-
significant: A, B, C, D, E, F.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
import re
from typing import Iterable, Sequence
import sympy as sp
from sympy.logic.boolalg import And, Or, Not, Xor, Equivalent, Implies, Boolean

VARIABLES = tuple(sp.symbols("A B C D E F"))

@dataclass(frozen=True)
class Implicant:
    pattern: str                 # e.g. 10-1
    covered: frozenset[int]
    @property
    def literals(self) -> int:
        return self.pattern.count("0") + self.pattern.count("1")

@dataclass
class MinimizationResult:
    variables: tuple[str, ...]
    on_set: tuple[int, ...]
    dont_cares: tuple[int, ...]
    prime_implicants: tuple[Implicant, ...]
    selected_implicants: tuple[Implicant, ...]
    expression: str
    form: str
    all_minimum_covers: tuple[tuple[Implicant, ...], ...]


def _validate_sets(n: int, on_set: Iterable[int], dont_cares: Iterable[int]) -> tuple[tuple[int,...], tuple[int,...]]:
    limit = 1 << n
    on = tuple(sorted(set(int(x) for x in on_set)))
    dc = tuple(sorted(set(int(x) for x in dont_cares)))
    if any(x < 0 or x >= limit for x in on + dc):
        raise ValueError(f"Minterms must be in the range 0–{limit-1} for {n} variables.")
    if set(on) & set(dc):
        raise ValueError("A minterm cannot be both an ON-set minterm and a don't-care.")
    return on, dc


def _combine_patterns(a: str, b: str) -> str | None:
    diff = 0
    out = []
    for x, y in zip(a, b):
        if x == y:
            out.append(x)
        elif x != "-" and y != "-":
            diff += 1
            out.append("-")
        else:
            return None
    return "".join(out) if diff == 1 else None


def _pattern_covers(pattern: str, value: int) -> bool:
    bits = format(value, f"0{len(pattern)}b")
    return all(p == "-" or p == b for p, b in zip(pattern, bits))


def _qm_prime_implicants(n: int, terms: Sequence[int]) -> tuple[Implicant, ...]:
    current: dict[str, frozenset[int]] = {format(x, f"0{n}b"): frozenset({x}) for x in terms}
    primes: dict[str, frozenset[int]] = {}
    while current:
        used: set[str] = set()
        next_patterns: dict[str, set[int]] = {}
        patterns = list(current)
        for i, a in enumerate(patterns):
            for b in patterns[i + 1:]:
                combined = _combine_patterns(a, b)
                if combined is not None:
                    used.add(a); used.add(b)
                    next_patterns.setdefault(combined, set()).update(current[a] | current[b])
        for pattern, covered in current.items():
            if pattern not in used:
                primes[pattern] = frozenset(set(primes.get(pattern, frozenset())) | set(covered))
        current = {p: frozenset(v) for p, v in next_patterns.items()}
    # Normalize covered minterms to all values represented by each implicant.
    result = []
    for pattern in primes:
        covered = frozenset(x for x in range(1 << n) if _pattern_covers(pattern, x))
        result.append(Implicant(pattern, covered))
    return tuple(sorted(result, key=lambda imp: (imp.literals, imp.pattern)))


def _petrick_cover(primes: Sequence[Implicant], on_set: Sequence[int]) -> tuple[tuple[Implicant,...], ...]:
    if not on_set:
        return (tuple(),)
    candidates = {m: [i for i, p in enumerate(primes) if m in p.covered] for m in on_set}
    if any(not ids for ids in candidates.values()):
        raise RuntimeError("Internal minimizer error: an ON-set minterm is uncovered.")
    # Petrick product represented as sets of prime implicant indices. Absorb supersets.
    products: list[frozenset[int]] = [frozenset()]
    for m in on_set:
        expanded = [p | {i} for p in products for i in candidates[m]]
        unique = sorted(set(expanded), key=lambda s: (len(s), tuple(sorted(s))))
        absorbed: list[frozenset[int]] = []
        for term in unique:
            if not any(old <= term for old in absorbed):
                absorbed.append(term)
        products = absorbed
    def cost(indices: frozenset[int]) -> tuple[int,int,tuple[int,...]]:
        return (sum(primes[i].literals for i in indices), len(indices), tuple(sorted(indices)))
    best_cost = min(cost(p)[:2] for p in products)
    winners = [p for p in products if cost(p)[:2] == best_cost]
    return tuple(tuple(primes[i] for i in sorted(w, key=lambda j: primes[j].pattern)) for w in sorted(winners, key=lambda s: tuple(sorted(s))))


def _term_text(pattern: str, names: Sequence[str], form: str) -> str:
    if form == "SOP":
        bits = [name if bit == "1" else name + "'" for name, bit in zip(names, pattern) if bit != "-"]
        return "".join(bits) if bits else "1"
    # POS maxterm: bit 0 -> uncomplemented variable; bit 1 -> complemented variable.
    bits = [name if bit == "0" else name + "'" for name, bit in zip(names, pattern) if bit != "-"]
    return "(" + "+".join(bits) + ")" if bits else "(0)"


def minimize(on_set: Iterable[int], n_vars: int, dont_cares: Iterable[int] = (), form: str = "SOP", variable_names: Sequence[str] | None = None) -> MinimizationResult:
    if n_vars not in (4, 5, 6):
        raise ValueError("This application supports 4, 5, or 6 variables.")
    form = form.upper()
    if form not in ("SOP", "POS"):
        raise ValueError("form must be 'SOP' or 'POS'.")
    names = tuple(variable_names or ["A", "B", "C", "D", "E", "F"][:n_vars])
    if len(names) != n_vars:
        raise ValueError("The number of variable names must equal n_vars.")
    on, dc = _validate_sets(n_vars, on_set, dont_cares)
    full = set(range(1 << n_vars))
    target = set(on) if form == "SOP" else full - set(on) - set(dc)
    # For POS, minimize the zero-set; don't-cares remain eligible for grouping.
    eligible = sorted(target | set(dc))
    primes = _qm_prime_implicants(n_vars, eligible)
    covers = _petrick_cover(primes, sorted(target))
    selected = covers[0]
    if not on and form == "SOP":
        expression = "0"
    elif len(on) + len(dc) == 1 << n_vars and form == "SOP":
        expression = "1"
    elif form == "POS" and not on:
        expression = "0"
    elif form == "POS" and not target:
        expression = "1"
    else:
        rendered = [_term_text(p.pattern, names, form) for p in selected]
        expression = ("+".join(rendered) if form == "SOP" else "".join(rendered)) or ("0" if form == "SOP" else "1")
    return MinimizationResult(names, on, dc, primes, selected, expression, form, covers)


def parse_minterm_notation(text: str, n_vars: int) -> tuple[list[int], list[int]]:
    """Parse Σm(1,2), m(1,2), d(3,4), and maxterm-style input.

    For maxterm notation ΠM(...), the listed indices are zeros, so the ON set
    is the complement of the listed maxterms (excluding don't-cares).
    """
    source = text.replace("Σ", "SUM").replace("∑", "SUM").replace("Π", "PROD").replace("π", "PROD")
    dc_match = re.search(r"(?:d|dc|don't\s*care)\s*\(([^)]*)\)", source, re.I)
    dc = _parse_int_list(dc_match.group(1)) if dc_match else []
    max_match = re.search(r"(?:PROD\s*M|Π\s*M|maxterms?)\s*\(([^)]*)\)", source, re.I)
    min_match = re.search(r"(?:SUM\s*m|Σ\s*m|minterms?|m)\s*\(([^)]*)\)", source, re.I)
    if max_match:
        zeros = set(_parse_int_list(max_match.group(1)))
        on = sorted(set(range(1 << n_vars)) - zeros - set(dc))
    elif min_match:
        on = _parse_int_list(min_match.group(1))
    else:
        raise ValueError("Could not find minterm/maxterm notation. Try Σm(0,2,5) + d(1,3).")
    return list(_validate_sets(n_vars, on, dc)[0]), list(_validate_sets(n_vars, on, dc)[1])


def _parse_int_list(value: str) -> list[int]:
    value = value.strip()
    if not value:
        return []
    try:
        return [int(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise ValueError(f"Invalid minterm list: {value!r}") from exc


def parse_boolean_expression(text: str, n_vars: int) -> tuple[list[int], list[int], Boolean]:
    """Parse common textbook notation: A' for NOT, + for OR, adjacency for AND."""
    names = ["A", "B", "C", "D", "E", "F"][:n_vars]
    expr = text.strip().replace("¬", "~").replace("·", "&").replace("×", "&").replace("∨", "|").replace("∧", "&")
    # Apostrophes are postfix negation; convert variable/group postfix apostrophes.
    expr = re.sub(r"([A-Fa-f])\s*'+", r"~\1", expr)
    expr = re.sub(r"\bAND\b", "&", expr, flags=re.I)
    expr = re.sub(r"\bOR\b", "|", expr, flags=re.I)
    # Convert textbook + to OR, adjacency to AND, and preserve explicit operators.
    expr = expr.replace("+", "|")
    expr = re.sub(r"(?<=[A-Fa-f0-9_)])\s*(?=[A-Fa-f(~])", "&", expr)
    local = {name: VARIABLES[i] for i, name in enumerate(names)}
    try:
        parsed = sp.sympify(expr, locals=local, evaluate=True)
    except Exception as exc:
        raise ValueError(f"Could not parse Boolean expression: {exc}") from exc
    if not isinstance(parsed, Boolean):
        parsed = sp.sympify(parsed)
    unknown = parsed.free_symbols - set(local.values())
    if unknown:
        raise ValueError(f"Unknown variables: {', '.join(sorted(map(str, unknown)))}")
    on = []
    for idx, bits in enumerate(product((0, 1), repeat=n_vars)):
        assignment = {local[name]: bool(bit) for name, bit in zip(names, bits)}
        if bool(parsed.subs(assignment)):
            on.append(idx)
    return on, [], parsed


def parse_truth_table(rows: Sequence[Sequence[int]], n_vars: int) -> list[int]:
    if len(rows) != 1 << n_vars:
        raise ValueError(f"Truth table must contain exactly {1 << n_vars} rows.")
    on = []
    for idx, row in enumerate(rows):
        if len(row) != n_vars + 1:
            raise ValueError(f"Truth-table row {idx} must have {n_vars} input bits and one output bit.")
        if any(int(bit) not in (0, 1) for bit in row):
            raise ValueError("Truth-table entries must be 0 or 1.")
        expected = tuple(int(x) for x in format(idx, f"0{n_vars}b"))
        if tuple(map(int, row[:-1])) != expected:
            raise ValueError("Truth-table rows must be in ascending binary input order.")
        if int(row[-1]) == 1:
            on.append(idx)
    return on


def expression_to_sympy(expression: str, names: Sequence[str], form: str = "SOP") -> Boolean:
    """Parse this module's rendered SOP/POS notation into a SymPy Boolean object."""
    if expression == "0": return sp.false
    if expression == "1": return sp.true
    local = {name: VARIABLES[i] for i, name in enumerate(names)}
    expr = expression.replace("'", "")
    # Use SOP/POS-specific conversion rather than ambiguous Python adjacency.
    if form.upper() == "SOP":
        terms = []
        for term in expression.split("+"):
            factors = re.findall(r"([A-F])('?)(?:$)?", term)
            if not factors:
                continue
            terms.append(And(*[(Not(local[v]) if neg else local[v]) for v, neg in factors]))
        return Or(*terms) if terms else sp.false
    clauses = re.findall(r"\(([^()]*)\)", expression)
    terms = []
    for clause in clauses:
        factors = re.findall(r"([A-F])('?)(?:$)?", clause)
        terms.append(Or(*[(Not(local[v]) if neg else local[v]) for v, neg in factors]))
    return And(*terms) if terms else sp.true


def truth_table_for_minterms(on_set: Iterable[int], n_vars: int) -> list[tuple[int,...]]:
    on = set(on_set)
    return [tuple(int(x) for x in format(i, f"0{n_vars}b")) + (int(i in on),) for i in range(1 << n_vars)]


def verify_equivalence(original_on: Iterable[int], reduced_expression: str, n_vars: int, form: str = "SOP", variable_names: Sequence[str] | None = None) -> dict:
    names = tuple(variable_names or ["A", "B", "C", "D", "E", "F"][:n_vars])
    original = set(original_on)
    reduced = expression_to_sympy(reduced_expression, names, form)
    mismatches = []
    for idx in range(1 << n_vars):
        bits = tuple(int(x) for x in format(idx, f"0{n_vars}b"))
        assignment = {VARIABLES[i]: bool(bit) for i, bit in enumerate(bits)}
        got = int(bool(reduced.subs(assignment)))
        expected = int(idx in original)
        if got != expected:
            mismatches.append({"index": idx, "inputs": bits, "expected": expected, "actual": got})
    return {"equivalent": not mismatches, "tested_rows": 1 << n_vars, "mismatches": mismatches}


def complexity_metrics(expression: str, form: str, n_vars: int, transistor_model: str = "CMOS basic gates") -> dict:
    """Transparent first-order estimates; excludes fan-out buffers and wiring."""
    if expression in ("0", "1"):
        return {"gate_count": 0, "input_pins": 0, "logic_depth": 0, "transistors_est": 0, "model": transistor_model}
    if form.upper() == "SOP":
        terms = expression.split("+")
        literal_counts = [len(re.findall(r"[A-F]", term)) for term in terms]
        gates = len(terms) + (1 if len(terms) > 1 else 0)
        depth = 2 if len(terms) > 1 and any(literal_counts) else 1
        # CMOS estimate: n-input AND ~= 2n+2, n-input OR ~= 2n+2; inverter ~= 2.
        trans = sum(2*n+2 for n in literal_counts if n > 1) + (2*len(terms)+2 if len(terms)>1 else 0)
        pins = sum(literal_counts) + (len(terms) if len(terms)>1 else 0)
    else:
        clauses = re.findall(r"\(([^()]*)\)", expression)
        literal_counts = [len(re.findall(r"[A-F]", c)) for c in clauses]
        gates = len(clauses) + (1 if len(clauses)>1 else 0)
        depth = 2 if len(clauses)>1 else 1
        trans = sum(2*n+2 for n in literal_counts if n > 1) + (2*len(clauses)+2 if len(clauses)>1 else 0)
        pins = sum(literal_counts) + (len(clauses) if len(clauses)>1 else 0)
    return {"gate_count": gates, "input_pins": pins, "logic_depth": depth, "transistors_est": trans, "model": transistor_model}


def algebraic_steps(expression: str, form: str = "SOP") -> list[str]:
    """Provide a reproducible SymPy simplification trace (not a claim of unique algebraic path)."""
    try:
        # SymPy accepts a conventional expression when operators are explicit.
        normalized = expression.replace("'", "")
        if form.upper() == "SOP":
            obj = expression_to_sympy(expression, ["A","B","C","D","E","F"], "SOP")
        else:
            obj = expression_to_sympy(expression, ["A","B","C","D","E","F"], "POS")
        simplified = sp.simplify_logic(obj, form=form.lower(), force=True)
        return [f"Input expression: {expression}", f"SymPy Boolean form: {sp.sstr(obj)}", f"Exact simplified form: {sp.sstr(simplified)}", "The selected Quine–McCluskey/Petrick cover is shown separately in the result panel."]
    except Exception:
        return [f"Input expression: {expression}", "Algebraic trace unavailable for this input; use the exact minimization result and truth-table verification."]
