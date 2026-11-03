import os, sys
os.environ["NEXORA_JWT_SECRET"] = "test-secret-for-ci-only-0123456789abcdef"
os.environ["NEXORA_ENV"] = "development"
os.environ["NEXORA_DATABASE_URL"] = "sqlite:///./test_nexora.db"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
