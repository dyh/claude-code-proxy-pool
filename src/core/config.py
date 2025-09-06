import os
import sys
import itertools
import asyncio
import json
from typing import List, Optional
from src.core.modelscope_validator import validate_modelscope_keys

# Configuration
class Config:
    def __init__(self):
        # Import from root config.py only
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            import config as root_config
            
            def get_config(key, default=None):
                """Helper to get config from root config.py only"""
                if hasattr(root_config, key):
                    return getattr(root_config, key)
                elif default is not None:
                    return default
                else:
                    raise ValueError(f"{key} not found in config.py")
                
        except ImportError:
            raise ValueError("config.py not found in project root directory")
        
        print(f"📁 Loading configuration from root config.py")
        
        # Support for multiple API keys (Python list from config.py)
        openai_api_keys = get_config("OPENAI_API_KEY")
        
        # Validate and store API keys
        if isinstance(openai_api_keys, list) and openai_api_keys:
            self.openai_api_keys = openai_api_keys
        else:
            raise ValueError(f"OPENAI_API_KEY must be a non-empty list in config.py")
        
        # Create a round-robin iterator for the API keys
        self.api_key_cycle = itertools.cycle(self.openai_api_keys)
        
        # Add Anthropic API key for client validation
        self.anthropic_api_key = get_config("ANTHROPIC_API_KEY")
        if not self.anthropic_api_key:
            print("Warning: ANTHROPIC_API_KEY not set. Client API key validation will be disabled.")
        
        self.openai_base_url = get_config("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.host = get_config("HOST", "0.0.0.0")
        self.port = int(get_config("PORT", "8082"))
        self.log_level = get_config("LOG_LEVEL", "INFO")
        self.max_tokens_limit = int(get_config("MAX_TOKENS_LIMIT", "4096"))
        self.min_tokens_limit = int(get_config("MIN_TOKENS_LIMIT", "100"))
        
        # Connection settings
        self.request_timeout = int(get_config("REQUEST_TIMEOUT", "90"))
        self.max_retries = int(get_config("MAX_RETRIES", "2"))
        
        # Model settings - multi-model support with round-robin for BIG_MODEL
        big_models_raw = get_config("BIG_MODEL", "gpt-4o")  # Will use default if not found in config.py
        
        # Validate and store models
        if isinstance(big_models_raw, list):
            self.big_models = big_models_raw
        elif isinstance(big_models_raw, str):
            # If it comes as a string, split by comma (single model)
            self.big_models = [model.strip() for model in big_models_raw.split(",") if model.strip()]
        else:
            raise ValueError(f"BIG_MODEL must be a list or string in config.py")
        
        if not self.big_models:
            self.big_models = ["gpt-4o"]  # Default fallback
        
        self.big_model_cycle = itertools.cycle(self.big_models)
        
        # All other models use the big model cycle (no differentiation)
        self.middle_model = self.big_models[0]  # Default to first for backward compatibility
        self.small_model = self.big_models[0]  # Default to first for backward compatibility
        
        # Initialize indices for prioritized polling (API keys first, then models)
        self.current_key_index = 0
        self.current_model_index = 0
        
        # Validate API keys if ModelScope is being used
        enable_validation_str = get_config("ENABLE_API_VALIDATION", "false")  # Default to false
        self.enable_api_validation = str(enable_validation_str).lower() == "true"
        keep_invalid_str = get_config("KEEP_INVALID_KEYS", "true")
        self.keep_invalid_keys = str(keep_invalid_str).lower() == "true"
        
        if self.enable_api_validation and self.is_modelscope_endpoint():
            print("🔍 Validating ModelScope API keys...")
            self.validation_results = self.validate_modelscope_keys_sync()
            
            # Store validation results for debugging and monitoring
            self.all_api_keys = self.validation_results.get("all_keys", self.openai_api_keys)
            self.valid_api_keys = self.validation_results.get("valid_keys", [])
            self.invalid_api_keys = self.validation_results.get("invalid_keys", [])
            
            # 重要：无论是否有效，都保留所有密钥用于轮询
            # 但有调用次数限制的密钥可能白天无效，晚上恢复
            self.openai_api_keys = self.all_api_keys
            
            if self.keep_invalid_keys:
                print(f"✅ Validated {len(self.all_api_keys)} keys: {len(self.valid_api_keys)} valid, {len(self.invalid_api_keys)} invalid") 
                print("   ✆ All keys retained - invalid keys will be shown in validation results")
            else:
                print(f"✅ Found {len(self.valid_api_keys)} valid API keys out of {len(self.all_api_keys)} total")
                
            if not self.valid_api_keys:
                print("🚨 Warning: No valid ModelScope API keys found. Service may experience issues.")
            
                # 用于API调用的轮询 - 所有密钥都参与轮询，无效的会在调用时失败
            self.api_key_cycle = itertools.cycle(self.openai_api_keys)
            
            # 可选：用于统计和展示
            self.validation_summary = {
                "total": len(self.all_api_keys),
                "valid": len(self.valid_api_keys),
                "invalid": len(self.invalid_api_keys),
                "rate": f"{len(self.valid_api_keys)/len(self.all_api_keys)*100:.1f}%"
            }
        
    def get_next_api_key(self):
        """Get the next API key in round-robin fashion"""
        return next(self.api_key_cycle)
        
    def get_next_big_model(self):
        """Get the next big model in round-robin fashion"""
        return next(self.big_model_cycle)
    
    def get_next_api_key_and_model(self):
        """
        Get the next API key and model combination using prioritized polling:
        First cycle through all API keys for current model, then move to next model
        """
        # Get current API key
        api_key = self.openai_api_keys[self.current_key_index]
        
        # Get current model
        model = self.big_models[self.current_model_index]
        
        # Move to next API key
        self.current_key_index += 1
        
        # If we've cycled through all API keys, move to next model and reset key index
        if self.current_key_index >= len(self.openai_api_keys):
            self.current_key_index = 0
            self.current_model_index = (self.current_model_index + 1) % len(self.big_models)
        
        return api_key, model
        
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
    
    def is_modelscope_endpoint(self) -> bool:
        """Check if the configured endpoint is ModelScope"""
        return "modelscope.cn" in self.openai_base_url.lower()
    
    def validate_modelscope_keys_sync(self) -> dict:
        """Synchronously validate ModelScope API keys and return detailed results"""
        loop = None
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run validation
            validation_results = loop.run_until_complete(
                validate_modelscope_keys(self.openai_api_keys, detailed=False)
            )
            
            # 返回详细的验证结果，包含所有密钥的信息
            result = {
                "all_keys": self.openai_api_keys,
                "valid_keys": validation_results.get("valid_keys_list", []),
                "invalid_keys": validation_results.get("invalid_keys_list", []),
                "summary": {
                    "total": validation_results['total_keys'],
                    "valid": validation_results['valid_keys'],
                    "invalid": validation_results['invalid_keys'],
                    "rate": validation_results.get('valid_rate', '0%')
                },
                "results": validation_results.get("results", [])
            }
            
            # Log detailed results
            if result["summary"]["total"] > 0:
                if self.keep_invalid_keys:
                    print(f"✅ API Key Validation Results:")
                    print(f"   Total keys: {result['summary']['total']}")
                    print(f"   Valid keys: {result['summary']['valid']}")
                    print(f"   Invalid keys: {result['summary']['invalid']}")
                    
                    if result["summary"]["invalid"] > 0:
                        print("   ❌ Problematic keys:")
                        for result_detail in result.get('results', []):
                            if not result_detail['valid']:
                                print(f"      {result_detail['key_prefix']}: {result_detail['message']}")
                else:
                    print(f"✅ Found {result['summary']['valid']} valid API keys out of {result['summary']['total']} total")
            
            return result
            
        except Exception as e:
            print(f"⚠️  API key validation failed: {str(e)}")
            # 出错时回退到保持所有原始密钥
            fallback_result = {
                "all_keys": self.openai_api_keys,
                "valid_keys": self.openai_api_keys,
                "invalid_keys": [],
                "summary": {
                    "total": len(self.openai_api_keys),
                    "valid": len(self.openai_api_keys),
                    "invalid": 0,
                    "rate": "100.0%"
                },
                "results": []
            }
            return fallback_result
        finally:
            if loop is not None:
                try:
                    # Properly close all pending tasks before closing the loop
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except:
                    pass
                loop.close()
    
    async def validate_modelscope_keys_async(self) -> dict:
        """Asynchronously validate ModelScope API keys and return detailed results"""
        try:
            validation_results = await validate_modelscope_keys(self.openai_api_keys, detailed=False)
            
            # 返回详细的验证结果
            result = {
                "all_keys": self.openai_api_keys,
                "valid_keys": validation_results.get("valid_keys_list", []),
                "invalid_keys": validation_results.get("invalid_keys_list", []),
                "summary": {
                    "total": validation_results['total_keys'],
                    "valid": validation_results['valid_keys'],
                    "invalid": validation_results['invalid_keys'],
                    "rate": validation_results.get('valid_rate', '0%')
                },
                "results": validation_results.get("results", [])
            }
            return result
        except Exception as e:
            print(f"⚠️  API key validation failed: {str(e)}")
            # 出错时回退到保持所有密钥
            return {
                "all_keys": self.openai_api_keys,
                "valid_keys": self.openai_api_keys,
                "invalid_keys": [],
                "summary": {
                    "total": len(self.openai_api_keys),
                    "valid": len(self.openai_api_keys),
                    "invalid": 0,
                    "rate": "100.0%"
                },
                "results": []
            }

try:
    config = Config()
    print(f"Configuration loaded: API_KEY={'*' * 20}..., BASE_URL='{config.openai_base_url}'")
except Exception as e:
    print(f"=4 Configuration Error: {e}")
    sys.exit(1)
