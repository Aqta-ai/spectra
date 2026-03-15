/**
 * Onboarding Hook
 * Manages first-time user experience and onboarding state
 */

import { useState, useEffect } from 'react';

const ONBOARDING_STORAGE_KEY = 'spectra_onboarding_completed';
const SCREEN_SHARED_STORAGE_KEY = 'spectra_screen_ever_shared';

export function useOnboarding() {
  const [isFirstTime, setIsFirstTime] = useState(true);
  const [hasSharedScreen, setHasSharedScreen] = useState(false);
  const [onboardingDismissed, setOnboardingDismissed] = useState(false);

  // Check if user has completed onboarding before
  useEffect(() => {
    try {
      const completed = localStorage.getItem(ONBOARDING_STORAGE_KEY);
      const screenShared = localStorage.getItem(SCREEN_SHARED_STORAGE_KEY);
      
      setIsFirstTime(completed !== 'true');
      setHasSharedScreen(screenShared === 'true');
    } catch (error) {
      console.error('[Onboarding] Failed to load state:', error);
    }
  }, []);

  const markOnboardingComplete = () => {
    try {
      localStorage.setItem(ONBOARDING_STORAGE_KEY, 'true');
      setIsFirstTime(false);
    } catch (error) {
      console.error('[Onboarding] Failed to save completion:', error);
    }
  };

  const markScreenShared = () => {
    try {
      localStorage.setItem(SCREEN_SHARED_STORAGE_KEY, 'true');
      setHasSharedScreen(true);
      
      // Also mark onboarding as complete when screen is shared
      if (isFirstTime) {
        markOnboardingComplete();
      }
    } catch (error) {
      console.error('[Onboarding] Failed to save screen share:', error);
    }
  };

  const dismissOnboarding = () => {
    setOnboardingDismissed(true);
  };

  const resetOnboarding = () => {
    try {
      localStorage.removeItem(ONBOARDING_STORAGE_KEY);
      localStorage.removeItem(SCREEN_SHARED_STORAGE_KEY);
      setIsFirstTime(true);
      setHasSharedScreen(false);
      setOnboardingDismissed(false);
    } catch (error) {
      console.error('[Onboarding] Failed to reset:', error);
    }
  };

  const shouldShowOnboarding = isFirstTime && !hasSharedScreen && !onboardingDismissed;

  return {
    isFirstTime,
    hasSharedScreen,
    shouldShowOnboarding,
    markOnboardingComplete,
    markScreenShared,
    dismissOnboarding,
    resetOnboarding,
  };
}
