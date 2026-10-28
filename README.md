# AI-Based Fault Detection, Diagnosis & Automated Circuit Repair

A modular reference implementation for combinational Boolean circuits. It combines an explicit netlist simulator, fault injection, exhaustive differential testing, a fault dictionary, a structured LLM prompt, repair-model generation, and exhaustive equivalence checking.

## Scope and reliability notes

- Supported models: 1-bit full adder, 4-bit ripple-carry adder, 4:1 MUX.
- Fault models: SA0/SA1 on modeled signals (including primary inputs and gate outputs), gate mutation, and AND/OR bridge between independent signals.
- Boolean semantics are two-state, zero-delay. This is not an analog simulator, gate-delay simulator, physical design tool, or silicon repair tool.
- A fault can be **undetectable** or have the same output signature as another fault. The diagnostic engine reports all exact signature matches instead of falsely claiming uniqueness.
- "Fault coverage" means the fraction of enumerated modeled faults that produce an output signature different from the golden circuit. It is model-dependent and is not industrial ATPG coverage.
- "Diagnostic resolution" is `100 / number of exact dictionary matches`; this is a compact metric, not a standardized industry metric.
- Repair is currently performed by removing the injected-fault overlay and restoring the nominal model. It is not an automatic rewrite of arbitrary third-party RTL.
- The Logisim exporter creates an XML schematic scaffold with labeled pins/gates. XML well-formedness is checked, but complete net routing and compatibility with every Logisim version are not guaranteed. Inspect it in Logisim before relying on it.
- The included Verilog example is for the 1-bit full adder. The Python engine models all three circuit choices.

## Files

- `app.py` — Streamlit dashboard.
- `circuit_engine.py` — topologically ordered gate-level Boolean simulator and fault injection.
- `fault_diagnostician.py` — differential tables, fault dictionary, candidate ranking, LLM prompt, exhaustive equivalence.
- `logisim_exporter.py` — Logisim-evolution XML scaffold generator.
- `faulty_logisim.py` — command-line wrapper for `.circ` generation.
- `golden_circuit.v`, `faulty_circuit.v`, `tb_fault_detector.v` — synthesizable reference RTL, parameterized demonstration faults, exhaustive testbench.
- `tests/` — automated Python regression tests.

## Setup

Use Python 3.10+ (3.11+ recommended). From this directory:

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run the dashboard

```bash
streamlit run app.py
```

Choose a circuit, choose the fault kind and node/operation, then click **Run diagnosis and repair**. The app shows the exhaustive differential truth table, signature-matched candidates, verification status, and downloads for CSV, prompt JSON, and schematic XML.

## Python tests

```bash
python -m unittest discover -s tests -v
```

## Icarus Verilog validation

Install Icarus Verilog (`iverilog` and `vvp`) from your platform package manager or the official project distribution. Then run:

```bash
iverilog -g2012 -Wall -s tb_fault_detector -o simv golden_circuit.v faulty_circuit.v tb_fault_detector.v
vvp simv
```

Expected result includes:
- `PASS: golden circuit matches reference equation on all 8 vectors.`
- `PASS: fault detected on ... vectors.`

Test other fault modes by editing `.FAULT_MODE(1)` in `tb_fault_detector.v`:
- `1`: Sum SA0
- `2`: Sum SA1
- `3`: Cout SA0
- `4`: Cout SA1
- `5`: XOR1 XOR→OR
- `6`: AND1 AND→NAND

For a no-fault equivalence run, set `.FAULT_ENABLE(0)`. The testbench currently expects a detected fault, so the final detection assertion should be disabled for that no-fault run.

## Generate a Logisim XML scaffold

```bash
python faulty_logisim.py --circuit "Full Adder" --node SUM --stuck 0 --out faulty_circuit.circ
```

The command writes XML and parses it back to check well-formedness. Open it in Logisim-evolution and inspect placement/wiring. This export is a scaffold, not a claim of a fully routed or simulation-validated schematic.

## LLM integration

`make_llm_prompt(...)` produces a structured JSON-compatible prompt with circuit netlist, truth-table evidence, and algorithmic candidates. No LLM API is called by default; this avoids requiring API keys and keeps the diagnosis deterministic. If you add a provider, keep API keys in environment variables, validate the response against a schema, and never accept a repair without running `verify_equivalence`.

## Design notes

### Fault dictionary
For every modeled fault, the tool computes the full output vector signature over all input combinations. A diagnosis returns all faults whose signatures exactly match the observed signature. Identical signatures indicate ambiguity under the chosen observation model.

### Exhaustive equivalence
For an N-input combinational circuit, the verifier checks all `2**N` input vectors and every primary output. This is exhaustive for the software model. It is not SAT-based RTL formal verification, sequential equivalence, four-state Verilog equivalence, or timing-aware equivalence.
