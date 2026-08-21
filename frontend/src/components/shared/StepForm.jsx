import { useState, useRef, useEffect } from 'react';

/**
 * StepForm — Conversational Multi-Step Onboarding Form Component
 *
 * Matching exact reference design:
 * - Top Progress Track with "X/N" + Checkmark icon (left) and "%" (right)
 * - Single Card Enclosure matching KueryCore dark cosmic theme
 * - Non-editable Question display bar with subtle bevel top highlight
 * - Answer input field with integrated circular green submit button (arrow icon)
 * - Animated fade/slide transition between steps
 * - Fully reusable via `steps` prop
 */
export default function StepForm({
  steps = [
    {
      id: 'name',
      question: "Welcome! What's your name?",
      placeholder: 'Type your answer...',
      type: 'text',
      required: true,
    },
    {
      id: 'role',
      question: 'What is your primary role or domain?',
      placeholder: 'e.g. Software Engineer, Legal Researcher, Data Scientist...',
      type: 'text',
      required: true,
    },
    {
      id: 'useCase',
      question: 'What type of documents will you analyze most?',
      placeholder: 'e.g. Architecture Docs, Financial Reports, Research Papers...',
      type: 'text',
      required: true,
    },
    {
      id: 'goal',
      question: 'What is your main objective with KueryCore AI?',
      placeholder: 'e.g. Grounded QA, compliance check, rapid synthesis...',
      type: 'text',
      required: true,
    },
  ],
  onComplete,
  onCancel,
  initialValues = {},
}) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [answers, setAnswers] = useState(initialValues);
  const [currentValue, setCurrentValue] = useState(initialValues[steps[0]?.id] || '');
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [direction, setDirection] = useState('forward'); // 'forward' | 'backward'
  const inputRef = useRef(null);

  const totalSteps = steps.length;
  const currentStep = steps[currentStepIndex];
  const progressPercent = Math.round(((currentStepIndex + 1) / totalSteps) * 100);

  // Auto-focus input on step change
  useEffect(() => {
    setCurrentValue(answers[currentStep?.id] || '');
    const timer = setTimeout(() => {
      inputRef.current?.focus();
    }, 150);
    return () => clearTimeout(timer);
  }, [currentStepIndex]);

  const handleNext = (e) => {
    if (e) e.preventDefault();
    if (currentStep.required && !currentValue.trim()) {
      return;
    }

    const updatedAnswers = {
      ...answers,
      [currentStep.id]: currentValue.trim(),
    };
    setAnswers(updatedAnswers);

    if (currentStepIndex < totalSteps - 1) {
      setDirection('forward');
      setIsTransitioning(true);
      setTimeout(() => {
        setCurrentStepIndex((prev) => prev + 1);
        setIsTransitioning(false);
      }, 200);
    } else {
      if (onComplete) {
        onComplete(updatedAnswers);
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleNext();
    }
  };

  const handlePrev = () => {
    if (currentStepIndex > 0) {
      setDirection('backward');
      setIsTransitioning(true);
      setTimeout(() => {
        setCurrentStepIndex((prev) => prev - 1);
        setIsTransitioning(false);
      }, 200);
    }
  };

  const isLastStep = currentStepIndex === totalSteps - 1;
  const canSubmit = !currentStep.required || currentValue.trim().length > 0;

  return (
    <div className="w-full max-w-xl mx-auto flex flex-col items-center select-none px-4 py-8">
      {/* ── Top Progress Header ── */}
      <div className="w-full mb-6">
        <div className="flex items-center justify-between text-xs font-semibold mb-2">
          {/* Step Indicator + Checkmark */}
          <div className="flex items-center gap-1.5 text-white">
            <span className="tracking-tight text-[13px] font-bold">
              {currentStepIndex + 1}/{totalSteps}
            </span>
            <div
              className="w-4 h-4 rounded-full flex items-center justify-center"
              style={{
                background: 'rgba(0, 214, 143, 0.15)',
                border: '1px solid rgba(0, 214, 143, 0.4)',
              }}
            >
              <svg
                width="10"
                height="10"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#00d68f"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </div>
          </div>

          {/* Percentage */}
          <span className="text-[13px] font-bold text-white tracking-tight">
            {progressPercent}%
          </span>
        </div>

        {/* Progress Track */}
        <div
          className="w-full h-1 rounded-full overflow-hidden"
          style={{ background: 'rgba(255, 255, 255, 0.1)' }}
        >
          <div
            className="h-full rounded-full transition-all duration-300 ease-out"
            style={{
              width: `${progressPercent}%`,
              background: 'linear-gradient(90deg, #00d68f 0%, #00ffaa 100%)',
              boxShadow: '0 0 10px rgba(0, 214, 143, 0.6)',
            }}
          />
        </div>
      </div>

      {/* ── Main Question Card (Matching Reference Image) ── */}
      <div
        className="w-full rounded-2xl p-6 transition-all duration-300 relative"
        style={{
          background: 'linear-gradient(180deg, rgba(13, 29, 21, 0.85) 0%, rgba(9, 20, 16, 0.95) 100%)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.06)',
        }}
      >
        <div
          className={`flex flex-col gap-3.5 transition-all duration-200 ${
            isTransitioning
              ? direction === 'forward'
                ? 'opacity-0 -translate-x-3'
                : 'opacity-0 translate-x-3'
              : 'opacity-100 translate-x-0'
          }`}
        >
          {/* Question Display Bar (Top dark rounded display bar) */}
          <div
            className="w-full px-5 py-4 rounded-xl flex items-center"
            style={{
              background: 'linear-gradient(180deg, #18201b 0%, #0e1612 100%)',
              border: '1px solid rgba(255, 255, 255, 0.09)',
              boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.1), 0 2px 8px rgba(0, 0, 0, 0.3)',
            }}
          >
            <p className="text-[15px] font-semibold text-white tracking-tight">
              {currentStep.question}
            </p>
          </div>

          {/* Answer Input Field with Integrated Circular Submit Button */}
          <form onSubmit={handleNext} className="w-full relative flex items-center">
            <input
              ref={inputRef}
              type={currentStep.type || 'text'}
              value={currentValue}
              onChange={(e) => setCurrentValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={currentStep.placeholder || 'Type your answer...'}
              className="w-full bg-[#050d08] border border-white/[0.1] hover:border-white/[0.18] focus:border-emerald-400/80 focus:ring-1 focus:ring-emerald-400/40 rounded-xl pl-5 pr-14 py-3.5 text-[14px] text-white placeholder:text-slate-500 focus:outline-none transition-all duration-150 shadow-inner"
            />

            {/* Circular Green Submit Arrow Button (Docked right inside input) */}
            <button
              type="submit"
              disabled={!canSubmit}
              aria-label={isLastStep ? 'Complete onboarding' : 'Next step'}
              className="absolute right-2.5 w-9 h-9 rounded-full flex items-center justify-center transition-all duration-150 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              style={{
                background: 'linear-gradient(135deg, #00d68f 0%, #00ffaa 100%)',
                color: '#020804',
                boxShadow: canSubmit
                  ? '0 2px 10px rgba(0, 214, 143, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.3)'
                  : 'none',
              }}
              onMouseEnter={(e) => {
                if (canSubmit) {
                  e.currentTarget.style.transform = 'scale(1.05)';
                  e.currentTarget.style.boxShadow = '0 4px 16px rgba(0, 214, 143, 0.7)';
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'scale(1)';
                if (canSubmit) {
                  e.currentTarget.style.boxShadow = '0 2px 10px rgba(0, 214, 143, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.3)';
                }
              }}
            >
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </button>
          </form>
        </div>

        {/* Back navigation option */}
        {currentStepIndex > 0 && (
          <div className="mt-4 flex justify-start">
            <button
              type="button"
              onClick={handlePrev}
              className="text-xs font-medium text-slate-400 hover:text-white flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <span>←</span>
              <span>Back</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
