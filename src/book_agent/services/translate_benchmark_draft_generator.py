from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz
import yaml


_FRONTMATTER_MARKERS = (
    "about this book",
    "about the author",
    "acknowledg",
    "contents",
    "copyright",
    "foreword",
    "index",
    "preface",
    "table of contents",
)


@dataclass(slots=True)
class PageProbe:
    page_number: int
    word_count: int
    image_count: int
    drawing_count: int
    preview_lines: list[str]


def _slugify(value: str) -> str:
    lowered = value.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "book"


def _normalized_preview(lines: list[str]) -> str:
    return " ".join(lines).lower()


def _looks_like_frontmatter(lines: list[str]) -> bool:
    normalized = _normalized_preview(lines)
    return any(marker in normalized for marker in _FRONTMATTER_MARKERS)


def _sample_id_for_path(document_path: Path) -> str:
    stem = document_path.stem
    slug = _slugify(stem)
    slug = re.sub(r"-(z-library|1lib|z-lib)-sk.*$", "", slug).strip("-")
    return f"pdf-{slug}-001"


def probe_pdf_pages(document_path: Path, *, candidate_pages: list[int] | None = None) -> tuple[int, list[PageProbe]]:
    if candidate_pages is None:
        candidate_pages = [1, 2, 3, 6, 11, 16, 21, 31, 41, 61, 81, 101, 121, 151, 181]
    probes: list[PageProbe] = []
    with fitz.open(str(document_path)) as document:
        page_count = document.page_count
        for page_number in candidate_pages:
            if page_number < 1 or page_number > page_count:
                continue
            page = document.load_page(page_number - 1)
            text = page.get_text("text") or ""
            probes.append(
                PageProbe(
                    page_number=page_number,
                    word_count=len(text.split()),
                    image_count=len(page.get_images(full=True)),
                    drawing_count=len(page.get_drawings()),
                    preview_lines=[line.strip() for line in text.splitlines() if line.strip()][:3],
                )
            )
    return page_count, probes


def choose_mixed_layout_probe_pages(page_probes: list[PageProbe]) -> list[int]:
    if not page_probes:
        return [1]
    body_candidates = [
        probe
        for probe in page_probes
        if probe.word_count >= 140 and not _looks_like_frontmatter(probe.preview_lines)
    ]
    if not body_candidates:
        body_candidates = [probe for probe in page_probes if probe.word_count >= 80]
    if not body_candidates:
        body_candidates = page_probes[:]
    chosen: list[int] = []
    first = min(body_candidates, key=lambda probe: probe.page_number)
    chosen.extend([first.page_number, first.page_number + 1])

    figure_candidates = sorted(
        body_candidates,
        key=lambda probe: (probe.image_count + probe.drawing_count, probe.word_count, probe.page_number),
        reverse=True,
    )
    for probe in figure_candidates:
        for page_number in (probe.page_number, probe.page_number + 1):
            if page_number not in chosen:
                chosen.append(page_number)
            if len(chosen) >= 4:
                break
        if len(chosen) >= 4:
            break
    return sorted(dict.fromkeys(page for page in chosen if page > 0))


