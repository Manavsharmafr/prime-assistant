// Web Speech API interface definitions for TypeScript support
interface SpeechRecognitionEvent {
  resultIndex: number;
  results: {
    [index: number]: {
      [index: number]: {
        transcript: string;
      };
      isFinal: boolean;
    };
    length: number;
  };
}

interface SpeechRecognitionErrorEvent {
  error: string;
  message: string;
}

interface ISpeechRecognition {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onstart: () => void;
  onresult: (event: SpeechRecognitionEvent) => void;
  onerror: (event: SpeechRecognitionErrorEvent) => void;
  onend: () => void;
  start: () => void;
  stop: () => void;
}

// Extends global Window interface
declare global {
  interface Window {
    webkitSpeechRecognition?: new () => ISpeechRecognition;
    SpeechRecognition?: new () => ISpeechRecognition;
  }
}

export class PrimeSpeechEngine {
  private recognition: ISpeechRecognition | null = null;
  private synthesis: SpeechSynthesis = window.speechSynthesis;
  private currentUtterance: SpeechSynthesisUtterance | null = null;
  private onResultCallback: (text: string, isFinal: boolean) => void = () => {};
  private onStatusChangeCallback: (status: 'idle' | 'listening' | 'speaking') => void = () => {};
  
  public isListening = false;

  constructor() {
    const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognitionClass) {
      this.recognition = new SpeechRecognitionClass();
      this.recognition.continuous = true;
      this.recognition.interimResults = true;
      this.recognition.lang = 'en-US';

      this.recognition.onstart = () => {
        this.isListening = true;
        this.onStatusChangeCallback('listening');
      };

      this.recognition.onresult = (event: SpeechRecognitionEvent) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }

        if (finalTranscript.trim()) {
          this.onResultCallback(finalTranscript, true);
        } else if (interimTranscript.trim()) {
          this.onResultCallback(interimTranscript, false);
        }
      };

      this.recognition.onerror = (err: SpeechRecognitionErrorEvent) => {
        console.error('Speech recognition error:', err.error);
        if (err.error !== 'no-speech') {
          this.stopListening();
        }
      };

      this.recognition.onend = () => {
        this.isListening = false;
        // Check if we want to auto-restart, but for now fallback to idle status
        this.onStatusChangeCallback('idle');
      };
    } else {
      console.warn('Web Speech API (Speech Recognition) is not supported in this browser.');
    }
  }

  public setCallbacks(
    onResult: (text: string, isFinal: boolean) => void,
    onStatusChange: (status: 'idle' | 'listening' | 'speaking') => void
  ) {
    this.onResultCallback = onResult;
    this.onStatusChangeCallback = onStatusChange;
  }

  public startListening() {
    if (this.recognition && !this.isListening) {
      this.stopSpeaking(); // Interrupt speaking when listening starts
      try {
        this.recognition.start();
      } catch (e) {
        console.error('Failed to start speech recognition:', e);
      }
    }
  }

  public stopListening() {
    if (this.recognition && this.isListening) {
      try {
        this.recognition.stop();
        this.isListening = false;
        this.onStatusChangeCallback('idle');
      } catch (e) {
        console.error('Failed to stop speech recognition:', e);
      }
    }
  }

  public speak(text: string, onEnd: () => void = () => {}) {
    this.stopSpeaking();
    
    // Temporarily halt listening while speaking to prevent echo/feedback loops
    const wasListening = this.isListening;
    if (wasListening) {
      this.stopListening();
    }

    this.currentUtterance = new SpeechSynthesisUtterance(text);
    
    // Choose a high quality default voice if available
    const voices = this.synthesis.getVoices();
    const premiumVoice = voices.find(
      v => v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('David')
    );
    if (premiumVoice) {
      this.currentUtterance.voice = premiumVoice;
    }

    this.currentUtterance.onstart = () => {
      this.onStatusChangeCallback('speaking');
    };

    this.currentUtterance.onend = () => {
      this.onStatusChangeCallback('idle');
      onEnd();
      // Resume listening if we were listening before
      if (wasListening) {
        this.startListening();
      }
    };

    this.currentUtterance.onerror = (e) => {
      console.error('Speech synthesis error:', e);
      this.onStatusChangeCallback('idle');
      if (wasListening) {
        this.startListening();
      }
    };

    this.synthesis.speak(this.currentUtterance);
  }

  public stopSpeaking() {
    if (this.synthesis.speaking) {
      this.synthesis.cancel();
    }
  }
}
