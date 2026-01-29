"""
Perplexity-style memory extraction using LLM.
Analyzes conversations and extracts categorized memories.
"""

import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from agent.config import Config
from agent.memory.categories import MemoryCategory
from agent.providers import PROVIDERS
import logging

logger = logging.getLogger(__name__)


class MemoryExtractor:
    """
    Extracts memories from conversations using LLM analysis.

    Features:
    - Auto-detects PII and flags privacy-sensitive memories
    - Categorizes memories using Perplexity-style taxonomy
    - Confidence scoring for memory quality
    - Cost-controlled extraction (min conversation length)
    """

    # PII detection patterns
    PRIVACY_PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'[\(\+]?\d{3}[\)\-\.\s]*\d{3}[\-\.\s]*\d{4}',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
    }

    def __init__(self, model_name: str = None):
        """
        Initialize memory extractor.

        Args:
            model_name: Model to use for extraction (defaults to config)
        """
        self.model_name = model_name or Config.MEMORY_EXTRACTION_MODEL
        self.provider_name, self.model = self._parse_model_name(self.model_name)

        # Get provider client
        if self.provider_name not in PROVIDERS:
            raise ValueError(f"Unsupported provider for memory extraction: {self.provider_name}")

        provider_class = PROVIDERS[self.provider_name]
        self.client = provider_class(api_key=self._get_api_key()).get_client()

    def _parse_model_name(self, model_name: str) -> tuple:
        """Parse provider:model format."""
        if ":" in model_name:
            provider, model = model_name.split(":", 1)
            return provider, model
        else:
            # Default to openrouter if no provider specified
            return "openrouter", model_name

    def _get_api_key(self) -> str:
        """Get API key for the configured provider."""
        if self.provider_name == "openrouter":
            return Config.OPENROUTER_API_KEY
        elif self.provider_name == "huggingface":
            return Config.HUGGINGFACE_API_KEY
        elif self.provider_name == "together":
            return Config.TOGETHER_API_KEY
        elif self.provider_name == "gemini":
            return Config.GEMINI_API_KEY
        elif self.provider_name == "grok":
            return Config.GROK_API_KEY
        else:
            raise ValueError(f"No API key configured for {self.provider_name}")

    def _detect_pii(self, content: str) -> Dict[str, Any]:
        """
        Auto-detect PII in content.

        Args:
            content: Text content to analyze

        Returns:
            Dict with has_pii flag and detected types
        """
        detected_types = []
        for pii_type, pattern in self.PRIVACY_PATTERNS.items():
            if re.search(pattern, content, re.IGNORECASE):
                detected_types.append(pii_type)

        return {
            "has_pii": len(detected_types) > 0,
            "types": detected_types
        }

    def _contains_pii(self, content: str) -> bool:
        """
        Check if content contains personally identifiable information.

        Args:
            content: Text content to check

        Returns:
            True if PII detected, False otherwise
        """
        pii_info = self._detect_pii(content)
        return pii_info["has_pii"]

    def extract_from_session(self,
                           conversation_history: List[Dict[str, str]],
                           session_id: str,
                           timestamp: datetime = None) -> List[Dict[str, Any]]:
        """
        Analyze conversation and extract categorized memories.

        Args:
            conversation_history: List of {"role": str, "content": str} messages
            session_id: Unique session identifier
            timestamp: Session timestamp (defaults to now)

        Returns:
            List of memory dictionaries with category, content, confidence, metadata
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Check if extraction should run (cost control)
        user_messages = [m for m in conversation_history if m.get("role") == "user"]
        if len(user_messages) < Config.MEMORY_MIN_TURNS_FOR_EXTRACTION:
            logger.info(f"Skipping extraction: only {len(user_messages)} user messages (min: {Config.MEMORY_MIN_TURNS_FOR_EXTRACTION})")
            return []

        # Format conversation for LLM
        formatted_conversation = self._format_conversation(conversation_history)

        # Create extraction prompt
        prompt = self._build_extraction_prompt(formatted_conversation)

        try:
            # Call LLM for extraction
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Low temperature for factual extraction
                max_tokens=2000
            )

            result_text = response.choices[0].message.content.strip()

            # Parse JSON response
            extracted_memories = self._parse_extraction_response(result_text, session_id, timestamp)

            logger.info(f"Extracted {len(extracted_memories)} memories from session {session_id}")
            return extracted_memories

        except Exception as e:
            logger.error(f"Memory extraction failed for session {session_id}: {e}")
            return []

    def _format_conversation(self, conversation_history: List[Dict[str, str]]) -> str:
        """
        Format conversation history for LLM input.

        Args:
            conversation_history: Raw conversation messages

        Returns:
            Formatted conversation string
        """
        formatted = []
        for msg in conversation_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "").strip()
            if content:
                formatted.append(f"{role.upper()}: {content}")

        return "\n\n".join(formatted)

    def _build_extraction_prompt(self, formatted_conversation: str) -> str:
        """
        Build the extraction prompt for the LLM.

        Args:
            formatted_conversation: Formatted conversation text

        Returns:
            Complete extraction prompt
        """
        categories = [cat.value for cat in MemoryCategory]

        return f"""You are a memory extraction assistant. Analyze this conversation and extract factual information about the user.