def build_pdf_mixed_layout_draft(
    *,
    document_path: Path,
    lane_id: str,
    family_guess: str,
    risk_tags: list[str],
    queue_profile_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    page_count, probes = probe_pdf_pages(document_path)
    selected_pages = choose_mixed_layout_probe_pages(probes)
    sample_id = _sample_id_for_path(document_path)
    gold_label = {
        "schema_version": 1,
        "sample_id": sample_id,
        "lane_id": lane_id,
        "document_path": str(document_path),
        "status": "stub_pending_annotation",
        "priority": "high",
        "slice_scope": {
            "pages": selected_pages,
            "notes": "Auto-generated mixed-layout benchmark draft. Confirm heading/caption/code boundaries before measured execution.",
        },
        "annotation_focus": [
            "heading_hierarchy",
            "mixed_layout_reading_order",
            "figure_caption_linkage",
            "asset_preservation",
        ],
        "blocks": [],
        "todo": [
            "Annotate at least one chapter or section heading block.",
            "Annotate one artifact + caption pair if present in the selected pages.",
            "Keep benchmark execution parser/export-only until the draft is upgraded to annotated_v1.",
        ],
    }
    manifest = {
        "schema_version": 1,
        "benchmark_name": f"translate-agent-auto-draft-{sample_id}",
        "owner": "smy",
        "generated_from": str(queue_profile_path),
        "purpose": (
            f"Auto-generated benchmark-first draft for `{document_path.name}`. "
            "This draft is intended to unblock unattended queue preparation before measured execution."
        ),
        "global_policy": {
            "fail_closed_on_blocking_issue": True,
            "require_gold_labels": True,
            "allow_full_document_run_only_after_lane_certification": True,
            "token_budget_policy": {
                "mode": "parser_probe_only",
                "notes": [
                    "Do not spend translation tokens in this wave.",
                    "Upgrade the gold label from stub_pending_annotation to annotated_v1 before measured execution.",
                ],
            },
        },
        "lanes": [
            {
                "lane_id": lane_id,
                "name": family_guess,
                "target_fidelity_tier": "C",
                "current_certification_status": "exploratory_probe",
            }
        ],
        "samples": [
            {
                "sample_id": sample_id,
                "lane_id": lane_id,
                "document_path": str(document_path),
                "document_kind": "real_book",
                "slice_type": "auto_generated_mixed_layout_probe",
                "source_pages_or_sections": [{"page": page} for page in selected_pages],
                "risk_tags": risk_tags,
                "expected_outputs": [
                    "chapter_or_section_heading_recovered",
                    "mixed_body_order_stable",
                    "figure_caption_linked_if_present",
                ],
                "gold_label_path": "",
            }
        ],
        "evaluation": {
            "required_metrics": [
                "protected_artifact_precision",
                "protected_artifact_recall",
                "catastrophic_artifact_corruption_count",
                "heading_hierarchy_accuracy",
                "reading_order_accuracy",
                "caption_linkage_success_rate",
                "asset_original_extraction_rate",
                "fallback_render_legibility_rate",
                "manual_review_required_rate",
            ],
            "current_blockers": [
                "Auto-generated draft still needs block-level annotation before measured execution.",
                "Keep this document in benchmark-first mode until annotated_v1 is available.",
            ],
        },
        "recommended_execution_order": [sample_id],
        "auto_probe": {
            "page_count": page_count,
            "selected_pages": selected_pages,
            "page_probes": [
                {
                    "page_number": probe.page_number,
                    "word_count": probe.word_count,
                    "image_count": probe.image_count,
                    "drawing_count": probe.drawing_count,
                    "preview_lines": probe.preview_lines,
                }
                for probe in probes
            ],
        },
    }
    return manifest, gold_label


def write_draft_files(
    *,
    manifest: dict[str, Any],
    gold_label: dict[str, Any],
    review_root: Path,
) -> tuple[Path, Path]:
    sample_id = str(gold_label["sample_id"])
    gold_label_path = review_root / "gold-labels" / f"{sample_id}.json"
    manifest_path = review_root / f"{manifest['benchmark_name']}.yaml"
    manifest["samples"][0]["gold_label_path"] = str(gold_label_path.resolve())
    gold_label_path.parent.mkdir(parents=True, exist_ok=True)
    gold_label_path.write_text(json.dumps(gold_label, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return manifest_path, gold_label_path


# ---------------------------------------------------------------------------
# Auto-annotation: parse PDF probe pages and generate gold blocks
# ---------------------------------------------------------------------------

_HEADING_FONT_SIZE_THRESHOLD = 13.0
_CAPTION_PREFIXES = ("figure", "fig.", "fig ", "table", "listing", "example", "exhibit")


@dataclass(slots=True)
class _ExtractedSpan:
    text: str
    font_size: float
    font_flags: int
    bbox: tuple[float, float, float, float]


def _extract_page_spans(page: Any) -> list[_ExtractedSpan]:
    """Extract text spans with font metadata from a fitz page."""
    spans: list[_ExtractedSpan] = []
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
    for block in blocks:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if not text:
                    continue
                spans.append(
                    _ExtractedSpan(
                        text=text,
                        font_size=float(span.get("size", 0)),
                        font_flags=int(span.get("flags", 0)),
                        bbox=tuple(span["bbox"]),
                    )
                )
    return spans


def _classify_text_block(text: str, max_font_size: float, *, is_bold: bool) -> tuple[str, int | None]:
    """Return (gold_role, heading_level) for a text block."""
    stripped = text.strip()
    lowered = stripped.lower()
    if lowered.startswith(_CAPTION_PREFIXES):
        return "caption", None
    if max_font_size >= _HEADING_FONT_SIZE_THRESHOLD + 6:
        return "heading", 1
    if max_font_size >= _HEADING_FONT_SIZE_THRESHOLD + 2:
        return "heading", 2
    if max_font_size >= _HEADING_FONT_SIZE_THRESHOLD or (is_bold and len(stripped.split()) < 15):
        return "heading", 3
    return "paragraph", None


def auto_annotate_gold_label_from_pdf(
    document_path: Path,
    gold_label: dict[str, Any],
) -> dict[str, Any]:
    """Parse the probe pages in *gold_label* and populate blocks + promote to annotated_v1."""
    pages = gold_label.get("slice_scope", {}).get("pages", [])
    if not pages:
        return gold_label

    blocks: list[dict[str, Any]] = []
    reading_order = 0

    with fitz.open(str(document_path)) as doc:
        for page_number in pages:
            if page_number < 1 or page_number > doc.page_count:
                continue
            page = doc.load_page(page_number - 1)

            # ---- images / drawings -> figure blocks ----
            images = page.get_images(full=True)
            for img_idx, img in enumerate(images):
                rects = page.get_image_rects(img[0])
                if not rects:
                    continue
                rect = rects[0]
                if rect.width < 40 or rect.height < 40:
                    continue
                reading_order += 1
                block_ref = f"p{page_number}-fig-auto-{img_idx + 1}"
                blocks.append({
                    "block_ref": block_ref,
                    "page_number": page_number,
                    "reading_order_index": reading_order,
                    "source_bbox": [round(rect.x0, 3), round(rect.y0, 3), round(rect.x1, 3), round(rect.y1, 3)],
                    "source_selector": None,
                    "gold_role": "figure",
                    "heading_level": None,
                    "protected": True,
                    "linked_artifact_block_ref": None,
                    "linked_caption_block_ref": None,
                    "linked_footnote_anchor": None,
                    "expected_render_mode": "protect",
                    "notes": f"Auto-extracted image on page {page_number}.",
                })

            # ---- text blocks ----
            text_blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
            for blk in text_blocks:
                if blk.get("type") != 0:
                    continue
                lines = blk.get("lines", [])
                if not lines:
                    continue
                full_text_parts: list[str] = []
                max_font_size = 0.0
                has_bold = False
                for line in lines:
                    for span in line.get("spans", []):
                        t = span.get("text", "").strip()
                        if t:
                            full_text_parts.append(t)
                            fs = float(span.get("size", 0))
                            if fs > max_font_size:
                                max_font_size = fs
                            if int(span.get("flags", 0)) & (1 << 4):
                                has_bold = True
                full_text = " ".join(full_text_parts)
                if not full_text.strip():
                    continue

                bbox = blk["bbox"]
                role, heading_level = _classify_text_block(full_text, max_font_size, is_bold=has_bold)

                reading_order += 1
                block_ref = f"p{page_number}-{role}-auto-{reading_order}"

                # Detect if this caption follows a figure on the same page
                linked_artifact_ref = None
                if role == "caption" and blocks:
                    for prev in reversed(blocks):
                        if prev["page_number"] == page_number and prev["gold_role"] == "figure":
                            linked_artifact_ref = prev["block_ref"]
                            prev["linked_caption_block_ref"] = block_ref
                            break

                protected = role == "figure"
                render_mode = {
                    "heading": "zh_markdown_heading",
                    "caption": "zh_caption",
                    "figure": "protect",
                }.get(role, "zh_paragraph")

                blocks.append({
                    "block_ref": block_ref,
                    "page_number": page_number,
                    "reading_order_index": reading_order,
                    "source_bbox": [round(bbox[0], 3), round(bbox[1], 3), round(bbox[2], 3), round(bbox[3], 3)],
                    "source_selector": None,
                    "gold_role": role,
                    "heading_level": heading_level,
                    "protected": protected,
                    "linked_artifact_block_ref": linked_artifact_ref,
                    "linked_caption_block_ref": None,
                    "linked_footnote_anchor": None,
                    "expected_render_mode": render_mode,
                    "notes": f"Auto-annotated {role} from page {page_number}.",
                })

    gold_label["blocks"] = blocks
    gold_label["status"] = "annotated_v1"
    gold_label["todo"] = [
        "Auto-annotated by auto_annotate_gold_label_from_pdf. Review block boundaries if needed.",
    ]
    return gold_label


def auto_annotate_and_write(gold_label_path: Path) -> dict[str, Any]:
    """Load a stub gold label, auto-annotate it, and write it back."""
    gold_label = json.loads(gold_label_path.read_text(encoding="utf-8"))
    if gold_label.get("status") != "stub_pending_annotation":
        return gold_label
    document_path = Path(gold_label["document_path"])
    if not document_path.exists():
        raise FileNotFoundError(f"Document not found: {document_path}")
    gold_label = auto_annotate_gold_label_from_pdf(document_path, gold_label)
    gold_label_path.write_text(json.dumps(gold_label, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return gold_label
