# Boolean Logic Workbench

Streamlit prototype for 4-, 5-, and 6-variable Boolean minimization using Quine–McCluskey prime implicant generation and Petrick-style minimum-cover selection. Includes truth tables, K-map planes, Verilog export, a Logisim XML exporter, complexity estimates, and exhaustive equivalence checking.

## Requirements

- Python 3.11 or newer recommended
- Logisim-evolution or Logisim installed separately for opening `.circ` exports
- Internet is not required after Python dependencies are installed

## Setup (macOS / Linux)

```bash
cd boolean_logic_generator
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

On Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

## Input formats

- Minterms: `Σm(0, 2, 5, 7) + d(1, 3)`
- Maxterms: `ΠM(0, 1, 4, 7)`
- Expression: textbook apostrophe complements and `+` OR, e.g. `A'B'C'D + AB'C'D`
- Truth table: exactly `2^N` rows, ascending binary order, input columns followed by output `F`

Variable order is A as most-significant bit through the selected final variable as least-significant bit.

## Tests

```bash
pytest -q
```

## Open a generated circuit

1. Click **Generate Logisim .circ file**, then download the file.
2. Open Logisim / Logisim-evolution and choose **File → Open**, then select the `.circ` file.
3. Inspect every gate input, wire, and output pin. Component attribute names and gate pin geometry can differ between Logisim classic and Logisim-evolution versions.
4. Run the simulator, toggle each input, and compare against the truth table shown in the app.

## Engineering limitations 

- The Boolean minimizer and truth-table equivalence checker are algorithmic; the checker verifies the reduced expression against the ON-set exhaustively.
- The Logisim file is generated XML and parsed for well-formedness, but this alone does **not** prove the target Logisim version accepts or electrically connects every wire. Validate the downloaded circuit in the exact version you use. Gate-pin geometry varies by version, and this starter generator is not a replacement for opening and simulation-testing the artifact.
- K-map cells are displayed in Gray-code order and grouped by plane; automatic colored prime-implicant loop overlays are not implemented yet.
- The expression parser supports common textbook notation, not every possible Boolean syntax. Prefer minterm notation or truth-table input for unambiguous results.
- Complexity figures are educational first-order estimates, not standard-cell synthesis, transistor-level netlist estimates, or timing sign-off. Actual propagation delay requires a target technology/library and load/fan-out assumptions.
- The LLM integration is a prompt generator. It does not require an API key and does not make claims about theorem steps it cannot substantiate.

## File layout

```text
boolean_logic_generator/
├── app.py
├── simplifier.py
├── logisim_builder.py
├── requirements.txt
├── README.md
└── tests/
    └── test_simplifier.py
```
