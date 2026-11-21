# Final report

- `final_report.pdf`: eight-page English report for the course submission.
- `final_report.md`: editable source, including explicit page breaks.
- `build_report.py`: reproducible PDF builder using ReportLab.
- `plot_report_figure.py`: compact unsupported-additions figure from the existing scores.
- `figures/`: compact figure in PNG and SVG formats; other report figures reuse the analysis assets.

Author: Sangkook Kang, as confirmed for this report.

The report includes an abstract, introduction, related work, data, methods,
evaluation protocol, quantitative and qualitative results, discussion,
limitations, conclusion, reproduction instructions, references, and AI-assistance
acknowledgement. Scores are unblinded single-reviewer AI judgments, not
independently validated accuracy estimates.

## Rebuild

From the repository root, in a Python environment with the report dependencies:

```bash
python -m pip install -r requirements-report.txt
python report/plot_report_figure.py
python report/build_report.py
```

To render page images into a private directory for layout review:

```bash
python report/build_report.py --render-dir /tmp/csi5130-report-pages
```

Inspect every page after changing the Markdown or figure sizing. Rendered page
PNGs are quality-check intermediates and do not belong in the final report folder.
The builder checks the analysis source fingerprints before generating the PDF.
It makes no API calls and does not change generation outputs or review scores.

The final report was rendered and all eight pages inspected. Numerical values,
PDF text, author metadata, paper size, links, source hashes, and required sections
were checked. The managed Word runtime was unavailable, so the editable source
is Markdown rather than a Word file.

The author should review the report and its disclosed evaluation limitations
before course submission. The repository update does not submit anything to Moodle.
