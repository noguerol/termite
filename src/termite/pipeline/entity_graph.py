"""Entity cross-reference graph module."""

from collections import defaultdict

from termite.config import CrossReferenceConfig
from termite.models import EntityCrossReference, ParsedDocument
from termite.pipeline.entity_extractor import EntityExtractor


class EntityGraph:
    """Builds and manages entity cross-reference graph."""

    def __init__(self, config: CrossReferenceConfig | None = None):
        """Initialize the entity graph.

        Args:
            config: Cross-reference configuration.
        """
        if config is None:
            config = CrossReferenceConfig()

        self.min_common_entities = config.min_common_entities
        self.max_refs_per_doc = config.max_refs_per_doc
        self.enabled = config.enabled

        self._doc_entities: dict[str, set[str]] = defaultdict(set)
        self._entity_docs: dict[str, set[str]] = defaultdict(set)
        self._cross_refs: dict[str, list[EntityCrossReference]] = defaultdict(list)

    def build_graph(
        self,
        documents: list[ParsedDocument],
        extractor: EntityExtractor | None = None,
    ) -> "EntityGraph":
        """Build cross-reference graph from documents.

        Args:
            documents: List of documents to analyze.
            extractor: Entity extractor to use.

        Returns:
            Self for chaining.
        """
        if not self.enabled:
            return self

        if extractor is None:
            extractor = EntityExtractor()

        # Extract entities for each document
        for doc in documents:
            entities = extractor.extract_from_document(doc)
            entity_keys = set()

            for ent in entities:
                key = f"{ent.text.lower()}|{ent.label}"
                entity_keys.add(key)
                self._entity_docs[key].add(doc.doc_id)

            self._doc_entities[doc.doc_id] = entity_keys

        # Build cross-references
        self._build_cross_references()

        return self

    def _build_cross_references(self) -> None:
        """Build cross-references between documents.

        Candidate discovery uses an inverted index (entity -> documents)
        so only pairs sharing at least one entity are considered, and the
        number of shared entities for each pair is accumulated in a
        counter. This replaces the previous full pairwise set-intersection
        pass, which was quadratic in corpus size with a large constant.
        Worst-case complexity remains quadratic (e.g., a single entity
        shared by every document), but typical corpora — where most
        documents share no entities — process near-linearly.
        """
        from collections import Counter

        doc_ids = list(self._doc_entities.keys())

        # Inverted index: entity key -> list of document positions
        # (positions follow doc_ids order, so pair indices are ordered).
        entity_positions: dict[str, list[int]] = defaultdict(list)
        for position, doc_id in enumerate(doc_ids):
            for key in self._doc_entities[doc_id]:
                entity_positions[key].append(position)

        # Accumulate shared-entity counts per document pair.
        pair_counts: Counter[tuple[int, int]] = Counter()
        for positions in entity_positions.values():
            for a_pos, a in enumerate(positions):
                for b in positions[a_pos + 1 :]:
                    pair_counts[(a, b)] += 1

        # Group qualifying candidate pairs by source document.
        candidates_by_source: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for (i, j), shared in pair_counts.items():
            if shared >= self.min_common_entities:
                candidates_by_source[i].append((j, shared))

        for source_pos, candidates in candidates_by_source.items():
            source_doc = doc_ids[source_pos]
            entities_a = self._doc_entities[doc_ids[source_pos]]

            scored: list[tuple[float, int, list[str]]] = []
            for target_pos, shared in candidates:
                entities_b = self._doc_entities[doc_ids[target_pos]]
                common = entities_a & entities_b
                union_size = len(entities_a | entities_b)
                strength = shared / union_size if union_size else 0.0
                names = sorted(key.split("|")[0] for key in common)
                scored.append((strength, target_pos, names))

            # Sort by strength (desc), deterministic tie-break by position
            scored.sort(key=lambda item: (-item[0], item[1]))

            for strength, target_pos, names in scored[: self.max_refs_per_doc]:
                cross_ref = EntityCrossReference(
                    source_doc_id=source_doc,
                    target_doc_id=doc_ids[target_pos],
                    common_entities=names[:5],  # Limit entity names
                    reference_strength=strength,
                )
                self._cross_refs[source_doc].append(cross_ref)

    def find_cross_references(self, doc_id: str) -> list[EntityCrossReference]:
        """Find cross-references for a document.

        Args:
            doc_id: Document ID to find references for.

        Returns:
            List of cross-references.
        """
        return self._cross_refs.get(doc_id, [])

    def get_connected_documents(self, doc_id: str) -> list[str]:
        """Get list of document IDs connected to this document.

        Args:
            doc_id: Source document ID.

        Returns:
            List of connected document IDs.
        """
        refs = self.find_cross_references(doc_id)
        return [ref.target_doc_id for ref in refs]

    def inject_cross_references(
        self,
        document: ParsedDocument,
        doc_title_map: dict[str, str] | None = None,
    ) -> ParsedDocument:
        """Inject cross-reference comments into document chunks.

        Args:
            document: Document to inject references into.
            doc_title_map: Mapping of doc_id to title for display.

        Returns:
            Document with cross-references injected.
        """
        if not self.enabled:
            return document

        if doc_title_map is None:
            doc_title_map = {}

        refs = self.find_cross_references(document.doc_id)
        if not refs:
            return document

        # Build reference comment
        ref_parts = []
        for ref in refs:
            target_title = doc_title_map.get(ref.target_doc_id, ref.target_doc_id)
            entities_str = ", ".join(ref.common_entities[:3])
            if entities_str:
                ref_parts.append(f"{target_title} ({entities_str})")
            else:
                ref_parts.append(target_title)

        comment = f"<!-- CROSS-REF: See also: {', '.join(ref_parts)} -->"

        # Inject into first chunk
        if document.chunks:
            first_chunk = document.chunks[0]
            updated_content = f"{comment}\n\n{first_chunk.content}"

            updated_chunk = first_chunk.model_copy(update={"content": updated_content})

            updated_chunks = [updated_chunk, *document.chunks[1:]]
            return document.model_copy(update={"chunks": updated_chunks})

        return document

    def get_statistics(self) -> dict:
        """Get graph statistics.

        Returns:
            Dictionary with graph statistics.
        """
        total_refs = sum(len(refs) for refs in self._cross_refs.values())
        docs_with_refs = sum(1 for refs in self._cross_refs.values() if refs)

        return {
            "total_documents": len(self._doc_entities),
            "total_entities": len(self._entity_docs),
            "total_cross_references": total_refs,
            "documents_with_references": docs_with_refs,
            "avg_references_per_doc": (total_refs / docs_with_refs if docs_with_refs > 0 else 0),
        }

    def clear(self) -> None:
        """Clear the graph data."""
        self._doc_entities.clear()
        self._entity_docs.clear()
        self._cross_refs.clear()
