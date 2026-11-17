# UMDAC Swift Automated Dashboard Builder

This is a **Python-based dashboard generator**. It reads small, approved aggregate CSVs and automatically generates:

- `dashboard_output/UMDAC_Swift_8_Page_Dashboard.pdf` (eight landscape feature-group pages)
- `dashboard_output/dashboard_01.png` ... `dashboard_08.png` (one PNG per page)

**You do not need to manually build charts in Power BI or process the full 10-million-row dataset.**

## Windows + VS Code: three steps

1. Extract this ZIP into one folder. In VS Code, choose **File > Open Folder** and open the extracted `UMDAC_Swift_Automated_Dashboard` folder.
2. Open **Terminal > New Terminal**, then install the required Python libraries (once):

   ```powershell
   python -m pip install pandas numpy matplotlib
   ```

   If using your existing VS Code virtual environment, use ` .\.venv\Scripts\python.exe -m pip install pandas numpy matplotlib ` instead.

3. In the same folder, run:

   ```powershell
   python generate_dashboard.py
   ```

   Or, with an existing venv:

   ```powershell
   .\.venv\Scripts\python.exe generate_dashboard.py
   ```

Output appears automatically in `dashboard_output/`.

## What is generated

| Page | Feature group |
|---|---|
| 01 | Payment Routing |
| 02 | Duration & Continuity |
| 03 | Currency Conversions |
| 04 | Payment Amounts |
| 05 | Currency Patterns |
| 06 | Temporal Patterns |
| 07 | Parties & Geography |
| 08 | Anomaly Patterns |

To adjust text, change the rule/interpretation/limitation strings inside the corresponding `page1()` ... `page8()` function in `generate_dashboard.py`, save, and rerun the command. You can also change axes and charts in those functions. All eight pages will regenerate.

## Evidence, provenance and safeguards

### Data Sources and Provenance

The 22 aggregate CSV files used by this dashboard generator originate from Kenny's corrected reverse-engineering analysis.

Member 1's Payment Economics analysis provides independent supporting evidence but is not directly imported by the current dashboard generator.

The dashboard script visualizes previously calculated statistics. It does not independently reproduce or validate the underlying generating rules.

All final interpretations, numerical claims and validation results must be reviewed against the original analytical outputs before submission.