/**
 * React hook for multimodal feedback system
 */

import { useEffect, useRef, useState } from 'react';
import { getFeedbackSystem, type Action, type Result, type FeedbackPreferences } from '@/lib/feedbackSystem';

export function useFeedback(preferences?: Partial<FeedbackPreferences>) {
  const feedbackRef = useRef(getFeedbackSystem(preferences));
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    setIsInitialized(true);
  }, []);

  const provideFeedback = async (action: Action, result: Result) => {
    if (!isInitialized) return;
    await feedbackRef.current.provideFeedback(action, result);
  };

  const showSuccess = async (message?: string) => {
    if (!isInitialized) return;
    await feedbackRef.current.showSuccess(message);
  };

  const showError = async (message?: string) => {
    if (!isInitialized) return;
    await feedbackRef.current.showError(message);
  };

  const showProgress = (message: string) => {
    if (!isInitialized) return null;
    return feedbackRef.current.showProgress(message);
  };

  const setPreferences = (prefs: Partial<FeedbackPreferences>) => {
    feedbackRef.current.setPreferences(prefs);
  };

  const getPreferences = () => {
    return feedbackRef.current.getPreferences();
  };

  return {
    provideFeedback,
    showSuccess,
    showError,
    showProgress,
    setPreferences,
    getPreferences,
    isInitialized,
  };
}
