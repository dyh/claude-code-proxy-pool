from fastapi import APIRouter, HTTPException, Request, Header, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from datetime import datetime
import uuid
import json
from typing import Optional

from src.core.config import config
from src.core.logging import logger
from src.core.client import OpenAIClient
from src.models.claude import ClaudeMessagesRequest, ClaudeTokenCountRequest
from src.conversion.request_converter import convert_claude_to_openai
from src.conversion.response_converter import (
    convert_openai_to_claude_response,
    convert_openai_streaming_to_claude_with_cancellation,
)
from src.core.model_manager import model_manager

router = APIRouter()

# Create a client factory to generate clients with prioritized polling
def get_openai_client():
    """Get an OpenAI client with the next API key in round-robin fashion"""
    api_key = config.get_next_api_key()
    return OpenAIClient(
        api_key,
        config.openai_base_url,
        config.request_timeout,
    )

def get_openai_client_prioritized():
    """Get an OpenAI client with prioritized polling: models first, then API keys"""
    api_key, model = config.get_next_api_key_and_model()
    return OpenAIClient(
        api_key,
        config.openai_base_url,
        config.request_timeout,
    ), model

async def validate_api_key(x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    """Validate the client's API key from either x-api-key header or Authorization header."""
    client_api_key = None
    
    # Extract API key from headers
    if x_api_key:
        client_api_key = x_api_key
    elif authorization and authorization.startswith("Bearer "):
        client_api_key = authorization.replace("Bearer ", "")
    
    # Skip validation if ANTHROPIC_API_KEY is not set in the environment
    if not config.anthropic_api_key:
        return
        
    # Validate the client API key
    if not client_api_key or not config.validate_client_api_key(client_api_key):
        logger.warning(f"Invalid API key provided by client")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key. Please provide a valid Anthropic API key."
        )

@router.post("/v1/messages")
async def create_message(request: ClaudeMessagesRequest, http_request: Request, _: None = Depends(validate_api_key)):
    try:
        logger.debug(
            f"Processing Claude request: model={request.model}, stream={request.stream}"
        )

        # Generate unique request ID for cancellation tracking
        request_id = str(uuid.uuid4())

        # Get client and model using prioritized polling (models first, then API keys)
        client, selected_model = get_openai_client_prioritized()

        # Convert Claude request to OpenAI format with the selected model
        openai_request = convert_claude_to_openai(request, model_manager, selected_model)

        # Check if client disconnected before processing
        if await http_request.is_disconnected():
            raise HTTPException(status_code=499, detail="Client disconnected")

        if request.stream:
            # Streaming response - wrap in error handling
            try:
                # Client and model already obtained via prioritized polling
                openai_stream = client.create_chat_completion_stream(
                    openai_request, request_id
                )
                return StreamingResponse(
                    convert_openai_streaming_to_claude_with_cancellation(
                        openai_stream,
                        request,
                        logger,
                        http_request,
                        client,
                        request_id,
                    ),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "*",
                    },
                )
            except HTTPException as e:
                # Convert to proper error response for streaming
                logger.error(f"Streaming error: {e.detail}")
                import traceback

                logger.error(traceback.format_exc())
                # Use a temporary client to classify the error
                temp_client = OpenAIClient(
                    config.openai_api_keys[0],
                    config.openai_base_url,
                    config.request_timeout,
                )
                error_message = temp_client.classify_openai_error(e.detail)
                # For streaming errors, return a StreamingResponse with error event
                # instead of JSONResponse to avoid "response already started" error
                return StreamingResponse(
                    iter([f"event: error\ndata: {json.dumps({'type': 'error', 'error': {'type': 'api_error', 'message': error_message}}, ensure_ascii=False)}\n\n"]),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "*",
                    },
                )
        else:
            # Non-streaming response
            # Client and model already obtained via prioritized polling
            openai_response = await client.create_chat_completion(
                openai_request, request_id
            )
            claude_response = convert_openai_to_claude_response(
                openai_response, request
            )
            return claude_response
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        logger.error(f"Unexpected error processing request: {e}")
        logger.error(traceback.format_exc())
        # Use a temporary client to classify the error
        temp_client = OpenAIClient(
            config.openai_api_keys[0],
            config.openai_base_url,
            config.request_timeout,
        )
        error_message = temp_client.classify_openai_error(str(e))
        raise HTTPException(status_code=500, detail=error_message)


