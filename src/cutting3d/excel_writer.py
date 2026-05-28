"""Excel template writer for competition result files.

Reads the template .xlsx files, identifies grey-filled cells for data entry,
and writes computed solution data while preserving the original format.
"""

from __future__ import annotations

import json
import logging
import shutil
from copy import copy
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from .models import ExperimentResult, Material, Pattern, Piece


def _is_grey_fill(fill: PatternFill) -> bool:
    """Check if a cell fill is grey (intended for data entry)."""
    if fill is None or fill.fgColor is None:
        return False
    try:
        fg = fill.fgColor
        if fg.type == "rgb" and fg.rgb:
            rgb = fg.rgb
            if len(rgb) == 8:
                rgb = rgb[2:]  # Remove alpha
            r, g, b = int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)
            # Grey: all channels roughly equal and not white/black
            if abs(r - g) < 30 and abs(g - b) < 30 and abs(r - b) < 30:
                if 100 < r < 240:
                    return True
        elif fg.type == "indexed":
            # Common grey indexed colors
            if fg.indexed in [15, 16, 48]:
                return True
    except Exception:
        pass
    return False


def _get_grey_cells(ws: openpyxl.worksheet.worksheet.Worksheet) -> list[dict[str, Any]]:
    """Identify all grey-filled cells in a worksheet."""
    grey_cells = []
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=ws.max_column):
        for cell in row:
            if _is_grey_fill(cell.fill):
                grey_cells.append({
                    "row": cell.row,
                    "col": cell.column,
                    "col_letter": get_column_letter(cell.column),
                    "coordinate": cell.coordinate,
                    "value": cell.value,
                })
    return grey_cells


def _find_adjacent_label(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    row: int, col: int,
) -> str:
    """Try to find a label adjacent to a grey cell (look left and up)."""
    # Look left
    for c in range(col - 1, max(0, col - 4), -1):
        val = ws.cell(row=row, column=c).value
        if val is not None:
            return str(val).strip()

    # Look up
    for r in range(row - 1, max(0, row - 4), -1):
        val = ws.cell(row=r, column=col).value
        if val is not None:
            return str(val).strip()

    return ""


def _get_column_header(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    col: int,
) -> str:
    """Get the column header (value in row 1 or nearby)."""
    for r in range(1, min(5, ws.max_row + 1)):
        val = ws.cell(row=r, column=col).value
        if val is not None:
            return str(val).strip()
    return ""


def _infer_template_structure(
    ws: openpyxl.worksheet.worksheet.Worksheet,
) -> dict[str, list[dict[str, Any]]]:
    """Try to infer the template structure from labels and grey cells."""
    grey_cells = _get_grey_cells(ws)
    if not grey_cells:
        return {"grey_cells": [], "sections": {}}

    # Group grey cells by their context
    structure: dict[str, list[dict[str, Any]]] = {}
    categorized: list[dict[str, Any]] = []

    for gc in grey_cells:
        label = _find_adjacent_label(ws, gc["row"], gc["col"])
        col_header = _get_column_header(ws, gc["col"])
        gc["adjacent_label"] = label
        gc["column_header"] = col_header
        categorized.append(gc)

    structure["grey_cells"] = categorized

    # Try to identify sections based on labels
    sections: dict[str, list[dict[str, Any]]] = {}
    for gc in categorized:
        label = gc.get("adjacent_label", "").upper()
        for mat in ["L01", "L02", "L03"]:
            if mat in label:
                if mat not in sections:
                    sections[mat] = []
                sections[mat].append(gc)
                break
        for p in ["J01", "J02", "J03", "J04", "J05", "J06", "J07"]:
            if p in label:
                key = f"{p}_section"
                if key not in sections:
                    sections[key] = []
                sections[key].append(gc)
                break

    structure["sections"] = sections
    return structure


