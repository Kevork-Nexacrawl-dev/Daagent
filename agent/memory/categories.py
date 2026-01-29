"""
Memory categories for Perplexity-style extraction.
Defines enum for categorizing user memories.
"""

from enum import Enum


class MemoryCategory(Enum):
    """Categories for user memory classification."""

    # User interests and topics
    INTERESTS = "interests"

    # Preferences for tools, workflows, decision styles
    PREFERENCES = "preferences"

    # Contact information (privacy-sensitive)
    CONTACT = "contact"

    # Personal information (name, age, location)
    PERSONAL = "personal"

    # Professional information (job, company)
    PROFESSIONAL = "professional"

    # Technical skills and expertise
    TECHNICAL = "technical"

    # Long-term objectives
    GOALS = "goals"

    # Usage patterns, habits
    HABITS = "habits"

    # Other miscellaneous memories
    OTHER = "other"