@router.post("/v1/messages/count_tokens")
async def count_tokens(request: ClaudeTokenCountRequest, _: None = Depends(validate_api_key)):
    try:
        # For token counting, we'll use a simple estimation
        # In a real implementation, you might want to use tiktoken or similar

        total_chars = 0

        # Count system message characters
        if request.system:
            if isinstance(request.system, str):
                total_chars += len(request.system)
            elif isinstance(request.system, list):
                for block in request.system:
                    if hasattr(block, "text"):
                        total_chars += len(block.text)

        # Count message characters
        for msg in request.messages:
            if msg.content is None:
                continue
            elif isinstance(msg.content, str):
                total_chars += len(msg.content)
            elif isinstance(msg.content, list):
                for block in msg.content:
                    if hasattr(block, "text") and block.text is not None:
                        total_chars += len(block.text)

        # Rough estimation: 4 characters per token
        # Ensure at least 1 token even for empty content
        if total_chars <= 0:
            estimated_tokens = 0
        else:
            estimated_tokens = max(1, total_chars // 4)

        return {"input_tokens": estimated_tokens}

    except Exception as e:
        logger.error(f"Error counting tokens: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/validate-keys")
async def validate_api_keys():
    """Validate all configured API keys"""
    try:
        # Only validate if using ModelScope
        if not config.is_modelscope_endpoint():
            return {
                "status": "skipped",
                "message": "API key validation is only available for ModelScope endpoints",
                "endpoint": config.openai_base_url,
                "timestamp": datetime.now().isoformat(),
            }
        
        # Import validation function
        from src.core.modelscope_validator import validate_modelscope_keys
        
        # Validate all keys
        validation_results = await validate_modelscope_keys(config.openai_api_keys, detailed=True)
        
        # Format response - now includes all keys for debugging
        response = {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_keys": validation_results["total_keys"],
                "valid_keys": validation_results["valid_keys"], 
                "invalid_keys": validation_results["invalid_keys"],
                "valid_rate": validation_results["valid_rate"],
                "api_keys_working": len(validation_results.get("all_keys", config.openai_api_keys)),
                "all_keys_configured": len(config.openai_api_keys),  # Original count from env
            },
            "valid_keys_list": [],
            "invalid_keys_list": [],
            "recommendations": []
        }
        
        # Process all validation results to show complete keys
        all_results = validation_results.get("results", [])
        
        for result in all_results:
            key_index = result["key_index"]
            original_key = config.openai_api_keys[key_index]
            
            if result["valid"]:
                response["valid_keys_list"].append({
                    "index": key_index,
                    "key_preview": original_key[:15] + "...",
                    "message": result["message"],
                    "reason": result["details"].get("reason", "success")
                })
            else:
                response["invalid_keys_list"].append({
                    "index": key_index,
                    "key_preview": original_key[:15] + "...",
                    "message": result["message"],
                    "reason": result["details"].get("reason", "unknown")
                })
        
        # Add recommendations
        if validation_results["invalid_keys"] > 0:
            response["recommendations"].extend([
                "Remove or replace invalid API keys from your configuration",
                "Check if keys have been revoked in ModelScope user center",
                "Verify keys have the necessary permissions for inference"
            ])
        
        if validation_results["total_keys"] == 0:
            response["recommendations"].append("No API keys configured. Add OPENAI_API_KEY environment variable")
        elif validation_results["valid_keys"] == 0:
            response["recommendations"].append("🚨 CRITICAL: No valid API keys found! Service may not work correctly.")
            response["status"] = "failed"
        
        return response
        
    except Exception as e:
        logger.error(f"API key validation failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Validation process failed: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "recommendations": [
                    "Check server logs for detailed error information",
                    "Ensure ModelScope library is properly installed (pip install modelscope)",
                    "Verify network connectivity to ModelScope services"
                ]
            }
        )


@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Claude-to-OpenAI API Proxy v1.0.0",
        "status": "running",
        "config": {
            "openai_base_url": config.openai_base_url,
            "max_tokens_limit": config.max_tokens_limit,
            "api_key_configured": len(config.openai_api_keys) > 0,
            "api_keys_count": len(config.openai_api_keys),
            "client_api_key_validation": bool(config.anthropic_api_key),
            "big_models": config.big_models,
            "modelscope_api_validation": config.is_modelscope_endpoint(),
            "api_validation_enabled": config.enable_api_validation,
        },
        "endpoints": {
            "messages": "/v1/messages",
            "count_tokens": "/v1/messages/count_tokens",
            "validate_keys": "/validate-keys",
        },
    }
