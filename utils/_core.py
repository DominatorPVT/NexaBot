"""
utils/_core.py - Internal API configuration (DO NOT SHARE THIS FILE PUBLICLY)
================================================================================
This file holds the AI API endpoint separately from config.py so it stays
out of the main configuration that gets shared/copied around.
"""

AI_API_URL    = "https://copilot-api-delta.vercel.app"
AI_MODEL      = "copilot"
AI_MAX_TOKENS = 1000
