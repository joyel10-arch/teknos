"""
confidence.py — Evidence Confidence computation.

WHAT: Computes the Evidence Confidence score (C) for each BehaviourEvent.
      C = 0.45*D + 0.30*T + 0.25*R  (clamped to [0,1], rounded to 2 dp)

Components:
  D = mean YOLO detection confidence of the entity over the event window
      (ranges 0–1; comes from the raw per-box scores, NOT from this module)
  T = track continuity = observed_frames / expected_frames in the event window
      (1.0 = no missing frames; < 1.0 = gaps existed)
  R = rule-evidence strength (0–1), defined per rule:
      - restricted_entry : fraction of next N frames person stays inside (capped at 1)
      - loitering        : (dwell_margin + speed_margin) / 2
                           dwell_margin  = min(1, dwell / (2 * threshold))
                           speed_margin  = 1 - observed_speed / threshold
      - wrong_direction  : min(1, reverse_travel / (2 * min_travel))
      - normal_walkthrough: fixed 0.7 (informational; not a risk event)

IMPORTANT: This score is called "Evidence Confidence" everywhere and MUST NOT
be described as a probability of danger, threat level, or likelihood of criminal
intent.  It quantifies how well the evidence supports the rule-based detection.
"""

from __future__ import annotations

import logging

from app.services.behaviour_engine import BehaviourEvent

logger = logging.getLogger(__name__)

# Weights (must sum to 1.0)
W_D = 0.45   # detection confidence weight
W_T = 0.30   # track continuity weight
W_R = 0.25   # rule-evidence strength weight


def compute_confidence(
    event: BehaviourEvent,
    w_d: float = W_D,
    w_t: float = W_T,
    w_r: float = W_R,
) -> float:
    """Compute and store Evidence Confidence for *event*.  Returns C.

    Also stores D, T, R components inside event.evidence["observed_values"]
    so the score is fully explainable (every number can be traced back to
    raw data).
    """
    # ── D: mean detection confidence ─────────────────────────────────────────
    confs = event._det_confidences
    d_score = float(sum(confs) / len(confs)) if confs else 0.5
    d_score = max(0.0, min(1.0, d_score))

    # ── T: track continuity ──────────────────────────────────────────────────
    if event._expected_frames > 0:
        t_score = min(1.0, event._observed_frames / event._expected_frames)
    else:
        t_score = 1.0

    # ── R: rule-evidence strength (pre-computed by behaviour rules) ───────────
    r_score = float(event.evidence.get("_r_strength", 0.5))
    r_score = max(0.0, min(1.0, r_score))

    # ── Weighted sum ─────────────────────────────────────────────────────────
    c = w_d * d_score + w_t * t_score + w_r * r_score
    c = round(max(0.0, min(1.0, c)), 2)

    # ── Store components for explainability ───────────────────────────────────
    event.evidence.setdefault("observed_values", {}).update({
        "evidence_confidence_D_detection": round(d_score, 4),
        "evidence_confidence_T_track_continuity": round(t_score, 4),
        "evidence_confidence_R_rule_strength": round(r_score, 4),
        "evidence_confidence_C_final": c,
        "confidence_formula": f"C = {w_d}*{d_score:.4f} + {w_t}*{t_score:.4f} + {w_r}*{r_score:.4f} = {c}",
    })

    event.confidence = c
    logger.debug(
        "%s %s: D=%.3f T=%.3f R=%.3f -> C=%.2f",
        event.entity_id, event.event_type, d_score, t_score, r_score, c,
    )
    return c


def compute_all_confidences(
    events: list[BehaviourEvent],
    w_d: float = W_D,
    w_t: float = W_T,
    w_r: float = W_R,
) -> None:
    """In-place: compute confidence for every event in the list."""
    for evt in events:
        compute_confidence(evt, w_d, w_t, w_r)
    logger.info("Computed evidence confidence for %d events", len(events))
