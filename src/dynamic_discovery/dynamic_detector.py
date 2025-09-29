"""Core dynamic structural migration detector."""

import difflib
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

try:
    from ..diff_analyzer import DiffAnalyzer
    from .semantic_analyzer import SemanticAnalyzer
except ImportError:
    import os
    import sys

    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from diff_analyzer import DiffAnalyzer
    from semantic_analyzer import SemanticAnalyzer


@dataclass
class MigrationCandidate:
    """Represents a potential migration target for orphaned data."""

    new_path: str
    similarity_type: str
    similarity_score: float
    evidence: str
    requires_human_review: bool = False
    field_mapping: Optional[Dict[str, str]] = None
    metadata_additions: Optional[Dict[str, Any]] = None


@dataclass
class DiscoveredMigration:
    """Represents a discovered structural migration."""

    old_path: str
    custom_value: Any
    candidates: List[MigrationCandidate]
    best_candidate: Optional[MigrationCandidate]
    confidence: float
    migration_type: str


class DynamicStructuralDetector:
    """Automatically discover structural migrations through semantic analysis."""

    def __init__(self, enable_verbose_logging: bool = False) -> None:
        """Initialize the dynamic detector.

        Args:
            enable_verbose_logging: Enable detailed logging for analysis steps.
        """
        self.diff_analyzer = DiffAnalyzer()
        self.semantic_analyzer = SemanticAnalyzer()
        self.verbose = enable_verbose_logging

        # Confidence thresholds for different actions
        self.auto_apply_threshold = 0.8
        self.suggest_threshold = 0.5

    def discover_structural_migrations(
        self,
        golden_config: Dict[str, Any],
        template_old: Dict[str, Any],
        template_new: Dict[str, Any],
    ) -> List[DiscoveredMigration]:
        """Discover potential structural migrations automatically.

        Args:
            golden_config: Original production configuration with custom values.
            template_old: Old template configuration.
            template_new: New template configuration.

        Returns:
            List of discovered migration opportunities.
        """
        if self.verbose:
            print("🔍 Starting dynamic structural migration discovery...")

        # Step 1: Find orphaned custom data
        orphaned_data = self._find_orphaned_custom_data(
            golden_config, template_old, template_new
        )

        if self.verbose:
            print(f"📊 Found {len(orphaned_data)} orphaned configuration paths")

        # Step 2: Analyze each orphaned path for migration opportunities
        discovered_migrations = []

        for old_path, custom_value in orphaned_data.items():
            if self.verbose:
                print(f"🔎 Analyzing: {old_path}")

            migration = self._analyze_migration_opportunity(
                old_path, custom_value, template_new
            )

            if migration.candidates:
                discovered_migrations.append(migration)
                if self.verbose:
                    print(
                        f"✅ Found {len(migration.candidates)} candidates for {old_path}"
                    )

        # Step 3: Rank and prioritize migrations
        discovered_migrations = self._prioritize_migrations(discovered_migrations)

        if self.verbose:
            print(
                f"🎯 Discovery complete: {len(discovered_migrations)} migrations found"
            )

        return discovered_migrations

    def _find_orphaned_custom_data(
        self,
        golden_config: Dict[str, Any],
        template_old: Dict[str, Any],
        template_new: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Find custom data that exists in golden config but has no home in new template.

        Args:
            golden_config: Golden configuration with custom values.
            template_old: Old template baseline.
            template_new: New template target.

        Returns:
            Dictionary mapping orphaned paths to their custom values.
        """
        # Extract all custom data from golden config
        custom_data = self.diff_analyzer.extract_custom_data(
            golden_config, template_old
        )

        # Find which custom data paths don't exist in new template
        orphaned_data = {}

        for path, custom_value in custom_data.items():
            if not self.diff_analyzer.path_exists(template_new, path):
                orphaned_data[path] = custom_value

        return orphaned_data

    def _analyze_migration_opportunity(
        self, old_path: str, custom_value: Any, template_new: Dict[str, Any]
    ) -> DiscoveredMigration:
        """Analyze a single orphaned path for migration opportunities.

        Args:
            old_path: The orphaned configuration path.
            custom_value: The custom value at that path.
            template_new: New template to search for candidates.

        Returns:
            DiscoveredMigration with candidate analysis.
        """
        candidates = []

        # Strategy 1: Field name similarity
        candidates.extend(self._find_by_field_similarity(old_path, template_new))

        # Strategy 2: Value pattern matching
        candidates.extend(
            self._find_by_value_pattern(old_path, custom_value, template_new)
        )

        # Strategy 3: Structural similarity
        candidates.extend(self._find_by_structural_similarity(old_path, template_new))

        # Strategy 4: Semantic context analysis
        candidates.extend(self._find_by_semantic_context(old_path, template_new))

        # Deduplicate and score candidates
        candidates = self._deduplicate_and_score_candidates(candidates)

        # Determine best candidate and migration type
        best_candidate = candidates[0] if candidates else None
        confidence = best_candidate.similarity_score if best_candidate else 0.0
        migration_type = self._determine_migration_type(old_path, best_candidate)

        return DiscoveredMigration(
            old_path=old_path,
            custom_value=custom_value,
            candidates=candidates,
            best_candidate=best_candidate,
            confidence=confidence,
            migration_type=migration_type,
        )

    def _find_by_field_similarity(
        self, old_path: str, template_new: Dict[str, Any]
    ) -> List[MigrationCandidate]:
        """Find candidates based on field name similarity.

        Args:
            old_path: Original configuration path.
            template_new: New template to search.

        Returns:
            List of candidates based on field name similarity.
        """
        candidates = []
        old_parts = old_path.split(".")
        old_field_name = old_parts[-1]

        all_new_paths = self._get_all_paths(template_new)

        for new_path in all_new_paths:
            new_parts = new_path.split(".")
            new_field_name = new_parts[-1]

            # Calculate similarity ratio
            similarity = difflib.SequenceMatcher(
                None, old_field_name, new_field_name
            ).ratio()

            if similarity > 0.6:  # 60% similarity threshold
                field_mapping = None
                if similarity < 1.0:  # Field name changed
                    field_mapping = {old_field_name: new_field_name}

                candidates.append(
                    MigrationCandidate(
                        new_path=new_path,
                        similarity_type="field_name",
                        similarity_score=similarity,
                        evidence=f"Field name: '{old_field_name}' → '{new_field_name}' ({similarity:.2f})",
                        requires_human_review=similarity < 0.8,
                        field_mapping=field_mapping,
                    )
                )

        return candidates

    def _find_by_value_pattern(
        self, old_path: str, custom_value: Any, template_new: Dict[str, Any]
    ) -> List[MigrationCandidate]:
        """Find candidates by analyzing value patterns and types.

        Args:
            old_path: Original configuration path.
            custom_value: The custom value to find a new home for.
            template_new: New template to search.

        Returns:
            List of candidates based on value compatibility.
        """
        candidates = []
        value_signature = self._create_value_signature(custom_value)

        all_new_paths = self._get_all_paths(template_new)

        for new_path in all_new_paths:
            try:
                new_value = self.diff_analyzer.get_nested_value(template_new, new_path)
                new_signature = self._create_value_signature(new_value)

                compatibility_score = self._calculate_value_compatibility(
                    value_signature, new_signature
                )

                if compatibility_score > 0.5:
                    candidates.append(
                        MigrationCandidate(
                            new_path=new_path,
                            similarity_type="value_pattern",
                            similarity_score=compatibility_score,
                            evidence=f"Value compatibility: {compatibility_score:.2f} (type: {type(custom_value).__name__})",
                            requires_human_review=compatibility_score < 0.7,
                        )
                    )
            except (KeyError, IndexError, TypeError):
                # Skip paths that don't exist or can't be accessed in the new template
                continue

        return candidates

    def _find_by_structural_similarity(
        self, old_path: str, template_new: Dict[str, Any]
    ) -> List[MigrationCandidate]:
        """Find candidates by analyzing surrounding structural context.

        Args:
            old_path: Original configuration path.
            template_new: New template to search.

        Returns:
            List of candidates based on structural similarity.
        """
        candidates = []
        old_parts = old_path.split(".")
        all_new_paths = self._get_all_paths(template_new)

        for new_path in all_new_paths:
            new_parts = new_path.split(".")

            structure_score = self._calculate_structural_similarity(
                old_parts, new_parts
            )

            if structure_score > 0.4:
                common_ancestors = self._find_common_ancestors(old_parts, new_parts)

                candidates.append(
                    MigrationCandidate(
                        new_path=new_path,
                        similarity_type="structural",
                        similarity_score=structure_score,
                        evidence=f"Structural similarity: {structure_score:.2f}, Common: {'/'.join(common_ancestors)}",
                        requires_human_review=structure_score < 0.7,
                    )
                )

        return candidates

    def _find_by_semantic_context(
        self, old_path: str, template_new: Dict[str, Any]
    ) -> List[MigrationCandidate]:
        """Find candidates using semantic understanding of configuration contexts.

        Args:
            old_path: Original configuration path.
            template_new: New template to search.

        Returns:
            List of candidates based on semantic similarity.
        """
        candidates = []

        # Get semantic domain of old path
        old_domain = self.semantic_analyzer.identify_semantic_domain(old_path)

        if not old_domain:
            return candidates

        all_new_paths = self._get_all_paths(template_new)

        for new_path in all_new_paths:
            new_domain = self.semantic_analyzer.identify_semantic_domain(new_path)

            if new_domain and old_domain == new_domain:
                # Calculate semantic similarity score
                semantic_score = self.semantic_analyzer.calculate_semantic_similarity(
                    old_path, new_path
                )

                candidates.append(
                    MigrationCandidate(
                        new_path=new_path,
                        similarity_type="semantic_context",
                        similarity_score=semantic_score,
                        evidence=f"Semantic domain: '{old_domain}', Similarity: {semantic_score:.2f}",
                        requires_human_review=semantic_score < 0.8,
                    )
                )

        return candidates

    def _create_value_signature(self, value: Any) -> Dict[str, Any]:
        """Create a signature describing value characteristics.

        Args:
            value: Value to analyze.

        Returns:
            Dictionary describing value characteristics.
        """
        if isinstance(value, str):
            patterns = {
                "service_account": bool(
                    re.search(r"serviceaccount|service-account", value, re.I)
                ),
                "has_dashes": "-" in value,
                "has_numbers": bool(re.search(r"\\d", value)),
                "length_category": "short"
                if len(value) < 10
                else "medium"
                if len(value) < 30
                else "long",
                "has_domain": bool(re.search(r"\\.[a-z]{2,}", value)),
                "is_uuid_like": bool(
                    re.search(
                        r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
                        value,
                        re.I,
                    )
                ),
            }
            return {"type": "string", "patterns": patterns, "length": len(value)}

        elif isinstance(value, bool):
            return {"type": "boolean", "value": value}

        elif isinstance(value, (int, float)):
            return {
                "type": "number",
                "value_range": "small" if abs(value) < 100 else "large",
            }

        elif isinstance(value, dict):
            keys = sorted(value.keys())
            return {"type": "dict", "keys": keys, "key_count": len(keys)}

        elif isinstance(value, list):
            return {
                "type": "list",
                "length": len(value),
                "item_types": [type(item).__name__ for item in value[:3]],
            }

        return {"type": type(value).__name__}

    def _calculate_value_compatibility(
        self, sig1: Dict[str, Any], sig2: Dict[str, Any]
    ) -> float:
        """Calculate compatibility score between two value signatures.

        Args:
            sig1: First value signature.
            sig2: Second value signature.

        Returns:
            Compatibility score between 0.0 and 1.0.
        """
        # Type compatibility is most important
        if sig1["type"] != sig2["type"]:
            return 0.0

        # String pattern matching
        if sig1["type"] == "string" and "patterns" in sig1 and "patterns" in sig2:
            pattern_matches = sum(
                1
                for key in sig1["patterns"]
                if key in sig2["patterns"]
                and sig1["patterns"][key] == sig2["patterns"][key]
            )
            pattern_score = pattern_matches / max(
                len(sig1["patterns"]), len(sig2["patterns"])
            )

            # Length similarity for strings
            len1, len2 = sig1.get("length", 0), sig2.get("length", 0)
            length_score = 1 - abs(len1 - len2) / max(len1, len2, 1)

            return pattern_score * 0.7 + length_score * 0.3

        # Boolean exact match
        elif sig1["type"] == "boolean":
            return 1.0 if sig1.get("value") == sig2.get("value") else 0.5

        # Dictionary structure similarity
        elif sig1["type"] == "dict":
            common_keys = set(sig1.get("keys", [])) & set(sig2.get("keys", []))
            all_keys = set(sig1.get("keys", [])) | set(sig2.get("keys", []))
            return len(common_keys) / len(all_keys) if all_keys else 0.0

        # Default for same type
        return 0.6

    def _calculate_structural_similarity(
        self, old_parts: List[str], new_parts: List[str]
    ) -> float:
        """Calculate similarity between path structures.

        Args:
            old_parts: Parts of the old path.
            new_parts: Parts of the new path.

        Returns:
            Structural similarity score.
        """
        # Factor 1: Common prefix length
        common_prefix = 0
        for i in range(min(len(old_parts), len(new_parts))):
            if old_parts[i] == new_parts[i]:
                common_prefix += 1
            else:
                break

        # Factor 2: Similar depth
        max_depth = max(len(old_parts), len(new_parts))
        depth_similarity = 1 - abs(len(old_parts) - len(new_parts)) / max_depth

        # Factor 3: Common keywords
        old_keywords = set(old_parts)
        new_keywords = set(new_parts)
        keyword_similarity = (
            len(old_keywords & new_keywords) / len(old_keywords | new_keywords)
            if old_keywords | new_keywords
            else 0
        )

        # Weighted combination
        prefix_weight = common_prefix / max_depth
        return prefix_weight * 0.4 + depth_similarity * 0.3 + keyword_similarity * 0.3

    def _find_common_ancestors(self, parts1: List[str], parts2: List[str]) -> List[str]:
        """Find common ancestor path components.

        Args:
            parts1: First path components.
            parts2: Second path components.

        Returns:
            List of common ancestor components.
        """
        common = []
        for i in range(min(len(parts1), len(parts2))):
            if parts1[i] == parts2[i]:
                common.append(parts1[i])
            else:
                break
        return common

    def _deduplicate_and_score_candidates(
        self, candidates: List[MigrationCandidate]
    ) -> List[MigrationCandidate]:
        """Remove duplicates and sort candidates by score.

        Args:
            candidates: List of migration candidates.

        Returns:
            Deduplicated and sorted list of candidates.
        """
        # Group by new_path and keep the best score for each
        best_candidates = {}

        for candidate in candidates:
            if candidate.new_path not in best_candidates:
                best_candidates[candidate.new_path] = candidate
            else:
                # Keep the candidate with higher score
                if (
                    candidate.similarity_score
                    > best_candidates[candidate.new_path].similarity_score
                ):
                    best_candidates[candidate.new_path] = candidate

        # Sort by similarity score (descending)
        sorted_candidates = sorted(
            best_candidates.values(), key=lambda x: x.similarity_score, reverse=True
        )

        return sorted_candidates

    def _determine_migration_type(
        self, old_path: str, best_candidate: Optional[MigrationCandidate]
    ) -> str:
        """Determine the type of migration based on path analysis.

        Args:
            old_path: Original path.
            best_candidate: Best migration candidate.

        Returns:
            String describing migration type.
        """
        if not best_candidate:
            return "no_candidate"

        old_parts = old_path.split(".")
        new_parts = best_candidate.new_path.split(".")

        # Check for different migration patterns
        if len(old_parts) != len(new_parts):
            if len(new_parts) > len(old_parts):
                return "path_expansion"
            else:
                return "path_consolidation"

        elif old_parts[-1] != new_parts[-1]:
            return "field_rename"

        elif old_parts[:-1] != new_parts[:-1]:
            return "structural_relocation"

        else:
            return "direct_mapping"

    def _prioritize_migrations(
        self, migrations: List[DiscoveredMigration]
    ) -> List[DiscoveredMigration]:
        """Prioritize migrations by confidence and impact.

        Args:
            migrations: List of discovered migrations.

        Returns:
            Prioritized list of migrations.
        """
        # Sort by confidence score (descending)
        return sorted(migrations, key=lambda x: x.confidence, reverse=True)

    def _get_all_paths(self, config: Dict[str, Any]) -> Set[str]:
        """Get all configuration paths from a nested dictionary.

        Args:
            config: Configuration dictionary.

        Returns:
            Set of all dot-notation paths.
        """
        paths = set()

        def _traverse(obj: Any, prefix: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{prefix}.{key}" if prefix else key
                    paths.add(current_path)
                    _traverse(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if isinstance(item, dict):
                        current_path = f"{prefix}[{i}]"
                        # Add array index path only if it contains actual content
                        if item:
                            _traverse(item, current_path)

        _traverse(config)
        return paths

    def get_auto_apply_migrations(
        self, migrations: List[DiscoveredMigration]
    ) -> List[DiscoveredMigration]:
        """Get migrations that can be automatically applied.

        Args:
            migrations: List of discovered migrations.

        Returns:
            Migrations suitable for automatic application.
        """
        return [
            migration
            for migration in migrations
            if migration.confidence >= self.auto_apply_threshold
            and migration.best_candidate
            and not migration.best_candidate.requires_human_review
        ]

    def get_suggested_migrations(
        self, migrations: List[DiscoveredMigration]
    ) -> List[DiscoveredMigration]:
        """Get migrations that should be suggested to the user.

        Args:
            migrations: List of discovered migrations.

        Returns:
            Migrations suitable for user review and confirmation.
        """
        return [
            migration
            for migration in migrations
            if self.suggest_threshold
            <= migration.confidence
            < self.auto_apply_threshold
            or (
                migration.best_candidate
                and migration.best_candidate.requires_human_review
            )
        ]
