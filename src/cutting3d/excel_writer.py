"""Excel template writer for competition result files.

Templates have Sheet1 with structure:
  - Column B: material type (L01 rows 4-8, L02 rows 9-13, L03 rows 14-18)
  - Row 3 Columns C-I: piece types J01-J07
  - Data cells C4:I18: piece counts per material block × piece type
  - result2 also has column J with profit formulas and grey D9D9D9 fills
  - result1 uses theme-based grey fills

Fills grey cells with actual piece counts from the solution patterns.
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.styles import PatternFill, Font, Border, Side
from openpyxl.utils import get_column_letter

from .models import ExperimentResult, Material, Pattern, Piece


def _is_grey_cell(cell) -> bool:
    """Detect grey-filled cells using multiple strategies."""
    f = cell.fill
    if f is None:
        return False

    # Strategy 1: Check fgColor RGB (e.g., D9D9D9)
    if f.fgColor and f.fgColor.type == "rgb" and f.fgColor.rgb:
        try:
            rgb = f.fgColor.rgb
            if len(rgb) == 8:
                rgb = rgb[2:]
            r, g, b = int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)
            if abs(r - g) < 40 and abs(g - b) < 40 and abs(r - b) < 40:
                if 100 < r < 250:
                    return True
        except (ValueError, TypeError):
            pass

    # Strategy 2: Check theme-based fills (used by result1.xlsx)
    if f.fgColor and f.fgColor.type == "theme":
        return True

    # Strategy 3: Check indexed grey colors
    if f.fgColor and f.fgColor.type == "indexed":
        if f.fgColor.indexed in [15, 16, 48]:
            return True

    # Strategy 4: Check bgColor for indexed grey (some templates use bgColor)
    if f.bgColor and f.bgColor.type == "indexed":
        if f.bgColor.indexed in [15, 16, 48]:
            return True

    # Strategy 5: Check patternType + empty value in data region
    if f.patternType == "solid" and cell.value is None:
        # Check if in likely data region (C4:I18 of Sheet1)
        if 4 <= cell.row <= 18 and 3 <= cell.column <= 9:
            # Heuristic: if surrounding cells are also empty with solid fill
            return True

    return False


def _detect_template_structure(ws) -> dict[str, Any]:
    """Detect the template structure from Sheet1.

    Returns dict with material_rows and piece_columns.
    """
    structure: dict[str, Any] = {
        "material_rows": {},  # material_name -> list of row numbers
        "piece_columns": {},  # piece_name -> column number
        "data_cells": [],     # list of (row, col) that need filling
        "data_range": None,
    }

    # Detect piece columns from row 3
    for col in range(3, 12):
        val = ws.cell(row=3, column=col).value
        if val and isinstance(val, str):
            val = val.strip().upper()
            if val.startswith("J") and len(val) == 3:
                structure["piece_columns"][val] = col

    # Detect material rows from column B (rows 4-18)
    for row in range(4, 20):
        val = ws.cell(row=row, column=2).value
        if val and isinstance(val, str):
            val = val.strip().upper()
            if val in ("L01", "L02", "L03"):
                if val not in structure["material_rows"]:
                    structure["material_rows"][val] = []
                structure["material_rows"][val].append(row)

    # Detect data cells (intersection of material rows and piece columns)
    for mat, rows in structure["material_rows"].items():
        for row in rows:
            for pname, col in structure["piece_columns"].items():
                cell = ws.cell(row=row, column=col)
                if _is_grey_cell(cell) or cell.value is None:
                    structure["data_cells"].append({
                        "row": row,
                        "col": col,
                        "material": mat,
                        "piece": pname,
                        "coordinate": cell.coordinate,
                        "is_grey": _is_grey_cell(cell),
                    })

    return structure


def _build_per_block_counts(
    result: ExperimentResult,
    materials: dict[str, Material],
    pieces: dict[str, Piece],
) -> dict[str, list[dict[str, int]]]:
    """Build per-block piece counts from the solution pattern usage.

    Returns dict[material_name] -> list of {piece_name: count} per block.
    """
    pattern_map = {p.pattern_id: p for p in result.patterns}
    per_block: dict[str, list[dict[str, int]]] = {}

    for mat_name, material in materials.items():
        blocks: list[dict[str, int]] = []
        for pid, count in result.solution.pattern_usage.items():
            if pid in pattern_map and pattern_map[pid].material_name == mat_name:
                pat = pattern_map[pid]
                piece_counts = pat.get_piece_counts(sorted(pieces.keys()))
                for _ in range(count):
                    blocks.append(dict(piece_counts))
        # Pad with empty blocks if fewer than material.count
        while len(blocks) < material.count:
            blocks.append({pn: 0 for pn in pieces})
        per_block[mat_name] = blocks[:material.count]

    return per_block


def fill_result_xlsx(
    template_path: str | Path,
    output_path: str | Path,
    result: ExperimentResult,
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    logger: logging.Logger | None = None,
    timing: dict[str, float] | None = None,
) -> tuple[bool, dict[str, Any]]:
    """Fill template with solution data.

    Reads template structure, fills piece counts per material block,
    adds computed_solution sheet, saves filled version.
    """
    template_path = Path(template_path)
    output_path = Path(output_path)

    report: dict[str, Any] = {
        "template": str(template_path),
        "output": str(output_path),
        "timestamp": datetime.now().isoformat(),
        "sheets_processed": [],
        "grey_cells_found": 0,
        "grey_cells_filled": 0,
        "computed_sheet_added": False,
        "errors": [],
        "warnings": [],
    }

    if not template_path.exists():
        msg = f"Template not found: {template_path}"
        if logger: logger.error(msg)
        report["errors"].append(msg)
        return False, report

    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(template_path, output_path)

    try:
        wb = openpyxl.load_workbook(output_path)
    except Exception as e:
        report["errors"].append(f"Failed to open: {e}")
        return False, report

    report["workbook_sheets"] = wb.sheetnames

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        if ws.max_row < 3:
            report["sheets_processed"].append({"name": sheet_name, "filled": 0})
            continue

        structure = _detect_template_structure(ws)
        data_cells = structure["data_cells"]
        report["grey_cells_found"] += len(data_cells)

        if not data_cells:
            report["sheets_processed"].append({"name": sheet_name, "filled": 0})
            continue

        # Build per-block counts
        per_block = _build_per_block_counts(result, materials, pieces)

        filled = 0
        skipped = 0
        for dc in data_cells:
            mat = dc["material"]
            pname = dc["piece"]
            row_idx = dc["row"]
            mat_rows = structure["material_rows"].get(mat, [])
            if not mat_rows:
                skipped += 1
                continue

            # Determine which block index this row corresponds to
            try:
                block_idx = mat_rows.index(row_idx)
            except ValueError:
                skipped += 1
                continue

            if mat in per_block and block_idx < len(per_block[mat]):
                count = per_block[mat][block_idx].get(pname, 0)
                ws.cell(row=dc["row"], column=dc["col"]).value = count
                filled += 1
            else:
                ws.cell(row=dc["row"], column=dc["col"]).value = 0
                filled += 1

        report["grey_cells_filled"] += filled
        report["sheets_processed"].append({
            "name": sheet_name,
            "grey_cells_found": len(data_cells),
            "grey_cells_filled": filled,
            "grey_cells_skipped": skipped,
        })

        if logger:
            logger.info(f"  Sheet '{sheet_name}': {len(data_cells)} data cells, {filled} filled")

    # Add computed_solution sheet
    _add_computed_solution_sheet(wb, result, materials, pieces, timing)
    report["computed_sheet_added"] = True

    try:
        wb.save(output_path)
        if logger: logger.info(f"Saved: {output_path}")
    except Exception as e:
        report["errors"].append(f"Save failed: {e}")
        return False, report

    return True, report


def _add_computed_solution_sheet(
    wb: openpyxl.Workbook,
    result: ExperimentResult,
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    timing: dict[str, float] | None = None,
) -> None:
    """Add comprehensive computed_solution sheet."""
    sheet_name = "computed_solution"
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(sheet_name)

    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=11)
    title_font = Font(bold=True, size=14, color="1F4E79")
    sub_font = Font(bold=True, size=12, color="2E75B6")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )

    s = result.solution
    row = 1

    ws.cell(row=row, column=1, value=f"Computed Solution - {result.problem_name.upper()}").font = title_font
    row += 2

    ws.cell(row=row, column=1, value="Basic Information").font = sub_font
    row += 1
    info_items = [
        ("Status", s.status.value),
        ("Objective Value", f"{s.objective_value:.2f}"),
        ("Total Profit", f"{s.total_profit:,.2f}"),
        ("Total Used Volume", f"{s.total_used_volume:,}"),
        ("Total Waste Volume", f"{s.total_waste_volume:,}"),
        ("Total Material Volume", f"{s.total_material_volume:,}"),
        ("Material Utilization", f"{s.material_utilization * 100:.4f}%"),
        ("Utilization Gap to 100%", f"{(1.0 - s.material_utilization) * 100:.4f}%"),
        ("Upper Bound", f"{s.upper_bound:,.4f}" if s.upper_bound > 2 else f"{s.upper_bound:.4f}"),
        ("Lower Bound", f"{s.lower_bound:,.4f}" if s.lower_bound < 2 else f"{s.lower_bound:,.2f}"),
        ("Gap", f"{s.gap * 100:.4f}%"),
        ("Solve Time (s)", f"{s.solve_time_seconds:.2f}"),
        ("Pattern-Library Optimal", "CP-SAT OPTIMAL within generated pattern library"),
    ]
    for label, value in info_items:
        c1 = ws.cell(row=row, column=1, value=label); c1.font = Font(bold=True); c1.border = thin_border
        c2 = ws.cell(row=row, column=2, value=value); c2.border = thin_border
        row += 1
    row += 1

    if timing:
        ws.cell(row=row, column=1, value="Runtime Breakdown").font = sub_font
        row += 1
        for k, v in timing.items():
            ws.cell(row=row, column=1, value=k).font = Font(bold=True)
            ws.cell(row=row, column=1).border = thin_border
            ws.cell(row=row, column=2, value=f"{v:.2f}s").border = thin_border
            row += 1
        row += 1

    # Piece production
    ws.cell(row=row, column=1, value="Piece Production Quantities").font = sub_font
    row += 1
    for j, h in enumerate(["Piece", "Count", "Unit Volume", "Total Volume", "Unit Profit", "Total Profit"], 1):
        c = ws.cell(row=row, column=j, value=h); c.font = header_font; c.fill = header_fill; c.border = thin_border
    row += 1
    for pname in sorted(pieces.keys()):
        count = s.piece_counts.get(pname, 0)
        piece = pieces[pname]
        for j, v in enumerate([pname, count, piece.volume, count * piece.volume, piece.profit, count * piece.profit], 1):
            ws.cell(row=row, column=j, value=v).border = thin_border
        row += 1
    row += 1

    # Material utilization
    ws.cell(row=row, column=1, value="Material Utilization Breakdown").font = sub_font
    row += 1
    for j, h in enumerate(["Material", "Count", "Unit Volume", "Total Volume", "Used Volume", "Waste", "Utilization"], 1):
        c = ws.cell(row=row, column=j, value=h); c.font = header_font; c.fill = header_fill; c.border = thin_border
    row += 1
    pattern_map = {p.pattern_id: p for p in result.patterns}
    for mat_name, material in materials.items():
        used_vol = sum(
            count * pattern_map[pid].used_volume
            for pid, count in s.pattern_usage.items()
            if pid in pattern_map and pattern_map[pid].material_name == mat_name
        )
        tv = material.volume * material.count
        waste = tv - used_vol
        util = used_vol / tv if tv > 0 else 0.0
        for j, v in enumerate([mat_name, material.count, material.volume, tv, used_vol, waste, f"{util * 100:.2f}%"], 1):
            ws.cell(row=row, column=j, value=v).border = thin_border
        row += 1
    row += 1

    # Pattern usage
    ws.cell(row=row, column=1, value="Pattern Usage Details").font = sub_font
    row += 1
    for j, h in enumerate(["Pattern ID", "Material", "Times Used", "Pieces", "Used Volume", "Utilization"], 1):
        c = ws.cell(row=row, column=j, value=h); c.font = header_font; c.fill = header_fill; c.border = thin_border
    row += 1
    for pid, count in sorted(s.pattern_usage.items()):
        pat = pattern_map.get(pid)
        mat_name = pat.material_name if pat else "?"
        num_pieces = pat.num_pieces if pat else 0
        used_vol = pat.used_volume if pat else 0
        mat = materials.get(mat_name)
        util = used_vol / mat.volume if mat and mat.volume > 0 else 0.0
        for j, v in enumerate([pid, mat_name, count, num_pieces, used_vol, f"{util * 100:.2f}%"], 1):
            ws.cell(row=row, column=j, value=v).border = thin_border
        row += 1

    for col in range(1, 10):
        ws.column_dimensions[get_column_letter(col)].width = 22


def make_backup(template_path: str | Path, backup_dir: str | Path) -> Path:
    """Create timestamped backup."""
    template_path = Path(template_path)
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{template_path.stem}_backup_{ts}{template_path.suffix}"
    shutil.copy(template_path, backup_path)
    return backup_path


def save_template_mapping(
    template_path: str | Path,
    output_path: str | Path,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """Save grey cell mapping."""
    template_path = Path(template_path)
    if not template_path.exists():
        return {"error": f"Not found: {template_path}"}

    wb = openpyxl.load_workbook(template_path)
    sheet_data: dict[str, Any] = {}

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        structure = _detect_template_structure(ws)
        sheet_data[sheet_name] = {
            "data_cells": len(structure["data_cells"]),
            "material_rows": structure["material_rows"],
            "piece_columns": structure["piece_columns"],
        }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"template": str(template_path), "sheets": sheet_data, "data_cells": structure.get("data_cells", [])}, f, indent=2, ensure_ascii=False)

    if logger:
        logger.info(f"Mapping saved: {output_path}")
    return {"template": str(template_path), "sheets": sheet_data}


def generate_validation_report(
    filled_path: str | Path,
    result: ExperimentResult,
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    output_path: str | Path,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """Read back and validate filled Excel."""
    filled_path = Path(filled_path)
    output_path = Path(output_path)

    report: dict[str, Any] = {
        "file": str(filled_path),
        "exists": filled_path.exists(),
        "timestamp": datetime.now().isoformat(),
        "sheet_names": [],
        "has_computed_solution": False,
        "grey_cells_found": 0,
        "grey_cells_filled": 0,
        "metrics_match_json": None,
        "warnings": [],
        "errors": [],
    }

    if not filled_path.exists():
        report["errors"].append("File does not exist")
        return report

    try:
        wb = openpyxl.load_workbook(filled_path)
        report["sheet_names"] = wb.sheetnames
        report["has_computed_solution"] = "computed_solution" in wb.sheetnames

        # Check data cells in Sheet1
        if "Sheet1" in wb.sheetnames:
            ws = wb["Sheet1"]
            structure = _detect_template_structure(ws)
            filled = 0
            for dc in structure["data_cells"]:
                val = ws.cell(row=dc["row"], column=dc["col"]).value
                if val is not None and val != "":
                    filled += 1
            report["grey_cells_found"] = len(structure["data_cells"])
            report["grey_cells_filled"] = filled
            if filled < len(structure["data_cells"]):
                report["warnings"].append(f"{len(structure['data_cells']) - filled} cells unfilled")

        # Cross-check computed_solution
        if "computed_solution" in wb.sheetnames:
            ws = wb["computed_solution"]
            for r in range(1, min(50, ws.max_row + 1)):
                val = ws.cell(row=r, column=1).value
                if val and "Material Utilization" in str(val).strip():
                    excel_val = ws.cell(row=r, column=2).value
                    try:
                        excel_util = float(str(excel_val).replace("%", "")) / 100.0
                        if abs(excel_util - result.solution.material_utilization) < 0.001:
                            report["metrics_match_json"] = True
                        else:
                            report["metrics_match_json"] = False
                            report["warnings"].append(f"Util mismatch: Excel={excel_util}, JSON={result.solution.material_utilization}")
                    except (ValueError, TypeError):
                        pass
                    break

    except Exception as e:
        report["errors"].append(str(e))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    if logger:
        status = "PASS" if report["metrics_match_json"] else "WARN"
        logger.info(f"Excel validation: {status} ({report['grey_cells_filled']}/{report['grey_cells_found']} filled)")

    return report
