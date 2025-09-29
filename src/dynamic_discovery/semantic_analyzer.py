"""Semantic analysis for configuration paths and values."""

import re
from typing import Dict, List, Optional, Set


class SemanticAnalyzer:
    """Analyze semantic context and domain of configuration paths."""

    def __init__(self) -> None:
        """Initialize semantic analyzer with domain definitions."""
        self.semantic_domains = {
            "service_account": [
                "serviceaccount",
                "account",
                "service",
                "auth",
                "identity",
                "authentication",
                "authorization",
                "sa",
                "principal",
            ],
            "network": [
                "network",
                "service",
                "ingress",
                "egress",
                "connectivity",
                "endpoint",
                "port",
                "ip",
                "dns",
                "proxy",
                "gateway",
                "load",
                "balancer",
                "traffic",
                "route",
            ],
            "storage": [
                "storage",
                "volume",
                "disk",
                "pvc",
                "persistent",
                "mount",
                "filesystem",
                "backup",
                "snapshot",
            ],
            "security": [
                "security",
                "tls",
                "ssl",
                "cert",
                "certificate",
                "secret",
                "key",
                "token",
                "encryption",
                "cipher",
                "crypto",
            ],
            "resource": [
                "resource",
                "cpu",
                "memory",
                "limit",
                "request",
                "quota",
                "allocation",
                "usage",
                "capacity",
            ],
            "monitoring": [
                "monitor",
                "metric",
                "prometheus",
                "alert",
                "health",
                "status",
                "log",
                "trace",
                "debug",
            ],
            "database": [
                "database",
                "db",
                "sql",
                "mysql",
                "ndb",
                "cluster",
                "replication",
                "backup",
                "restore",
                "schema",
            ],
            "container": [
                "container",
                "image",
                "pod",
                "deployment",
                "replica",
                "docker",
                "registry",
                "tag",
                "pull",
            ],
            "annotation": ["annotation", "label", "metadata", "tag", "mark"],
            "configuration": [
                "config",
                "setting",
                "parameter",
                "option",
                "value",
                "property",
                "attribute",
                "feature",
                "flag",
            ],
        }

        # Compile regex patterns for efficiency
        self.domain_patterns = {}
        for domain, keywords in self.semantic_domains.items():
            pattern = (
                r"\b(?:" + "|".join(re.escape(keyword) for keyword in keywords) + r")\b"
            )
            self.domain_patterns[domain] = re.compile(pattern, re.IGNORECASE)

        # Context-specific patterns for better domain identification
        self.context_patterns = {
            "service_account": [
                r"serviceaccount.*(?:create|name)",
                r"(?:create|name).*serviceaccount",
                r"account.*(?:upgrade|multus|app)",
                r"auth.*(?:token|principal)",
            ],
            "network": [
                r"service.*(?:labels|annotations|type)",
                r"connectivity.*service",
                r"external.*(?:service|connectivity)",
                r"load.*balancer",
                r"ingress|egress",
            ],
            "database": [
                r"(?:mysql|ndb).*(?:host|port|user)",
                r"replication.*(?:service|host)",
                r"backup.*(?:manager|executor)",
                r"db.*(?:tier|monitor)",
            ],
        }

    def identify_semantic_domain(self, path: str) -> Optional[str]:
        """Identify the semantic domain of a configuration path.

        Args:
            path: Dot-notation configuration path.

        Returns:
            Semantic domain name or None if no clear domain identified.
        """
        path_lower = path.lower()

        # First, try context-specific patterns (more accurate)
        domain_scores = {}

        for domain, patterns in self.context_patterns.items():
            for pattern in patterns:
                if re.search(pattern, path_lower):
                    domain_scores[domain] = domain_scores.get(domain, 0) + 2

        # Then, try keyword matching
        for domain, pattern in self.domain_patterns.items():
            matches = pattern.findall(path_lower)
            if matches:
                domain_scores[domain] = domain_scores.get(domain, 0) + len(matches)

        # Return domain with highest score
        if domain_scores:
            return max(domain_scores.items(), key=lambda x: x[1])[0]

        return None

    def calculate_semantic_similarity(self, path1: str, path2: str) -> float:
        """Calculate semantic similarity between two configuration paths.

        Args:
            path1: First configuration path.
            path2: Second configuration path.

        Returns:
            Semantic similarity score between 0.0 and 1.0.
        """
        domain1 = self.identify_semantic_domain(path1)
        domain2 = self.identify_semantic_domain(path2)

        # If different domains, low similarity
        if not domain1 or not domain2 or domain1 != domain2:
            return 0.1

        # Same domain - calculate additional similarity factors
        similarity_score = 0.6  # Base score for same domain

        # Factor 1: Shared semantic keywords
        keywords1 = self._extract_semantic_keywords(path1, domain1)
        keywords2 = self._extract_semantic_keywords(path2, domain2)

        if keywords1 and keywords2:
            common_keywords = keywords1 & keywords2
            all_keywords = keywords1 | keywords2
            keyword_similarity = len(common_keywords) / len(all_keywords)
            similarity_score += keyword_similarity * 0.3

        # Factor 2: Structural context similarity
        context_similarity = self._calculate_context_similarity(path1, path2)
        similarity_score += context_similarity * 0.1

        return min(similarity_score, 1.0)

    def _extract_semantic_keywords(self, path: str, domain: str) -> Set[str]:
        """Extract semantic keywords from a path within a specific domain.

        Args:
            path: Configuration path.
            domain: Semantic domain.

        Returns:
            Set of semantic keywords found in the path.
        """
        if domain not in self.semantic_domains:
            return set()

        domain_keywords = self.semantic_domains[domain]
        path_lower = path.lower()

        found_keywords = set()
        for keyword in domain_keywords:
            if keyword in path_lower:
                found_keywords.add(keyword)

        return found_keywords

    def _calculate_context_similarity(self, path1: str, path2: str) -> float:
        """Calculate contextual similarity between paths.

        Args:
            path1: First path.
            path2: Second path.

        Returns:
            Context similarity score.
        """
        # Extract context indicators (parent path components)
        parts1 = path1.split(".")[:-1]  # Exclude final field name
        parts2 = path2.split(".")[:-1]

        if not parts1 or not parts2:
            return 0.0

        # Find common context elements
        common_context = set(parts1) & set(parts2)
        all_context = set(parts1) | set(parts2)

        return len(common_context) / len(all_context) if all_context else 0.0

    def get_domain_keywords(self, domain: str) -> List[str]:
        """Get keywords for a specific semantic domain.

        Args:
            domain: Domain name.

        Returns:
            List of keywords for the domain.
        """
        return self.semantic_domains.get(domain, [])

    def get_all_domains(self) -> List[str]:
        """Get all available semantic domains.

        Returns:
            List of all domain names.
        """
        return list(self.semantic_domains.keys())

    def analyze_value_semantics(self, value: str, path_context: str) -> Dict[str, any]:
        """Analyze semantic meaning of a configuration value.

        Args:
            value: Configuration value to analyze.
            path_context: Path context for additional semantic clues.

        Returns:
            Dictionary with semantic analysis results.
        """
        if not isinstance(value, str):
            return {"type": "non_string", "semantics": {}}

        semantics = {
            "is_identifier": self._is_identifier(value),
            "is_url": self._is_url(value),
            "is_hostname": self._is_hostname(value),
            "is_port": self._is_port_number(value),
            "is_version": self._is_version(value),
            "is_boolean_string": self._is_boolean_string(value),
            "contains_secrets": self._contains_secret_patterns(value),
            "is_resource_spec": self._is_resource_specification(value),
        }

        # Context-aware semantic analysis
        domain = self.identify_semantic_domain(path_context)
        if domain:
            semantics["domain_specific"] = self._analyze_domain_specific_semantics(
                value, domain
            )

        return {"type": "semantic_analysis", "semantics": semantics, "domain": domain}

    def _is_identifier(self, value: str) -> bool:
        """Check if value looks like an identifier."""
        return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", value))

    def _is_url(self, value: str) -> bool:
        """Check if value looks like a URL."""
        return bool(re.match(r"^https?://", value))

    def _is_hostname(self, value: str) -> bool:
        """Check if value looks like a hostname."""
        return (
            bool(re.match(r"^[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]$", value))
            and "." in value
        )

    def _is_port_number(self, value: str) -> bool:
        """Check if value looks like a port number."""
        try:
            port = int(value)
            return 1 <= port <= 65535
        except ValueError:
            return False

    def _is_version(self, value: str) -> bool:
        """Check if value looks like a version number."""
        return bool(re.match(r"^\\d+(\\.\\d+)*(-\\w+)?$", value))

    def _is_boolean_string(self, value: str) -> bool:
        """Check if value is a string representation of boolean."""
        return value.lower() in {
            "true",
            "false",
            "on",
            "off",
            "yes",
            "no",
            "enabled",
            "disabled",
        }

    def _contains_secret_patterns(self, value: str) -> bool:
        """Check if value contains patterns suggesting it's a secret."""
        secret_patterns = [
            r"password",
            r"secret",
            r"key",
            r"token",
            r"auth",
            r"[a-f0-9]{32,}",  # Long hex strings
            r"[A-Za-z0-9+/]{20,}={0,2}",  # Base64-like strings
        ]
        return any(
            re.search(pattern, value, re.IGNORECASE) for pattern in secret_patterns
        )

    def _is_resource_specification(self, value: str) -> bool:
        """Check if value is a resource specification (like '2Gi', '100Mi')."""
        return bool(re.match(r"^\\d+(\\.\\d+)?[KMGT]?i?[Bb]?$", value))

    def _analyze_domain_specific_semantics(
        self, value: str, domain: str
    ) -> Dict[str, bool]:
        """Analyze value semantics specific to a domain.

        Args:
            value: Value to analyze.
            domain: Semantic domain.

        Returns:
            Domain-specific semantic analysis.
        """
        domain_analysis = {}

        if domain == "service_account":
            domain_analysis.update(
                {
                    "has_serviceaccount_suffix": "serviceaccount" in value.lower(),
                    "has_site_prefix": bool(
                        re.search(r"^[a-z0-9-]+(?:serviceaccount|sa)$", value.lower())
                    ),
                    "follows_naming_convention": bool(
                        re.search(r"^[a-z0-9-]+-(?:serviceaccount|sa)$", value.lower())
                    ),
                }
            )

        elif domain == "network":
            domain_analysis.update(
                {
                    "is_service_name": "service" in value.lower(),
                    "is_cluster_ip": value.lower() == "clusterip",
                    "is_load_balancer": value.lower() == "loadbalancer",
                    "has_network_suffix": any(
                        suffix in value.lower() for suffix in ["svc", "service", "lb"]
                    ),
                }
            )

        elif domain == "database":
            domain_analysis.update(
                {
                    "is_mysql_related": "mysql" in value.lower(),
                    "is_ndb_related": "ndb" in value.lower(),
                    "is_replication_related": "repl" in value.lower(),
                    "has_db_suffix": value.lower().endswith(("db", "database")),
                }
            )

        return domain_analysis
