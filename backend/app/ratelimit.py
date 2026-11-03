from slowapi import Limiter
from slowapi.util import get_remote_address

# In-memory limiter for single-process deploys; set NEXORA_REDIS_URL and switch
# storage_uri to redis for multi-worker production deploys.
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
