"""Eight comparison group configurations."""

from prototype.conflict.resolver import ResolverConfig


def build_groups() -> list[ResolverConfig]:
    """Build the 8 comparison groups for the experiment."""

    return [
        # Group 1: Baseline - simple last-write-wins, no detection, no strategies
        ResolverConfig(
            name="1_Baseline",
            use_detection=False,
            use_timestamp=False,
            use_trust_score=False,
            use_leader=False,
            use_judge=False,
            use_pre_filter=False,
            consistency_mode="none"
        ),

        # Group 2: Strong consistency only - no strategies, no Judge
        ResolverConfig(
            name="2_StrongOnly",
            use_detection=True,
            use_timestamp=False,
            use_trust_score=False,
            use_leader=False,
            use_judge=False,
            use_pre_filter=False,
            consistency_mode="strong"
        ),

        # Group 3: Timestamp priority only
        ResolverConfig(
            name="3_TimestampPriority",
            use_detection=True,
            use_timestamp=True,
            use_trust_score=False,
            use_leader=False,
            use_judge=False,
            use_pre_filter=True,
            consistency_mode="none"
        ),

        # Group 4: Trust score priority only
        ResolverConfig(
            name="4_TrustScorePriority",
            use_detection=True,
            use_timestamp=False,
            use_trust_score=True,
            use_leader=False,
            use_judge=False,
            use_pre_filter=True,
            consistency_mode="none"
        ),

        # Group 5: Leader mediation only
        ResolverConfig(
            name="5_LeaderMediation",
            use_detection=True,
            use_timestamp=False,
            use_trust_score=False,
            use_leader=True,
            use_judge=False,
            use_pre_filter=True,
            consistency_mode="none"
        ),

        # Group 6: Ablation 1 — no Judge Agent (hierarchical + structural strategies only)
        ResolverConfig(
            name="6_Ablation1_NoJudge",
            use_detection=True,
            use_timestamp=True,
            use_trust_score=True,
            use_leader=True,
            use_judge=False,
            use_pre_filter=True,
            consistency_mode="hierarchical"
        ),

        # Group 7: Ablation 2 — no structural pre-filter (hierarchical + all strategies + Judge)
        ResolverConfig(
            name="7_Ablation2_NoPreFilter",
            use_detection=True,
            use_timestamp=True,
            use_trust_score=True,
            use_leader=True,
            use_judge=True,
            use_pre_filter=False,
            consistency_mode="hierarchical"
        ),

        # Group 8: Full proposed approach
        ResolverConfig(
            name="8_FullProposed",
            use_detection=True,
            use_timestamp=True,
            use_trust_score=True,
            use_leader=True,
            use_judge=True,
            use_pre_filter=True,
            consistency_mode="hierarchical"
        ),
    ]
