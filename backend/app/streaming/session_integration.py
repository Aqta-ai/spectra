"""
Fast Pipeline Integration for SpectraStreamingSession
This module provides helper methods to integrate the fast pipeline into the session
"""

import asyncio
import logging
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


async def process_frame_with_pipeline(
    session: 'SpectraStreamingSession',
    frame_data: bytes,
    last_user_text: str = ""
) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Enhanced frame processing with smart optimizations.
    
    Returns:
        (should_skip_gemini, cached_description, predictions) tuple
        - should_skip_gemini: True if we can use cached data
        - cached_description: The cached description if available
        - predictions: Predicted next actions for proactive assistance
    """
    try:
        # Use enhanced fast pipeline
        pipeline_result = await session.fast_pipeline.process_command(
            command=last_user_text or "describe screen",
            frame_data=frame_data,
            gemini_session=session
        )
        
        frame_hash = pipeline_result['frame_hash']
        frame_changed = pipeline_result['frame_changed']
        cached_description = pipeline_result.get('cached_description')
        predictions = pipeline_result.get('predictions', [])
        intent = pipeline_result.get('intent', {})
        cached_elements = pipeline_result.get('cached_elements', [])
        
        # Log enhanced performance metrics
        processing_time = pipeline_result.get('processing_time', 0)
        cache_hit = pipeline_result.get('cache_hit', False)
        
        logger.info(
            f"[FastPipeline] Frame processed in {processing_time*1000:.1f}ms "
            f"(changed={frame_changed}, cached={cached_description is not None}, "
            f"intent={intent.get('type', 'unknown')}, predictions={len(predictions)})"
        )
        
        # Track ultra-fast responses
        if processing_time < 0.2:
            logger.info(f"[FastPipeline] ⚡ Ultra-fast response achieved!")
        
        # Update session state
        session._frame_hash = frame_hash
        session._last_intent = intent
        session._cached_elements = cached_elements
        
        # Smart caching decision
        should_skip = False
        if cache_hit and intent.get('confidence', 0) > 0.8:
            # High confidence cached response
            should_skip = True
            logger.info(f"[FastPipeline] Using high-confidence cached response")
        elif not frame_changed and cached_description and intent.get('type') == 'read':
            # Frame unchanged and user wants to read - use cache
            should_skip = True
            logger.info(f"[FastPipeline] Using cached description for read intent")
        
        # Precompute likely next actions in background
        if predictions and not should_skip:
            asyncio.create_task(
                session.fast_pipeline.precompute_likely_actions(
                    last_user_text, frame_hash
                )
            )
        
        return should_skip, cached_description, predictions
        
    except Exception as e:
        logger.error(f"[FastPipeline] Error processing frame: {e}")
        return False, None, []


def cache_description_result(
    session: 'SpectraStreamingSession',
    frame_hash: str,
    description: str,
    elements: list = None
):
    """Enhanced caching with element detection"""
    try:
        # Cache description
        session.fast_pipeline.cache_frame_description(
            frame_hash=frame_hash,
            description=description,
            elements=elements or []
        )
        
        # Cache elements separately for faster access
        if elements:
            session.fast_pipeline.cache_elements(frame_hash, elements)
        
        logger.info(f"[FastPipeline] Cached description + {len(elements or [])} elements for frame {frame_hash[:8]}")
    except Exception as e:
        logger.error(f"[FastPipeline] Error caching description: {e}")


def update_action_result(
    session: 'SpectraStreamingSession',
    action: str,
    success: bool,
    command: str = ""
):
    """Enhanced action result tracking with learning"""
    try:
        # Update predictor
        session.fast_pipeline.update_action_result(action, success)
        
        # Learn shortcuts from successful commands
        if success and command and len(command.strip()) > 3:
            # Extract key phrases from successful commands
            key_phrases = _extract_key_phrases(command)
            for phrase in key_phrases:
                session.fast_pipeline.action_predictor.learn_shortcut(
                    command=phrase,
                    action_type=action,
                    params={},
                    confidence=0.7
                )
        
        logger.debug(f"[FastPipeline] Updated action result: {action} -> {success}")
    except Exception as e:
        logger.error(f"[FastPipeline] Error updating action result: {e}")


def _extract_key_phrases(command: str) -> list[str]:
    """Extract meaningful phrases from commands for learning"""
    command_lower = command.lower().strip()
    
    # Common meaningful phrases
    phrases = []
    
    # Extract action + target patterns
    action_words = ['click', 'press', 'type', 'scroll', 'go', 'open', 'search', 'find']
    for action in action_words:
        if action in command_lower:
            # Find the phrase around the action word
            words = command_lower.split()
            if action in words:
                idx = words.index(action)
                # Take action + next 1-2 words
                if idx + 1 < len(words):
                    phrases.append(f"{action} {words[idx + 1]}")
                if idx + 2 < len(words):
                    phrases.append(f"{action} {words[idx + 1]} {words[idx + 2]}")
    
    # Extract complete short commands
    if len(command_lower.split()) <= 3:
        phrases.append(command_lower)
    
    return phrases


def get_performance_metrics(session: 'SpectraStreamingSession') -> dict:
    """Get enhanced performance metrics"""
    try:
        base_metrics = session.fast_pipeline.get_metrics()
        
        # Add derived metrics
        total_requests = base_metrics.get('total_requests', 0)
        sub_200ms = base_metrics.get('sub_200ms_responses', 0)
        
        enhanced_metrics = {
            **base_metrics,
            'ultra_fast_percentage': (sub_200ms / total_requests * 100) if total_requests > 0 else 0,
            'cache_hit_rate': (base_metrics.get('cache_hits', 0) / 
                             max(base_metrics.get('cache_hits', 0) + base_metrics.get('cache_misses', 0), 1)) * 100,
            'prediction_accuracy': (base_metrics.get('predictions_correct', 0) / 
                                  max(base_metrics.get('predictions_made', 0), 1)) * 100,
            'learning_stats': session.fast_pipeline.action_predictor.get_learning_stats()
        }
        
        return enhanced_metrics
    except Exception as e:
        logger.error(f"[FastPipeline] Error getting metrics: {e}")
        return {}


async def provide_proactive_suggestions(
    session: 'SpectraStreamingSession',
    predictions: list,
    intent: dict
) -> Optional[str]:
    """Provide proactive suggestions based on predictions"""
    try:
        if not predictions or intent.get('confidence', 0) < 0.7:
            return None
        
        # Generate contextual suggestions
        suggestions = []
        
        for pred in predictions[:2]:  # Top 2 predictions
            if pred.confidence > 0.8:
                if pred.action_type == 'click_element':
                    suggestions.append("I can help you click on elements")
                elif pred.action_type == 'type_text':
                    suggestions.append("I can help you fill in forms")
                elif pred.action_type == 'scroll_page':
                    suggestions.append("I can help you scroll through content")
        
        if suggestions:
            return f"Suggestion: {suggestions[0]}"
        
        return None
        
    except Exception as e:
        logger.error(f"[FastPipeline] Error providing suggestions: {e}")
        return None
