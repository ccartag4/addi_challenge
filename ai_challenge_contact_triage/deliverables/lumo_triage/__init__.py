"""lumo_triage — contact triage and grounded reply drafting for Lumo's CX team.

Pipeline: normalise -> deterministic rules and entity extraction -> LLM classification
(structured output) -> routing policy (YAML) -> grounded drafting -> code verifier -> batch
summary. See IMPLEMENTATION_PLAN.md and DESIGN.md.
"""

__version__ = "0.1.0"