def fill_result_xlsx(
    template_path: str | Path,
    output_path: str | Path,
    result: ExperimentResult,
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    logger: logging.Logger | None = None,
) -> tuple[bool, dict[str, Any]]:
    """Fill a result Excel template with solution data.

    Args:
        template_path: Path to the template .xlsx file.
        output_path: Where to write the filled file.
        result: The experiment result to write.
        materials: Material definitions.
        pieces: Piece definitions.
        logger: Logger instance.

    Returns:
        (success, report) where report describes what was filled.
    """
    template_path = Path(template_path)
    output_path = Path(output_path)

    report: dict[str, Any] = {
        "template": str(template_path),
        "output": str(output_path),
        "sheets_processed": [],
        "grey_cells_found": 0,
        "grey_cells_filled": 0,
        "computed_sheet_added": False,
        "errors": [],
        "warnings": [],
    }

    if not template_path.exists():
        msg = f"Template not found: {template_path}"
        if logger:
            logger.error(msg)
        report["errors"].append(msg)
        return False, report

    # Copy template to output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(template_path, output_path)

    try:
        wb = openpyxl.load_workbook(output_path)
    except Exception as e:
        msg = f"Failed to open workbook: {e}"
        if logger:
            logger.error(msg)
        report["errors"].append(msg)
        return False, report

    if logger:
        logger.info(f"Processing template: {template_path}")
        logger.info(f"  Sheets: {wb.sheetnames}")

    # Process each sheet
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        structure = _infer_template_structure(ws)
        grey_cells = structure.get("grey_cells", [])
        report["grey_cells_found"] += len(grey_cells)

        if logger:
            logger.info(f"  Sheet '{sheet_name}': {len(grey_cells)} grey cells found")

        # Try to fill grey cells
        filled_count = 0
        for gc in grey_cells:
            cell = ws.cell(row=gc["row"], column=gc["col"])
            filled_value = _determine_cell_value(
                gc, result, materials, pieces, ws
            )
            if filled_value is not None:
                cell.value = filled_value
                filled_count += 1
                if logger:
                    logger.debug(
                        f"    Filled {gc['coordinate']}: "
                        f"'{gc.get('adjacent_label', '')}' -> {filled_value}"
                    )

        report["grey_cells_filled"] += filled_count

        if logger:
            logger.info(f"    Filled {filled_count}/{len(grey_cells)} grey cells")

        report["sheets_processed"].append({
            "name": sheet_name,
            "grey_cells_found": len(grey_cells),
            "grey_cells_filled": filled_count,
        })

    # Always add a computed_solution sheet
    _add_computed_solution_sheet(wb, result, materials, pieces, logger)
    report["computed_sheet_added"] = True

    # Save
    try:
        wb.save(output_path)
        if logger:
            logger.info(f"Saved filled workbook to: {output_path}")
    except Exception as e:
        msg = f"Failed to save workbook: {e}"
        if logger:
            logger.error(msg)
        report["errors"].append(msg)
        return False, report

    return True, report


def _determine_cell_value(
    gc: dict[str, Any],
    result: ExperimentResult,
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    ws: Any,
) -> Any:
    """Try to determine the appropriate value for a grey cell based on context."""
    label = gc.get("adjacent_label", "")
    col_header = gc.get("column_header", "")
    context = (label + " " + col_header).lower()

    solution = result.solution

    s = result.solution
    pattern_map = {p.pattern_id: p for p in result.patterns}

    # Try to match material names
    for mat_name in ["L01", "L02", "L03"]:
        if mat_name.lower() in context or mat_name.lower() in label:
            mat = materials.get(mat_name)
            if mat is None:
                continue
            # Compute per-material utilization from pattern usage
            used_vol = sum(
                count * pattern_map[pid].used_volume
                for pid, count in s.pattern_usage.items()
                if pid in pattern_map and pattern_map[pid].material_name == mat_name
            )
            total_vol = mat.volume * mat.count
            # Determine what value is expected
            if any(w in context for w in ["利用率", "utilization", "util"]):
                return f"{used_vol / total_vol * 100:.2f}%" if total_vol > 0 else "0%"
            if any(w in context for w in ["废料", "waste", "废弃"]):
                return total_vol - used_vol
            if any(w in context for w in ["用量", "使用", "count", "数量"]):
                mat_count = sum(
                    count for pid, count in s.pattern_usage.items()
                    if pid in pattern_map and pattern_map[pid].material_name == mat_name
                )
                return mat_count
            # Default: return utilization for this material
            return f"{used_vol / total_vol * 100:.2f}%" if total_vol > 0 else "0%"

    # Try to match piece names
    for pname in ["J01", "J02", "J03", "J04", "J05", "J06", "J07"]:
        if pname.lower() in context or pname.lower() in label:
            if any(w in context for w in ["数量", "产量", "count", "quantity", "件数"]):
                return solution.piece_counts.get(pname, 0)
            if any(w in context for w in ["收益", "profit", "value"]):
                count = solution.piece_counts.get(pname, 0)
                if pname in pieces:
                    return count * pieces[pname].profit
                return 0
            # Default: return count
            return solution.piece_counts.get(pname, 0)

    # Match overall metrics
    if any(w in context for w in ["总利用率", "overall util", "整体利用率"]):
        return f"{solution.material_utilization * 100:.2f}%"
    if any(w in context for w in ["总废料", "total waste", "总废弃"]):
        return solution.total_waste_volume
    if any(w in context for w in ["总收益", "total profit", "总利润"]):
        return solution.total_profit
    if any(w in context for w in ["总使用体积", "used volume"]):
        return solution.total_used_volume

    # If nothing matches, don't fill
    return None


