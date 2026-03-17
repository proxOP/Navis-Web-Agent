"""Tests for the minimal intent service."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "navis-backend"))

from services.intent_service import IntentService


def test_intent_service_heuristic_click():
    service = IntentService()
    intent = service._parse_heuristically("click login button")
    assert intent.action_type == "click"
    assert "login" in intent.keywords


def test_intent_service_heuristic_fill_form_requires_confirmation():
    service = IntentService()
    intent = service._parse_heuristically("fill the signup form")
    assert intent.action_type == "fill_form"
    assert intent.requires_confirmation is True


def test_intent_service_heuristic_scroll_down():
    service = IntentService()
    intent = service._parse_heuristically("scroll down a bit")
    assert intent.action_type == "scroll_down"
    assert intent.element_types == []
