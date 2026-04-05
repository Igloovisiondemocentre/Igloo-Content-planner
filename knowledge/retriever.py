from __future__ import annotations

from collections import defaultdict

from igloo_experience_builder.knowledge.taxonomy import request_concepts
from igloo_experience_builder.knowledge.text_utils import navigation_penalty, tokenize
from igloo_experience_builder.models import EvidenceIndex, EvidenceStrength, RankedEvidence, SourceType


STRENGTH_WEIGHTS = {
    EvidenceStrength.HARD: 4.0,
    EvidenceStrength.MEDIUM: 1.0,
    EvidenceStrength.WEAK: 0.1,
}

SOURCE_WEIGHTS = {
    SourceType.RUNTIME_API: 2.2,
    SourceType.PLATFORM_DOC: 1.8,
    SourceType.INTERNAL_PDF: 0.8,
}


class DeterministicRetriever:
    def __init__(self, index: EvidenceIndex) -> None:
        self.index = index

    def search(self, question: str, limit: int = 8) -> list[RankedEvidence]:
        query_tokens = set(tokenize(question))
        query_concepts = set(request_concepts(question))
        scored: list[RankedEvidence] = []
        per_source_count: dict[str, int] = defaultdict(int)
        for fragment in self.index.fragments:
            fragment_tokens = set(fragment.tokens) | set(tokenize(fragment.text)) | set(tokenize(fragment.title))
            token_overlap = min(len(query_tokens & fragment_tokens), 3)
            concept_overlap = min(len(query_concepts & set(fragment.concept_tags)), 3)
            title_overlap = min(len(query_tokens & set(tokenize(fragment.title))), 2)
            explicit_phrase_bonus = sum(1 for concept in query_concepts if concept in fragment.concept_tags)
            chrome_penalty = navigation_penalty(fragment.text)
            if token_overlap == 0 and concept_overlap == 0 and title_overlap == 0:
                continue
            score = (
                token_overlap * 2.0
                + concept_overlap * 4.0
                + title_overlap * 1.5
                + explicit_phrase_bonus * 0.8
                + STRENGTH_WEIGHTS[fragment.evidence_strength]
                + SOURCE_WEIGHTS[fragment.source_type]
                + fragment.source_priority
                - chrome_penalty * 1.2
            )
            scored.append(RankedEvidence(fragment=fragment, score=score))
        ranked = sorted(scored, key=lambda item: item.score, reverse=True)
        filtered: list[RankedEvidence] = []
        for item in ranked:
            if per_source_count[item.fragment.source_id] >= 3:
                continue
            filtered.append(item)
            per_source_count[item.fragment.source_id] += 1
            if len(filtered) >= limit:
                break
        covered_concepts = {concept for item in filtered for concept in item.fragment.concept_tags}
        missing_concepts = [concept for concept in query_concepts if concept not in covered_concepts]
        existing_ids = {item.fragment.fragment_id for item in filtered}
        for concept in missing_concepts:
            for item in ranked:
                if item.fragment.fragment_id in existing_ids:
                    continue
                if concept not in item.fragment.concept_tags:
                    continue
                filtered.append(item)
                existing_ids.add(item.fragment.fragment_id)
                break
        return filtered