def _add_computed_solution_sheet(
    wb: openpyxl.Workbook,
    result: ExperimentResult,
    materials: dict[str, Material],
    pieces: dict[str, Piece],
    logger: logging.Logger | None = None,
) -> None:
    """Add a comprehensive computed solution sheet to the workbook."""
    sheet_name = "computed_solution"
    if sheet_name in wb.sheetnames:
        # Remove existing one
        del wb[sheet_name]

    ws = wb.create_sheet(sheet_name)

    # Styles
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=11)
    title_font = Font(bold=True, size=14, color="1F4E79")
    sub_font = Font(bold=True, size=12, color="2E75B6")
    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    s = result.solution
    row = 1

    # Title
    ws.cell(row=row, column=1, value=f"Solution Summary - {result.problem_name.upper()}").font = title_font
    row += 2

    # Basic info
    info = [
        ("Status", s.status.value),
        ("Objective Value", f"{s.objective_value:.2f}"),
        ("Total Profit", f"{s.total_profit:,.2f}"),
        ("Total Used Volume", s.total_used_volume),
        ("Total Waste Volume", s.total_waste_volume),
        ("Total Material Volume", s.total_material_volume),
        ("Material Utilization", f"{s.material_utilization * 100:.2f}%"),
        ("Solve Time (s)", f"{s.solve_time_seconds:.2f}"),
        ("Upper Bound", f"{s.upper_bound:.2f}"),
        ("Lower Bound", f"{s.lower_bound:.2f}"),
        ("Gap", f"{s.gap * 100:.2f}%"),
    ]

    ws.cell(row=row, column=1, value="Basic Information").font = sub_font
    row += 1
    for label, value in info:
        ws.cell(row=row, column=1, value=label).font = Font(bold=True)
        ws.cell(row=row, column=1).border = border
        ws.cell(row=row, column=2, value=value).border = border
        row += 1

    row += 1

    # Piece counts
    ws.cell(row=row, column=1, value="Piece Production Quantities").font = sub_font
    row += 1
    headers = ["Piece", "Quantity", "Volume/Unit", "Total Volume", "Unit Profit", "Total Profit"]
    for j, h in enumerate(headers, 1):
        cell = ws.cell(row=row, column=j, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
    row += 1

    piece_names = sorted(pieces.keys())
    for pname in piece_names:
        count = s.piece_counts.get(pname, 0)
        piece = pieces.get(pname)
        vol_unit = piece.volume if piece else 0
        total_vol = count * vol_unit
        unit_profit = piece.profit if piece else 0
        total_profit = count * unit_profit
        values = [pname, count, vol_unit, total_vol, unit_profit, total_profit]
        for j, v in enumerate(values, 1):
            cell = ws.cell(row=row, column=j, value=v)
            cell.border = border
        row += 1

    row += 1

    # Material utilization
    ws.cell(row=row, column=1, value="Material Utilization Breakdown").font = sub_font
    row += 1
    mat_headers = ["Material", "Count", "Volume/Material", "Total Volume", "Used Volume", "Waste", "Utilization"]
    for j, h in enumerate(mat_headers, 1):
        cell = ws.cell(row=row, column=j, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
    row += 1

    pattern_map = {p.pattern_id: p for p in result.patterns}
    for mat_name, material in materials.items():
        used_vol = sum(
            count * pattern_map[pid].used_volume
            for pid, count in s.pattern_usage.items()
            if pid in pattern_map and pattern_map[pid].material_name == mat_name
        )
        total_vol = material.volume * material.count
        waste = total_vol - used_vol
        util = used_vol / total_vol if total_vol > 0 else 0.0
        values = [
            mat_name, material.count, material.volume, total_vol,
            used_vol, waste, f"{util * 100:.2f}%"
        ]
        for j, v in enumerate(values, 1):
            cell = ws.cell(row=row, column=j, value=v)
            cell.border = border
        row += 1

    row += 1

    # Pattern usage
    ws.cell(row=row, column=1, value="Pattern Usage Details").font = sub_font
    row += 1
    pat_headers = ["Pattern ID", "Material", "Times Used", "Pieces", "Used Volume", "Utilization"]
    for j, h in enumerate(pat_headers, 1):
        cell = ws.cell(row=row, column=j, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
    row += 1

    for pid, count in sorted(s.pattern_usage.items()):
        pat = pattern_map.get(pid)
        mat_name = pat.material_name if pat else "?"
        num_pieces = pat.num_pieces if pat else 0
        used_vol = pat.used_volume if pat else 0
        mat = materials.get(mat_name)
        util = used_vol / mat.volume if mat and mat.volume > 0 else 0.0
        values = [pid, mat_name, count, num_pieces, used_vol, f"{util * 100:.2f}%"]
        for j, v in enumerate(values, 1):
            cell = ws.cell(row=row, column=j, value=v)
            cell.border = border
        row += 1

    # Adjust column widths
    for col in range(1, 10):
        ws.column_dimensions[get_column_letter(col)].width = 18

    if logger:
        logger.info(f"Added 'computed_solution' sheet with full results")


def save_template_mapping(
    template_path: str | Path,
    output_path: str | Path,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """Analyze template structure and save grey cell mapping to JSON."""
    template_path = Path(template_path)
    if not template_path.exists():
        return {"error": f"Template not found: {template_path}"}

    wb = openpyxl.load_workbook(template_path)
    all_data: dict[str, Any] = {
        "template": str(template_path),
        "sheets": {},
    }

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        structure = _infer_template_structure(ws)
        all_data["sheets"][sheet_name] = {
            "grey_cell_count": len(structure.get("grey_cells", [])),
            "grey_cells": structure.get("grey_cells", []),
            "sections": {
                k: len(v) for k, v in structure.get("sections", {}).items()
            },
        }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    if logger:
        logger.info(f"Template mapping saved to: {output_path}")

    return all_data
