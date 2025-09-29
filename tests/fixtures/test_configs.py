"""Test configuration fixtures for use across test modules."""

from typing import Any, Dict

# Simple test configurations
SIMPLE_OLD_TEMPLATE: Dict[str, Any] = {
    "service": {
        "name": "default-service",
        "port": 8080,
        "timeout": 30
    },
    "database": {
        "host": "localhost",
        "port": 5432
    }
}

SIMPLE_NEW_TEMPLATE: Dict[str, Any] = {
    "service": {
        "name": "default-service",
        "port": 9000,
        "timeout": 45,
        "new_setting": "default"
    },
    "database": {
        "host": "localhost",
        "port": 5432,
        "ssl": True
    }
}

SIMPLE_GOLDEN_CONFIG: Dict[str, Any] = {
    "service": {
        "name": "my-custom-service",
        "port": 8080,
        "timeout": 120
    },
    "database": {
        "host": "custom-db-host",
        "port": 5432
    }
}

# Complex nested configurations
COMPLEX_OLD_TEMPLATE: Dict[str, Any] = {
    "application": {
        "name": "myapp",
        "version": "1.0.0",
        "server": {
            "host": "0.0.0.0",
            "port": 8080,
            "ssl": {
                "enabled": False,
                "cert_path": "/etc/ssl/cert.pem",
                "key_path": "/etc/ssl/key.pem"
            }
        },
        "database": {
            "primary": {
                "host": "localhost",
                "port": 5432,
                "name": "app_db",
                "ssl_mode": "disable"
            },
            "replica": {
                "host": "localhost",
                "port": 5433,
                "name": "app_db",
                "ssl_mode": "disable"
            }
        },
        "logging": {
            "level": "info",
            "format": "json",
            "outputs": ["stdout", "file"]
        }
    },
    "features": {
        "auth": {
            "enabled": True,
            "provider": "local",
            "session_timeout": 3600
        },
        "caching": {
            "enabled": True,
            "type": "redis",
            "ttl": 300
        }
    }
}

COMPLEX_NEW_TEMPLATE: Dict[str, Any] = {
    "application": {
        "name": "myapp",
        "version": "2.0.0",
        "server": {
            "host": "0.0.0.0",
            "port": 8080,
            "ssl": {
                "enabled": False,
                "cert_path": "/etc/ssl/cert.pem",
                "key_path": "/etc/ssl/key.pem",
                "protocols": ["TLSv1.2", "TLSv1.3"]  # New field
            },
            "cors": {  # New section
                "enabled": False,
                "origins": ["*"]
            }
        },
        "database": {
            "primary": {
                "host": "localhost",
                "port": 5432,
                "name": "app_db",
                "ssl_mode": "require",  # Changed default
                "connection_pool": {    # New nested section
                    "min_size": 5,
                    "max_size": 20
                }
            },
            # replica section removed
        },
        "logging": {
            "level": "info",
            "format": "structured",  # Changed from "json"
            "outputs": ["stdout", "file"],
            "structured_format": {   # New nested section
                "timestamp_format": "iso8601",
                "include_caller": True
            }
        },
        "observability": {  # New top-level section
            "metrics": {
                "enabled": True,
                "port": 9090
            },
            "tracing": {
                "enabled": False,
                "endpoint": "http://jaeger:14268"
            }
        }
    },
    "features": {
        "auth": {
            "enabled": True,
            "providers": [  # Changed from single "provider" to list "providers"
                {
                    "name": "local",
                    "config": {}
                }
            ],
            "session_timeout": 7200  # Changed default
        },
        "caching": {
            "enabled": True,
            "type": "redis",
            "ttl": 600,  # Changed default
            "redis": {   # New nested config
                "host": "localhost",
                "port": 6379
            }
        },
        "rate_limiting": {  # New feature
            "enabled": False,
            "requests_per_minute": 1000
        }
    }
}

COMPLEX_GOLDEN_CONFIG: Dict[str, Any] = {
    "application": {
        "name": "production-app",  # Custom
        "version": "1.0.0",
        "server": {
            "host": "0.0.0.0",
            "port": 443,  # Custom
            "ssl": {
                "enabled": True,  # Custom
                "cert_path": "/prod/ssl/cert.pem",  # Custom
                "key_path": "/prod/ssl/key.pem"     # Custom
            }
        },
        "database": {
            "primary": {
                "host": "prod-db-primary.internal",  # Custom
                "port": 5432,
                "name": "production_db",  # Custom
                "ssl_mode": "require"     # Custom
            },
            "replica": {
                "host": "prod-db-replica.internal",  # Custom
                "port": 5432,
                "name": "production_db",  # Custom
                "ssl_mode": "require"     # Custom
            }
        },
        "logging": {
            "level": "warn",  # Custom
            "format": "json",
            "outputs": ["stdout", "file", "syslog"]  # Custom
        }
    },
    "features": {
        "auth": {
            "enabled": True,
            "provider": "oauth2",     # Custom
            "session_timeout": 1800  # Custom
        },
        "caching": {
            "enabled": True,
            "type": "redis",
            "ttl": 1800  # Custom
        }
    }
}

# Migration map examples
SIMPLE_MIGRATION_MAP: Dict[str, str] = {
    "old.setting": "new.setting",
    "deprecated.config": "new.config.setting"
}

COMPLEX_MIGRATION_MAP: Dict[str, str] = {
    "features.auth.provider": "features.auth.providers.0.name",
    "application.database.replica": "application.database.secondary"
}

# Expected results for testing
EXPECTED_SIMPLE_MERGE_RESULT: Dict[str, Any] = {
    "service": {
        "name": "my-custom-service",  # Custom preserved
        "port": 8080,                # Custom preserved
        "timeout": 120,              # Custom preserved
        "new_setting": "default"     # New default added
    },
    "database": {
        "host": "custom-db-host",    # Custom preserved
        "port": 5432,
        "ssl": True                  # New default added
    }
}