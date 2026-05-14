"""
LLM Service - Centralized service for managing LangChain LLM instances
Provides a clean service layer for all LLM operations across the application
"""

import logging
import time
from typing import Optional, Dict, Any, List, AsyncIterator, Union
from enum import Enum
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from core.config import settings
from core.database import get_database

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers"""

    OPENAI = "openai"  # OpenAI GPT models (default)
    GEMINI = "gemini"  # Google Gemini models


class LLMProfile(Enum):
    """Predefined LLM profiles for different use cases"""

    DEFAULT = "default"  # Balanced, general purpose (temp=0.7)
    PRECISE = "precise"  # Low temperature for structured output (temp=0.3)
    CREATIVE = "creative"  # High temperature for creative content (temp=0.9)
    ANALYTICAL = "analytical"  # For analysis and reasoning (temp=0.5)


class LLMService:
    """
    Centralized service for LLM operations using LangChain
    Manages LLM client instances and provides unified interface
    """

    def __init__(self):
        """Initialize LLM service with configuration"""
        self._clients: Dict[str, Optional[Union[ChatOpenAI, ChatGoogleGenerativeAI]]] = {}
        self._supabase = None
        self._initialize_clients()
        self._initialize_supabase()

    def _initialize_supabase(self):
        """Initialize Supabase client for logging"""
        try:
            db = get_database()
            self._supabase = db.client
            logger.info("Supabase client initialized for LLM logging")
        except Exception as e:
            logger.warning(f"Failed to initialize Supabase for LLM logging: {e}")

    def _initialize_clients(self):
        """Initialize LangChain LLM clients for different profiles"""
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not configured - LLM service unavailable")
            return

        try:
            # Initialize OpenAI clients for each profile (default provider)
            profile_configs = {
                LLMProfile.DEFAULT: {
                    "temperature": 0.7,
                    "model": "gpt-4o-mini",
                    "provider": LLMProvider.OPENAI,
                },
                LLMProfile.PRECISE: {
                    "temperature": 0.3,
                    "model": "gpt-4o-mini",
                    "provider": LLMProvider.OPENAI,
                },
                LLMProfile.CREATIVE: {
                    "temperature": 0.9,
                    "model": "gpt-4o-mini",
                    "provider": LLMProvider.OPENAI,
                },
                LLMProfile.ANALYTICAL: {
                    "temperature": 0.5,
                    "model": "gpt-4o-mini",
                    "provider": LLMProvider.OPENAI,
                },
            }

            for profile, config in profile_configs.items():
                self._clients[profile.value] = ChatOpenAI(
                    api_key=settings.openai_api_key,
                    model=config["model"],
                    temperature=config["temperature"],
                    timeout=120.0,  # 2 minute timeout to prevent hanging
                )
                logger.info(f"Initialized OpenAI LLM client for profile: {profile.value}")

            logger.info("LLM service initialized successfully with OpenAI")

        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {e}")
            self._clients = {}

    def is_available(self, profile: LLMProfile = LLMProfile.DEFAULT) -> bool:
        """
        Check if LLM service is available for a specific profile

        Args:
            profile: The LLM profile to check

        Returns:
            True if the service is available, False otherwise
        """
        return profile.value in self._clients and self._clients[profile.value] is not None

    def get_client(
        self,
        profile: LLMProfile = LLMProfile.DEFAULT,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        provider: Optional[LLMProvider] = None,
        **kwargs,
    ) -> Optional[Union[ChatOpenAI, ChatGoogleGenerativeAI]]:
        """
        Get a LangChain LLM client, optionally with custom configuration

        Args:
            profile: The LLM profile to use
            model: Override model name
            temperature: Override temperature
            provider: Override provider (OpenAI or Gemini)
            **kwargs: Additional model parameters

        Returns:
            ChatOpenAI or ChatGoogleGenerativeAI client or None if unavailable
        """
        # Determine provider - default to OpenAI
        target_provider = provider or LLMProvider.GEMINI

        # Check if requesting Gemini
        if target_provider == LLMProvider.GEMINI:
            if not settings.google_api_key:
                logger.warning("Google API key not configured - Gemini unavailable")
                return None

            # Create Gemini client
            try:
                gemini_model = model or "gemini-2.0-flash"
                gemini_temp = temperature if temperature is not None else 0.7

                # Filter kwargs to only include parameters supported by ChatGoogleGenerativeAI
                # Gemini doesn't support: max_retries, request_timeout, and other OpenAI-specific params
                gemini_kwargs = {}

                # Map max_tokens to max_output_tokens for Gemini
                if 'max_tokens' in kwargs and kwargs['max_tokens']:
                    gemini_kwargs['max_output_tokens'] = kwargs['max_tokens']

                # Include other supported parameters
                supported_params = {'top_p', 'top_k', 'n', 'stop'}
                for k, v in kwargs.items():
                    if k in supported_params:
                        gemini_kwargs[k] = v

                return ChatGoogleGenerativeAI(
                    google_api_key=settings.google_api_key,
                    model=gemini_model,
                    temperature=gemini_temp,
                    timeout=120.0,  # 2 minute timeout to prevent hanging
                    **gemini_kwargs,
                )
            except Exception as e:
                logger.error(f"Failed to create Gemini client: {e}")
                return None

        # OpenAI provider (default)
        if not self.is_available(profile):
            logger.warning(f"LLM client not available for profile: {profile.value}")
            return None

        base_client = self._clients[profile.value]

        # If no overrides, return cached client
        if model is None and temperature is None and not kwargs:
            return base_client

        # Create customized OpenAI client with overrides
        try:
            custom_config = {
                "api_key": settings.openai_api_key,
                "model": model or base_client.model_name,
                "temperature": temperature if temperature is not None else base_client.temperature,
                "timeout": 120.0,  # 2 minute timeout to prevent hanging
            }
            custom_config.update(kwargs)

            return ChatOpenAI(**custom_config)

        except Exception as e:
            logger.error(f"Failed to create custom LLM client: {e}")
            return base_client

    def _convert_messages(self, messages: List[Dict[str, str]], image_url: Optional[str] = None) -> List[BaseMessage]:
        """
        Convert message dicts to LangChain message objects
        Supports multimodal messages with images for vision models

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            image_url: Optional image URL for vision-enabled models

        Returns:
            List of LangChain message objects
        """
        lc_messages = []
        for i, msg in enumerate(messages):
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # For vision models, add image to the last user message
            if image_url and i == len(messages) - 1 and (role == "user" or role == "human"):
                # Create multimodal content with text and image
                multimodal_content = [
                    {"type": "text", "text": content},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
                lc_messages.append(HumanMessage(content=multimodal_content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant" or role == "ai":
                lc_messages.append(AIMessage(content=content))
            else:  # user or human
                lc_messages.append(HumanMessage(content=content))

        return lc_messages

    async def _log_to_supabase(
        self,
        profile: LLMProfile,
        model: str,
        operation: str,
        messages: List[Dict[str, str]],
        response_content: Optional[str],
        status: str,
        execution_time_ms: int,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        error_message: Optional[str] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        service_name: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs,
    ):
        """
        Log LLM request and response to Supabase

        Args:
            profile: LLM profile used
            model: Model name
            operation: Operation type (generate, stream, batch_generate)
            messages: Request messages
            response_content: Generated response
            status: Request status (success, error, partial)
            execution_time_ms: Execution time in milliseconds
            temperature: Temperature setting
            max_tokens: Max tokens setting
            error_message: Error message if failed
            tenant_id: Tenant ID for RLS
            user_id: User ID who made the request
            service_name: Name of the service making the call
            request_id: Optional request tracking ID
            **kwargs: Additional parameters
        """
        if not self._supabase:
            return

        try:
            log_entry = {
                "profile": profile.value,
                "model": model,
                "operation": operation,
                "messages": messages,
                "response_content": response_content,
                "status": status,
                "execution_time_ms": execution_time_ms,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "error_message": error_message,
                "tenant_id": tenant_id,
                "created_by": user_id,
                "service_name": service_name,
                "request_id": request_id,
                "additional_params": {k: v for k, v in kwargs.items() if v is not None},
                "created_at": datetime.utcnow().isoformat(),
            }

            # Estimate token counts (rough approximation)
            # More accurate counts would come from OpenAI response metadata
            if messages:
                prompt_text = " ".join([m.get("content", "") for m in messages])
                prompt_tokens = len(prompt_text.split()) * 1.3  # Rough estimate
                log_entry["prompt_tokens"] = int(prompt_tokens)

            if response_content:
                completion_tokens = len(response_content.split()) * 1.3
                log_entry["completion_tokens"] = int(completion_tokens)
                log_entry["total_tokens"] = int(prompt_tokens + completion_tokens)

            # Insert into Supabase
            result = self._supabase.table("llm_logs").insert(log_entry).execute()

            if result.data:
                logger.debug(f"Logged LLM request to Supabase: {result.data[0]['id']}")

        except Exception as e:
            # Don't let logging errors break the main flow
            logger.error(f"Failed to log LLM request to Supabase: {e}")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        profile: LLMProfile = LLMProfile.DEFAULT,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
        provider: Optional[LLMProvider] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        service_name: Optional[str] = None,
        request_id: Optional[str] = None,
        image_url: Optional[str] = None,  # For vision-enabled models
        **kwargs,
    ) -> Optional[str]:
        """
        Generate a completion using LangChain LLM

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            profile: LLM profile to use
            max_tokens: Maximum tokens to generate
            temperature: Override temperature for this request
            model: Override model for this request
            provider: Override provider (OpenAI or Gemini)
            tenant_id: Tenant ID for logging and RLS
            user_id: User ID for logging
            service_name: Name of the calling service (for tracking)
            request_id: Optional request tracking ID
            image_url: Optional image URL for vision-enabled models
            **kwargs: Additional parameters to pass to the model

        Returns:
            Generated text content or None if failed
        """
        start_time = time.time()
        response_content = None
        status = "error"
        error_message = None

        # For Gemini, skip profile availability check
        if provider != LLMProvider.GEMINI and not self.is_available(profile):
            logger.warning(f"LLM service not available for profile: {profile.value}")
            return None

        try:
            # Use vision-enabled model if image_url is provided
            if image_url:
                # Force use of vision-enabled provider and model when image is present
                if not provider:
                    # Default to Gemini for vision (since it's the default provider)
                    provider = LLMProvider.GEMINI
                    model = model or "gemini-2.0-flash"
                elif provider == LLMProvider.GEMINI:
                    model = model or "gemini-2.0-flash"
                else:
                    # OpenAI
                    model = model or "gpt-4o"
                logger.info(f"Using vision-enabled model {model} with provider {provider.value} and image: {image_url[:50]}...")

            # Get client with optional overrides
            client = self.get_client(
                profile=profile,
                model=model,
                temperature=temperature,
                provider=provider,
                max_tokens=max_tokens,
                **kwargs,
            )

            if not client:
                error_message = "Failed to get LLM client"
                return None

            # Convert messages (with image if provided)
            lc_messages = self._convert_messages(messages, image_url=image_url)

            # Generate response
            response = await client.ainvoke(lc_messages)
            response_content = response.content
            status = "success"
            return response_content

        except Exception as e:
            error_message = str(e)
            logger.error(f"Failed to generate completion: {e}")
            return None

        finally:
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Determine model name for logging
            if provider == LLMProvider.GEMINI:
                log_model = model or "gemini-2.0-flash"
            else:
                log_model = model or (
                    self._clients[profile.value].model_name
                    if self.is_available(profile)
                    else "unknown"
                )

            # Log to Supabase (async, non-blocking)
            try:
                await self._log_to_supabase(
                    profile=profile,
                    model=log_model,
                    operation="generate",
                    messages=messages,
                    response_content=response_content,
                    status=status,
                    execution_time_ms=execution_time_ms,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    error_message=error_message,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    service_name=service_name,
                    request_id=request_id,
                    provider=provider.value if provider else LLMProvider.OPENAI.value,
                    **kwargs,
                )
            except Exception as log_error:
                logger.error(f"Failed to log LLM request: {log_error}")

    async def stream(
        self,
        messages: List[Dict[str, str]],
        profile: LLMProfile = LLMProfile.DEFAULT,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
        provider: Optional[LLMProvider] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        service_name: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Stream a completion using LangChain LLM

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            profile: LLM profile to use
            max_tokens: Maximum tokens to generate
            temperature: Override temperature for this request
            model: Override model for this request
            provider: Override provider (OpenAI or Gemini)
            tenant_id: Tenant ID for logging and RLS
            user_id: User ID for logging
            service_name: Name of the calling service (for tracking)
            request_id: Optional request tracking ID
            **kwargs: Additional parameters to pass to the model

        Yields:
            Generated text chunks
        """
        start_time = time.time()
        response_content = ""
        status = "error"
        error_message = None

        # For Gemini, skip profile availability check
        if provider != LLMProvider.GEMINI and not self.is_available(profile):
            logger.warning(f"LLM service not available for profile: {profile.value}")
            return

        try:
            # Get client with optional overrides
            client = self.get_client(
                profile=profile,
                model=model,
                temperature=temperature,
                provider=provider,
                max_tokens=max_tokens,
                **kwargs,
            )

            if not client:
                error_message = "Failed to get LLM client"
                return

            # Convert messages
            lc_messages = self._convert_messages(messages)

            # Stream response and collect content
            async for chunk in client.astream(lc_messages):
                if chunk.content:
                    response_content += chunk.content
                    yield chunk.content

            status = "success"

        except Exception as e:
            error_message = str(e)
            logger.error(f"Failed to stream completion: {e}")
            status = "partial" if response_content else "error"

        finally:
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Determine model name for logging
            if provider == LLMProvider.GEMINI:
                log_model = model or "gemini-2.0-flash"
            else:
                log_model = model or (
                    self._clients[profile.value].model_name
                    if self.is_available(profile)
                    else "unknown"
                )

            # Log to Supabase (async, non-blocking)
            try:
                await self._log_to_supabase(
                    profile=profile,
                    model=log_model,
                    operation="stream",
                    messages=messages,
                    response_content=response_content or None,
                    status=status,
                    execution_time_ms=execution_time_ms,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    error_message=error_message,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    service_name=service_name,
                    request_id=request_id,
                    provider=provider.value if provider else LLMProvider.OPENAI.value,
                    **kwargs,
                )
            except Exception as log_error:
                logger.error(f"Failed to log LLM stream request: {log_error}")

    async def batch_generate(
        self,
        message_batches: List[List[Dict[str, str]]],
        profile: LLMProfile = LLMProfile.DEFAULT,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        service_name: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs,
    ) -> List[Optional[str]]:
        """
        Generate completions for multiple message sets in batch

        Args:
            message_batches: List of message lists to process
            profile: LLM profile to use
            max_tokens: Maximum tokens to generate per request
            temperature: Override temperature
            tenant_id: Tenant ID for logging and RLS
            user_id: User ID for logging
            service_name: Name of the calling service (for tracking)
            request_id: Optional request tracking ID
            **kwargs: Additional parameters

        Returns:
            List of generated responses (None for failed requests)
        """
        start_time = time.time()
        responses = [None] * len(message_batches)
        status = "error"
        error_message = None

        if not self.is_available(profile):
            logger.warning(f"LLM service not available for profile: {profile.value}")
            return responses

        try:
            client = self.get_client(
                profile=profile, temperature=temperature, max_tokens=max_tokens, **kwargs
            )

            if not client:
                error_message = "Failed to get LLM client"
                return responses

            # Convert all message batches
            lc_message_batches = [self._convert_messages(msgs) for msgs in message_batches]

            # Batch invoke
            batch_responses = await client.abatch(lc_message_batches)
            responses = [resp.content if resp else None for resp in batch_responses]
            status = "success"

        except Exception as e:
            error_message = str(e)
            logger.error(f"Failed to batch generate completions: {e}")

        finally:
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Log batch operation (summarized)
            try:
                # Create a summary of the batch operation
                batch_summary = {
                    "batch_size": len(message_batches),
                    "successful_responses": sum(1 for r in responses if r is not None),
                    "failed_responses": sum(1 for r in responses if r is None),
                }

                await self._log_to_supabase(
                    profile=profile,
                    model=client.model_name if client else "unknown",
                    operation="batch_generate",
                    messages=[
                        {
                            "role": "system",
                            "content": f"Batch operation with {len(message_batches)} requests",
                        }
                    ],
                    response_content=f"Batch completed: {batch_summary}",
                    status=status,
                    execution_time_ms=execution_time_ms,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    error_message=error_message,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    service_name=service_name,
                    request_id=request_id,
                    batch_summary=batch_summary,
                    **kwargs,
                )
            except Exception as log_error:
                logger.error(f"Failed to log LLM batch request: {log_error}")

        return responses


# Singleton instance
llm_service = LLMService()
