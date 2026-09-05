"""Human correction and outcome recording service (spec sections 10, 11, 13, 17)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.models.human_correction import HumanCorrection
from app.domain.schemas import HumanCorrectionStatsRead, OverrideStatsCategory


def is_override_decision(original: str, human: str) -> bool:
    """Determine whether human decision overrides the original system recommendation."""
    orig = original.strip().upper()
    hum = human.strip().upper()

    if orig in ("STAGE", "AUTO_RESOLVE", "EXECUTE", "RECOMMEND", "APPROVE"):
        return hum in ("REJECT", "REJECTED", "OVERRIDE", "DISMISSED", "DENIED")
    if orig in ("REJECT", "REJECTED", "REFUSE"):
        return hum in ("APPROVE", "APPROVED", "OVERRIDE", "RESOLVED")
    return orig != hum


def get_confidence_bucket(conf: Decimal | float | None) -> str:
    """Classify confidence score into statistical tracking buckets."""
    if conf is None:
        return "UNKNOWN"
    val = float(conf)
    if val >= 0.95:
        return "HIGH (>=0.95)"
    if val >= 0.80:
        return "MEDIUM (0.80-0.94)"
    return "LOW (<0.80)"


class HumanCorrectionService:
    """Manages human outcome recording, override metrics, and policy tuning candidates."""

    def __init__(self, session: AsyncSession, company_id: uuid.UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def record_correction(
        self,
        *,
        exception_id: uuid.UUID,
        original_decision: str,
        human_decision: str,
        close_run_id: uuid.UUID | None = None,
        original_confidence: Decimal | None = None,
        calibrated_confidence: Decimal | None = None,
        exception_type: str = "UNKNOWN",
        policy_version_id: str | None = None,
        reviewer_role: str = "controller",
        actor: str = "controller",
        reason: str | None = None,
    ) -> HumanCorrection:
        """Record an explicit human review decision on an exception."""
        correction = HumanCorrection(
            company_id=self.company_id,
            exception_id=exception_id,
            close_run_id=close_run_id,
            original_decision=original_decision,
            human_decision=human_decision,
            original_confidence=original_confidence,
            calibrated_confidence=calibrated_confidence,
            exception_type=exception_type,
            policy_version_id=policy_version_id,
            reviewer_role=reviewer_role,
            actor=actor,
            reason=reason,
            created_at=utcnow(),
        )
        self.session.add(correction)
        await self.session.flush()
        return correction

    async def list_corrections(
        self, exception_id: uuid.UUID | None = None
    ) -> Sequence[HumanCorrection]:
        """List human correction records for company, optionally filtered by exception."""
        stmt = select(HumanCorrection).where(HumanCorrection.company_id == self.company_id)
        if exception_id:
            stmt = stmt.where(HumanCorrection.exception_id == exception_id)
        stmt = stmt.order_by(HumanCorrection.created_at.desc())
        return (await self.session.scalars(stmt)).all()

    async def get_override_statistics(self) -> HumanCorrectionStatsRead:
        """Compute override statistics overall, by exception type, and by confidence bucket."""
        stmt = (
            select(HumanCorrection)
            .where(HumanCorrection.company_id == self.company_id)
            .order_by(HumanCorrection.created_at)
        )
        records = list((await self.session.scalars(stmt)).all())

        total = len(records)
        overrides = sum(
            1 for r in records if is_override_decision(r.original_decision, r.human_decision)
        )
        overall_rate = round(overrides / total, 4) if total > 0 else 0.0
        overall_candidate = total >= 5 and overall_rate > 0.20

        overall_stat = OverrideStatsCategory(
            total_decisions=total,
            overrides=overrides,
            override_rate=overall_rate,
            tuning_candidate=overall_candidate,
        )

        # By exception type
        type_counts: dict[str, list[bool]] = {}
        for r in records:
            etype = r.exception_type or "UNKNOWN"
            type_counts.setdefault(etype, []).append(
                is_override_decision(r.original_decision, r.human_decision)
            )

        by_type: dict[str, OverrideStatsCategory] = {}
        for etype, flags in type_counts.items():
            tot = len(flags)
            ovr = sum(1 for f in flags if f)
            rate = round(ovr / tot, 4) if tot > 0 else 0.0
            by_type[etype] = OverrideStatsCategory(
                total_decisions=tot,
                overrides=ovr,
                override_rate=rate,
                tuning_candidate=(tot >= 5 and rate > 0.20),
            )

        # By confidence bucket
        bucket_counts: dict[str, list[bool]] = {}
        for r in records:
            bucket = get_confidence_bucket(r.calibrated_confidence or r.original_confidence)
            bucket_counts.setdefault(bucket, []).append(
                is_override_decision(r.original_decision, r.human_decision)
            )

        by_bucket: dict[str, OverrideStatsCategory] = {}
        for bucket, flags in bucket_counts.items():
            tot = len(flags)
            ovr = sum(1 for f in flags if f)
            rate = round(ovr / tot, 4) if tot > 0 else 0.0
            by_bucket[bucket] = OverrideStatsCategory(
                total_decisions=tot,
                overrides=ovr,
                override_rate=rate,
                tuning_candidate=(tot >= 5 and rate > 0.20),
            )

        tuning_candidates = [
            f"exception_type:{t}" for t, cat in by_type.items() if cat.tuning_candidate
        ] + [f"confidence_bucket:{b}" for b, cat in by_bucket.items() if cat.tuning_candidate]

        return HumanCorrectionStatsRead(
            overall=overall_stat,
            by_exception_type=by_type,
            by_confidence_bucket=by_bucket,
            tuning_candidates=tuning_candidates,
        )
