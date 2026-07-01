"""
AI Provider Abstraction Layer and Prompt Builder for AI Company OS.

Feature 17.1 -- AI Provider Abstraction:
  This package is the ONLY place that knows how to talk to an AI model.
  The rest of AI Company OS must never know which provider is in use.

Feature 17.2 -- Prompt Builder:
  The PromptBuilder converts structured PromptContext objects into
  PromptResult objects containing system and user prompts.  It knows
  nothing about any specific provider -- it only builds prompts.

Architecture reference: §2.10 LLM Gateway, §3 Layer 2 (Intelligence Layer).
"""
