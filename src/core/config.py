import os
import sys
import itertools

# Configuration
class Config:
    def __init__(self):
        # Support for multiple API keys (comma-separated)
        openai_api_keys = os.environ.get("OPENAI_API_KEY", "")
        if not openai_api_keys:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # Split keys by comma and remove whitespace
        self.openai_api_keys = [key.strip() for key in openai_api_keys.split(",") if key.strip()]
        if not self.openai_api_keys:
            raise ValueError("No valid OPENAI_API_KEY found in environment variables")
        
        # Create a round-robin iterator for the API keys
        self.api_key_cycle = itertools.cycle(self.openai_api_keys)
        
        # Add Anthropic API key for client validation
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.anthropic_api_key:
            print("Warning: ANTHROPIC_API_KEY not set. Client API key validation will be disabled.")
        
        self.openai_base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.azure_api_version = os.environ.get("AZURE_API_VERSION")  # For Azure OpenAI
        self.host = os.environ.get("HOST", "0.0.0.0")
        self.port = int(os.environ.get("PORT", "8082"))
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")
        self.max_tokens_limit = int(os.environ.get("MAX_TOKENS_LIMIT", "4096"))
        self.min_tokens_limit = int(os.environ.get("MIN_TOKENS_LIMIT", "100"))
        
        # Connection settings
        self.request_timeout = int(os.environ.get("REQUEST_TIMEOUT", "90"))
        self.max_retries = int(os.environ.get("MAX_RETRIES", "2"))
        
        # Model settings - BIG and SMALL models
        self.big_model = os.environ.get("BIG_MODEL", "gpt-4o")
        self.middle_model = os.environ.get("MIDDLE_MODEL", self.big_model)
        self.small_model = os.environ.get("SMALL_MODEL", "gpt-4o-mini")
        
    def get_next_api_key(self):
        """Get the next API key in round-robin fashion"""
        return next(self.api_key_cycle)
        
    def validate_api_key(self, api_key=None):
        """Basic API key validation"""
        key_to_validate = api_key or self.openai_api_keys[0]
        if not key_to_validate:
            return False
        # Basic format check for OpenAI API keys
        if not key_to_validate.startswith('sk-'):
            return False
        return True
        
    def validate_client_api_key(self, client_api_key):
        """Validate client's Anthropic API key"""
        # If no ANTHROPIC_API_KEY is set in the environment, skip validation
        if not self.anthropic_api_key:
            return True
            
        # Check if the client's API key matches the expected value
        return client_api_key == self.anthropic_api_key

try:
    config = Config()
    print(f" Configuration loaded: API_KEY={'*' * 20}..., BASE_URL='{config.openai_base_url}'")
except Exception as e:
    print(f"=4 Configuration Error: {e}")
    sys.exit(1)
