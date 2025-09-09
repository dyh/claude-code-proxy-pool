import asyncio
import aiohttp
import json
from typing import List, Dict, Any
from datetime import datetime
import logging

# Use basic logging to avoid circular imports during module import
logger = logging.getLogger(__name__)


class ModelScopeValidator:
    """Validator for ModelScope API keys using ModelScope Inference API
    
    This validator directly tests API keys against the ModelScope inference API
    by making an authenticated request to /v1/models endpoint. This is the most
    reliable way to verify if an API key has inference permissions.
    
    The previous HubApi-based validation has been deprecated as it requires
    different token types than inference API keys.
    """
    
    def __init__(self):
        self.base_url = "https://www.modelscope.cn"
        self.api_base_url = "https://api-inference.modelscope.cn"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type=None, exc_val=None, exc_tb=None):
        if self.session:
            await self.session.close()
    
    async def validate_api_key(self, api_key: str) -> Dict[str, Any]:
        """
        Validate a ModelScope API key using direct inference API call
        
        Returns:
            Dict containing:
                - valid: bool - Whether the key is valid
                - message: str - Status message
                - details: Dict - Additional information about the key
        """
        if not api_key or not api_key.startswith('ms-'):
            return {
                "valid": False,
                "message": "Invalid API key format. ModelScope keys should start with 'ms-'",
                "details": {"format": "invalid", "reason": "wrong_prefix"}
            }
        
        # Use direct API validation as the primary method
        return await self._validate_api_key_direct(api_key)
    
    async def _validate_api_key_direct(self, api_key: str) -> Dict[str, Any]:
        """Direct HTTP validation using actual ModelScope inference API"""
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # 🔥 CRITICAL CHANGE: Test with REAL inference request, not just model list
            # The model list endpoint has no authentication check, but inference does
            test_data = {
                "model": "Qwen/Qwen2.5-7B-Instruct",  # Use a public model
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 5,  # Very small, just to test auth
                "temperature": 0.1
            }
            
            test_url = f"{self.api_base_url}/v1/chat/completions"
            
            async with self.session.post(test_url, headers=headers, json=test_data, timeout=10) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    # Key passed authentication and can actually perform inference
                    try:
                        result = json.loads(response_text)
                        has_choices = 'choices' in result and len(result['choices']) > 0
                        text_content = result.get('choices', [{}])[0].get('message', {}).get('content', '') if has_choices else ''
                        
                        if has_choices and text_content:
                            return {
                                "valid": True,
                                "message": "API key is valid and can perform inference",
                                "details": {
                                    "method": "real_inference_test",
                                    "status_code": response.status,
                                    "response_generated": True,
                                    "text_preview": text_content[:50] + "...",
                                    "model_scoped": result.get('model', 'unknown'),
                                    "tested_at": datetime.now().isoformat()
                                }
                            }
                        else:
                            # Responded but no content - unusual but technically valid
                            return {
                                "valid": True,
                                "message": "API key works but generated no content",
                                "details": {
                                    "method": "real_inference_test",
                                    "status_code": response.status,
                                    "response_generated": False,
                                    "reason": "empty_response"
                                }
                            }
                    except json.JSONDecodeError:
                        return {
                            "valid": True,
                            "message": "API key authenticated but invalid response format",
                            "details": {
                                "method": "real_inference_test",
                                "status_code": response.status,
                                "response_format": "invalid"
                            }
                        }
                        
                elif response.status == 401:
                    # This is the expected response for invalid/fake keys
                    error_detail = "Invalid or expired API key"
                    if response_text:
                        try:
                            error_data = json.loads(response_text)
                            if isinstance(error_data, dict) and 'error' in error_data:
                                error_detail = error_data['error']
                        except:
                            error_detail = response_text[:200]
                    
                    return {
                        "valid": False,
                        "message": "API key is invalid, expired, or revoked",
                        "details": {
                            "method": "real_inference_test",
                            "status_code": response.status,
                            "error": error_detail,
                            "reason": "unauthorized",
                            "expected": True  # 401 for fake keys is expected
                        }
                    }
                    
                else:
                    # Other status codes
                    error_detail = f"HTTP {response.status}"
                    if response_text:
                        error_detail += f": {response_text[:200]}"
                    
                    return {
                        "valid": False,
                        "message": f"API key validation failed with status {response.status}",
                        "details": {
                            "method": "real_inference_test",
                            "status_code": response.status,
                            "error": error_detail,
                            "reason": "http_error"
                        }
                    }
                    
        except asyncio.TimeoutError:
            # Timeout might indicate rate limiting or service issues
            return {
                "valid": False,
                "message": "API validation timeout - service may be overloaded",
                "details": {
                    "method": "real_inference_test",
                    "reason": "timeout",
                    "timeout_seconds": 10
                }
            }
        except aiohttp.ClientError as e:
            return {
                "valid": False,
                "message": f"Network error during validation: {str(e)}",
                "details": {
                    "method": "real_inference_test",
                    "reason": "network_error",
                    "error_type": type(e).__name__
                }
            }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Unexpected validation error: {str(e)}",
                "details": {
                    "method": "real_inference_test",
                    "error": str(e),
                    "reason": "unexpected_error",
                    "error_type": type(e).__name__
                }
            }
    
    async def validate_api_key_simple(self, api_key: str) -> bool:
        """Simple validation returning just true/false"""
        result = await self.validate_api_key(api_key)
        return result["valid"]
    
    async def validate_multiple_keys(self, api_keys: List[str]) -> Dict[str, Any]:
        """Validate multiple API keys and return summary"""
        if not api_keys:
            return {
                "total_keys": 0,
                "valid_keys": 0,
                "invalid_keys": 0,
                "results": []
            }
        
        tasks = [self.validate_api_key(key) for key in api_keys]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        valid_keys = []
        invalid_keys = []
        
        for i, (key, result) in enumerate(zip(api_keys, results)):
            if isinstance(result, Exception):
                # Handle exceptions in validation
                processed_result = {
                    "key_index": i,
                    "key_prefix": key[:10] + "..." if len(key) > 10 else key,
                    "valid": False,
                    "message": f"Validation exception: {str(result)}",
                    "details": {"exception": str(result)}
                }
                invalid_keys.append(key)
            else:
                processed_result = {
                    "key_index": i,
                    "key": key,  # Add the complete key for API endpoint use
                    "key_prefix": key[:10] + "..." if len(key) > 10 else key,
                    **result
                }
                if result["valid"]:
                    valid_keys.append(key)
                else:
                    invalid_keys.append(key)
            
            processed_results.append(processed_result)
        
        return {
            "total_keys": len(api_keys),
            "valid_keys": len(valid_keys),
            "invalid_keys": len(invalid_keys),
            "valid_rate": f"{len(valid_keys)/len(api_keys)*100:.1f}%",
            "valid_keys_list": valid_keys,
            "invalid_keys_list": invalid_keys,
            "results": processed_results
        }
    
    async def validate_api_key_with_test_inference(self, api_key: str, model: str = "Qwen/Qwen2.5-0.5B-Instruct") -> Dict[str, Any]:
        """
        Validate API key by attempting a test inference request
        This provides more thorough validation than just checking the key format
        """
        if not api_key or not api_key.startswith('ms-'):
            return {
                "valid": False,
                "message": "Invalid API key format",
                "details": {"format": "invalid"}
            }
        
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Simple test inference request
            test_data = {
                "model": model,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 5,
                "temperature": 0.1
            }
            
            test_url = f"{self.base_url}/v1/chat/completions"
            
            async with self.session.post(test_url, headers=headers, json=test_data, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "valid": True,
                        "message": "API key is valid and can perform inference",
                        "details": {
                            "status_code": response.status,
                            "test_model": model,
                            "response_id": data.get("id"),
                            "key_has_inference_access": True
                        }
                    }
                elif response.status == 401:
                    error_data = await response.json() if response.content_type == 'application/json' else await response.text()
                    return {
                        "valid": False,
                        "message": "API key is invalid or has no inference access",
                        "details": {
                            "status_code": response.status,
                            "error": error_data,
                            "reason": "inference_unauthorized"
                        }
                    }
                else:
                    error_data = await response.json() if response.content_type == 'application/json' else await response.text()
                    # Some other error, but key might still be valid
                    return {
                        "valid": True,  # Key is format-valid, but there might be other issues
                        "message": f"Test inference failed with status {response.status}, but key format is valid",
                        "details": {
                            "status_code": response.status,
                            "error": error_data,
                            "warning": "Key format valid but inference failed"
                        }
                    }
                    
        except asyncio.TimeoutError:
            return {
                "valid": False,
                "message": "Test inference timeout",
                "details": {"reason": "timeout"}
            }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Test inference error: {str(e)}",
                "details": {"reason": "inference_error", "error": str(e)}
            }
    
    def log_validation_results(self, results: Dict[str, Any], log_level: str = "INFO"):
        """Log validation results in a formatted way"""
        if log_level.upper() == "INFO":
            logger_func = logger.info
        elif log_level.upper() == "WARNING":
            logger_func = logger.warning
        elif log_level.upper() == "ERROR":
            logger_func = logger.error
        else:
            logger_func = logger.info
        
        logger_func("=" * 60)
        logger_func("ModelScope API Key Validation Results")
        logger_func("=" * 60)
        logger_func(f"Total Keys: {results['total_keys']}")
        logger_func(f"Valid Keys: {results['valid_keys']} ({results['valid_rate']})")
        logger_func(f"Invalid Keys: {results['invalid_keys']}")
        logger_func("")
        
        if results['invalid_keys'] > 0:
            logger_func("Invalid/Problematic Keys:")
            for result in results['results']:
                if not result['valid']:
                    logger_func(f"  ❌ {result['key_prefix']}: {result['message']}")
        
        if results['valid_keys'] > 0:
            logger_func("Valid Keys:")
            for result in results['results']:
                if result['valid']:
                    logger_func(f"  ✅ {result['key_prefix']}: {result['message']}")
        
        logger_func("=" * 60)


# Standalone validation function for easy use
async def validate_modelscope_keys(api_keys: List[str], detailed: bool = True) -> Dict[str, Any]:
    """
    Standalone function to validate ModelScope API keys
    
    Args:
        api_keys: List of API keys to validate
        detailed: Whether to perform detailed validation (including test inference)
    
    Returns:
        Validation results summary
    """
    async with ModelScopeValidator() as validator:
        basic_results = await validator.validate_multiple_keys(api_keys)
        
        if detailed and basic_results['valid_keys'] > 0:
            # Perform additional test inference for valid keys
            logger.info("Performing detailed validation with test inference...")
            for i, result in enumerate(basic_results['results']):
                if result['valid']:
                    detailed_result = await validator.validate_api_key_with_test_inference(
                        api_keys[result['key_index']]
                    )
                    basic_results['results'][i]['detailed_validation'] = detailed_result
        
        validator.log_validation_results(basic_results)
        return basic_results