CATEGORIES: {', '.join(categories)}

CONVERSATION:
{formatted_conversation}

INSTRUCTIONS:
1. Extract 5-15 distinct memories
2. Each memory: factual, concise (1-2 sentences), confidence-scored (0.0-1.0)
3. Output JSON array only (no extra text)

FORMAT:
[
  {{"category": "interests", "content": "...", "confidence": 0.95, "metadata": {{"related_topics": ["topic1", "topic2"]}}}},
  ...
]"""

    def _parse_extraction_response(self,
                                 response_text: str,
                                 session_id: str,
                                 timestamp: datetime) -> List[Dict[str, Any]]:
        """
        Parse LLM response into structured memories.

        Args:
            response_text: Raw LLM response
            session_id: Session identifier
            timestamp: Extraction timestamp

        Returns:
            List of validated memory dictionaries
        """
        try:
            # Extract JSON from response (handle potential extra text)
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1

            if json_start == -1 or json_end == 0:
                logger.warning(f"No JSON found in extraction response: {response_text[:200]}...")
                return []

            json_text = response_text[json_start:json_end]
            memories = json.loads(json_text)

            # Validate and enhance memories
            validated_memories = []
            for i, mem in enumerate(memories):
                if self._validate_memory(mem):
                    enhanced_mem = self._enhance_memory(mem, session_id, timestamp, i)
                    validated_memories.append(enhanced_mem)

            return validated_memories

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extraction response as JSON: {e}")
            logger.debug(f"Raw response: {response_text}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error parsing extraction response: {e}")
            return []

    def _validate_memory(self, memory: Dict[str, Any]) -> bool:
        """
        Validate memory structure and content.

        Args:
            memory: Memory dictionary to validate

        Returns:
            True if memory is valid
        """
        required_fields = ["category", "content", "confidence"]

        # Check required fields
        for field in required_fields:
            if field not in memory:
                logger.warning(f"Memory missing required field '{field}': {memory}")
                return False

        # Validate category
        if memory["category"] not in [cat.value for cat in MemoryCategory]:
            logger.warning(f"Invalid memory category '{memory['category']}': {memory}")
            return False

        # Validate confidence
        if not isinstance(memory["confidence"], (int, float)) or not (0.0 <= memory["confidence"] <= 1.0):
            logger.warning(f"Invalid confidence score {memory['confidence']}: {memory}")
            return False

        # Validate content
        if not isinstance(memory["content"], str) or len(memory["content"].strip()) == 0:
            logger.warning(f"Invalid content: {memory}")
            return False

        return True

    def _enhance_memory(self,
                       memory: Dict[str, Any],
                       session_id: str,
                       timestamp: datetime,
                       index: int) -> Dict[str, Any]:
        """
        Enhance memory with additional metadata and PII detection.

        Args:
            memory: Base memory dictionary
            session_id: Session identifier
            timestamp: Extraction timestamp
            index: Memory index for ID generation

        Returns:
            Enhanced memory dictionary
        """
        # Generate unique ID
        memory_id = f"mem_{timestamp.strftime('%Y_%m_%d_%H%M%S')}_{index:03d}"

        # Detect PII
        pii_check = self._detect_pii(memory["content"])

        # Build enhanced memory
        enhanced = {
            "id": memory_id,
            "category": memory["category"],
            "content": memory["content"].strip(),
            "confidence": float(memory["confidence"]),
            "source": session_id,
            "created_at": timestamp.isoformat(),
            "metadata": memory.get("metadata", {})
        }

        # Add PII metadata
        if pii_check["has_pii"]:
            enhanced["metadata"]["privacy_sensitive"] = True
            enhanced["metadata"]["pii_types"] = pii_check["types"]
        else:
            enhanced["metadata"]["privacy_sensitive"] = False

        return enhanced