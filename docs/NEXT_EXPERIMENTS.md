# Exact commands for the next offline experiments

Run from the repository root. These commands use fresh `results/local-next-*` folders, which must not already contain outputs. All are local and credential-free. Use `.venv\Scripts\python.exe` in place of `python` for plotting; standard-library runs below use `--no-plots`. On macOS/Linux the virtual-environment interpreter is `.venv/bin/python`.

```powershell
python -m unittest discover -s tests -v
python -m mas_failure_lab.benchmarks --replicates 1000
python -m mas_failure_lab --config configs/corrective_small.json --output results/local-next-corrective --no-plots
python -m mas_failure_lab --config configs/scaling_matched.json --output results/local-next-scaling --no-plots
python -m mas_failure_lab.suite composition --config configs/composition_routes.json --output results/local-next-routes --no-plots
python -m mas_failure_lab.suite oversight --config configs/oversight_extended.json --output results/local-next-oversight --no-plots
python -m mas_failure_lab.retrieval --config configs/retrieval_mock.json --output results/local-next-retrieval
python -m mas_failure_lab.llm_pilot --mock --config configs/llm_repeated_mock.json --output results/local-next-repeated
python -m mas_failure_lab.datasets --input results/local-next-oversight --version oversight-demo-v1 --output .tmp/releases/oversight-next-demo-v1.zip
```

The new extension sweeps contain 24 corrective, 36 matched-scaling, 18 alternative-workflow and 48 oversight runs. The retrieval and restricted-choice mock configurations each contain three trials on one environment. Replicates/trials are deliberately small worked demonstrations, not powered hypothesis tests. For model trials, choose a provider/model/settings and budget separately; the evidence-retrieval CLI cannot execute paid calls.

To generate plots, omit `--no-plots` and use an environment with Matplotlib installed. On memory-constrained machines set `OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1` before launching Python. Plot/report generation does not modify historical pilot folders.
