"""
AI Provider Abstraction Layer for AI Company OS.

This package is the ONLY place that knows how to talk to an AI model.
The rest of AI Company OS must never know which provider is in use.

Architecture reference: §2.10 LLM Gateway, §3 Layer 2 (Intelligence Layer).
"""
