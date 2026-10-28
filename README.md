# Natural Language to Logic Circuit Generator & Simulator

A Streamlit engineering prototype that converts supported English decision specifications into a validated Boolean JSON specification, truth table, minimized SOP/POS expression, live input simulator, schematic, Verilog, and a Logisim `.circ` export.

## Requirements
- Python 3.11+
- Graphviz system executable recommended for SVG schematic rendering (`brew install graphviz` on macOS; `sudo apt install graphviz` on Debian/Ubuntu).
- Optional OpenAI API key for LLM-assisted parsing. Offline demo and expression parsing work without a key.

## Setup
```bash
cd nl_logic_circuit_generator
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```
Open the local URL printed by Streamlit (typically http://localhost:8501).

## Optional OpenAI parser
macOS/Linux:
```bash
export OPENAI_API_KEY="your-key"
streamlit run app.py
```
PowerShell:
```powershell
$env:OPENAI_API_KEY="your-key"
streamlit run app.py
```
Never commit API keys. Use environment variables or a secret manager.

## Demo scenarios
1. Automobile seatbelt & ignition safety (3 inputs).
2. Chemical tank overflow & temperature alarm (4 inputs).
3. Three-person majority voting with override (4 inputs).

Load a demo in the **Demo scenarios** tab. The parser returns a structured intermediate JSON spec; the app then builds the truth table and minimizes the selected output.

## Tests
```bash
pytest -q
```

## Logisim import
1. Download the `.circ` file from the app.
2. Open Logisim or Logisim-evolution and use **File → Open**.
3. Inspect component properties, pin directions, and every wire.
4. Simulate all truth-table combinations and compare with the CSV output before relying on the circuit.

## Boolean expression syntax
Use uppercase variable names A-F and operators `AND`, `OR`, `NOT`, `&`, `|`, `~`, `^`, with parentheses. Example:
`Y = (A AND B) OR NOT C`

## Engineering and safety notes
- Offline natural-language parsing is intentionally conservative: it recognizes known demo patterns and explicit Boolean expressions; unfamiliar free-form prose requires the optional LLM parser or a reviewed explicit rule.
- SymPy performs exact Boolean minimization for the bounded input count. The app exhaustively checks the reduced expression against the formal rule represented in the intermediate specification.
- The equivalence test is not proof that the English specification was interpreted correctly. Review the JSON specification.
- Gate counts, CMOS transistor estimates, and delay are rough educational metrics, not technology-specific synthesis or sign-off.
- Logisim XML schemas and gate pin coordinates vary across versions. Treat export as a starting point and verify it in the exact installed version.
- Hazard-free behavior is not proven by static truth-table equivalence. Real-time industrial or automotive safety use requires formal requirements, timing analysis, independent verification, and certified hardware/software processes.
