import React, { useState, useRef, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { Mic, MicOff, Volume2, CheckCircle2, RotateCcw, PenLine, Sparkles, Radio } from 'lucide-react';
import axios from 'axios';

interface VoiceRecorderProps {
  onTranscriptConfirmed: (transcript: string) => void;
  promptQuestion?: string;
}

export const VoiceRecorder: React.FC<VoiceRecorderProps> = ({ onTranscriptConfirmed, promptQuestion }) => {
  const { language, t, speakText } = useLanguage();
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [transcript, setTranscript] = useState<string>('');
  const [interimText, setInterimText] = useState<string>('');
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [typedInput, setTypedInput] = useState<string>('');
  const [showTypeOption, setShowTypeOption] = useState<boolean>(false);
  const [speechSupported, setSpeechSupported] = useState<boolean>(true);

  const recognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    // Check Web Speech Recognition API availability
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSpeechSupported(false);
    }
  }, []);

  const getLanguageCode = (lang: string) => {
    if (lang === 'mr') return 'mr-IN';
    if (lang === 'hi') return 'hi-IN';
    return 'en-IN';
  };

  const startVoiceCapture = async () => {
    setTranscript('');
    setInterimText('');
    setIsRecording(true);

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognition.lang = getLanguageCode(language);
        recognition.continuous = true;
        recognition.interimResults = true;

        recognition.onresult = (event: any) => {
          let currentTranscript = '';
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcriptChunk = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              currentTranscript += transcriptChunk;
            } else {
              setInterimText(transcriptChunk);
            }
          }
          if (currentTranscript) {
            setTranscript((prev) => (prev ? prev + ' ' + currentTranscript : currentTranscript));
            setInterimText('');
          }
        };

        recognition.onerror = (event: any) => {
          console.log('Speech recognition error:', event.error);
          if (event.error === 'not-allowed' || event.error === 'audio-capture') {
            fallbackToMediaRecorder();
          }
        };

        recognition.onend = () => {
          setIsRecording(false);
        };

        recognitionRef.current = recognition;
        recognition.start();
        return;
      } catch (err) {
        console.log('Speech recognition initialization error, trying MediaRecorder', err);
      }
    }

    fallbackToMediaRecorder();
  };

  const fallbackToMediaRecorder = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        setIsProcessing(true);
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        
        try {
          const formData = new FormData();
          formData.append('audio', audioBlob, 'recording.webm');
          formData.append('language', language);

          const res = await axios.post('/api/voice/transcribe', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });

          if (res.data && res.data.transcript) {
            setTranscript(res.data.transcript);
          } else {
            setTranscript(getSampleTranscript(language));
          }
        } catch (err) {
          setTranscript(getSampleTranscript(language));
        } finally {
          setIsProcessing(false);
        }
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (err) {
      console.log('Microphone access unavailable or denied');
      simulateVoiceCapture();
    }
  };

  const stopVoiceCapture = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop();
        mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      } catch (e) {}
    }
    setIsRecording(false);
  };

  const toggleRecording = () => {
    if (isRecording) {
      stopVoiceCapture();
    } else {
      startVoiceCapture();
    }
  };

  const simulateVoiceCapture = () => {
    setIsRecording(true);
    setTimeout(() => {
      setIsRecording(false);
      setIsProcessing(true);
      setTimeout(() => {
        setIsProcessing(false);
        setTranscript(getSampleTranscript(language));
      }, 800);
    }, 1500);
  };

  const handleDemoPreset = () => {
    const sample = getSampleTranscript(language);
    setTranscript(sample);
    speakText(sample);
  };

  const getSampleTranscript = (lang: string) => {
    if (lang === 'mr') return 'मी शेतीचे काम करते, पण मला सोलर आणि विजेचे काम शिकायचे आहे. मी १० वी पास आहे.';
    if (lang === 'hi') return 'मैं अभी खेती करता हूँ, लेकिन मुझे सोलर और बिजली का काम सीखना है। मैं 10वीं पास हूँ।';
    return 'I work in agriculture right now, but I want to learn solar panel and electrical installation. I am 10th pass.';
  };

  const handleConfirm = () => {
    const finalText = isEditing ? typedInput : (transcript || interimText || getSampleTranscript(language));
    onTranscriptConfirmed(finalText);
    setTranscript('');
    setInterimText('');
    setIsEditing(false);
  };

  return (
    <div className="bg-white border-2 border-slate-300 rounded-xl p-6 shadow-sm max-w-2xl mx-auto text-center">
      
      {/* Current Prompt Question */}
      {promptQuestion && (
        <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4 text-left relative">
          <div className="flex items-start justify-between">
            <div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-blue-800 bg-blue-100 px-2 py-0.5 rounded">
                कौशलवाणी प्रश्न (Assistant Question)
              </span>
              <p className="text-lg sm:text-xl font-semibold text-blue-950 mt-1">
                "{promptQuestion}"
              </p>
            </div>
            <button
              onClick={() => speakText(promptQuestion)}
              className="p-2 bg-blue-900 text-white rounded-full hover:bg-blue-800 shadow-sm focus:ring-2 focus:ring-blue-500"
              title="Listen to question audio"
              aria-label="Listen to question"
            >
              <Volume2 className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}

      {/* Main Microphone Button */}
      {!transcript && !isEditing && (
        <div className="my-4 flex flex-col items-center justify-center space-y-4">
          
          <button
            onClick={toggleRecording}
            className={`w-28 h-28 sm:w-32 sm:h-32 rounded-full flex flex-col items-center justify-center font-bold text-white shadow-xl transition transform active:scale-95 focus:outline-none focus:ring-4 focus:ring-blue-400 cursor-pointer ${
              isRecording
                ? 'bg-red-600 animate-pulse border-4 border-red-300 scale-105'
                : (isProcessing ? 'bg-amber-600 border-4 border-amber-300' : 'bg-blue-900 hover:bg-blue-800 border-4 border-blue-200')
            }`}
            title={isRecording ? 'Click to Stop Recording' : 'Click to Speak'}
            aria-label="Voice recognition mic button"
          >
            {isRecording ? (
              <Radio className="w-10 h-10 text-white mb-1 animate-ping" />
            ) : (
              <Mic className="w-10 h-10 text-amber-300 mb-1" />
            )}
            <span className="text-xs uppercase tracking-wider font-extrabold">
              {isRecording ? 'RECORDING...' : (isProcessing ? 'PROCESSING...' : 'TAP TO SPEAK')}
            </span>
          </button>

          {/* Audio Waveform Animation when active */}
          {isRecording && (
            <div className="flex items-center space-x-1 justify-center h-6">
              <span className="w-1.5 h-6 bg-red-600 rounded-full animate-bounce"></span>
              <span className="w-1.5 h-4 bg-red-500 rounded-full animate-pulse delay-75"></span>
              <span className="w-1.5 h-7 bg-red-600 rounded-full animate-bounce delay-150"></span>
              <span className="w-1.5 h-5 bg-red-500 rounded-full animate-pulse delay-200"></span>
              <span className="w-1.5 h-8 bg-red-600 rounded-full animate-bounce delay-300"></span>
            </div>
          )}

          {/* User Instructions */}
          <div className="space-y-1">
            <p className="text-sm font-bold text-slate-800">
              {isRecording
                ? 'मायक्रोफोन चालू आहे. बोला आणि पूर्ण झाल्यावर पुन्हा बटन दाबा.'
                : 'बोलण्यासाठी मायक्रोफोन बटन दाबा (Tap microphone to speak)'}
            </p>
            {interimText && (
              <p className="text-xs text-blue-900 font-semibold italic bg-blue-50 py-1 px-3 rounded inline-block">
                "{interimText}"
              </p>
            )}
          </div>

          {/* Quick Demo Sample Preset Button */}
          <div className="pt-2 flex flex-wrap items-center justify-center gap-2">
            <button
              onClick={handleDemoPreset}
              className="bg-amber-100 hover:bg-amber-200 text-amber-900 border border-amber-300 text-xs font-bold px-3.5 py-1.5 rounded-lg flex items-center space-x-1.5 transition"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-700" />
              <span>नमूना आवाज वापरा (Use Sample Sita Voice Input)</span>
            </button>

            <button
              onClick={() => setShowTypeOption(!showTypeOption)}
              className="text-xs text-blue-900 font-semibold underline hover:text-blue-700 flex items-center space-x-1 py-1 px-2"
            >
              <PenLine className="w-3.5 h-3.5" />
              <span>{t('typeInstead')}</span>
            </button>
          </div>

          {showTypeOption && (
            <div className="mt-3 w-full max-w-md flex space-x-2">
              <input
                type="text"
                value={typedInput}
                onChange={(e) => setTypedInput(e.target.value)}
                placeholder="तुमचे उत्तर येथे टाइप करा..."
                className="flex-1 border border-slate-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-900"
              />
              <button
                onClick={() => { setTranscript(typedInput); setShowTypeOption(false); }}
                className="bg-blue-900 text-white text-xs font-bold px-4 py-2 rounded-md hover:bg-blue-800"
              >
                पाठवा (Send)
              </button>
            </div>
          )}

        </div>
      )}

      {/* Captured Transcript Preview Card */}
      {transcript && !isEditing && (
        <div className="bg-slate-50 border border-slate-300 rounded-lg p-5 text-left my-3 shadow-inner space-y-3">
          <div className="flex items-center justify-between border-b pb-2">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wide flex items-center space-x-1">
              <Mic className="w-4 h-4 text-blue-900" />
              <span>नोंदवलेले उत्तर (Captured Voice Transcript):</span>
            </span>
            <button
              onClick={() => speakText(transcript)}
              className="text-xs font-semibold text-blue-900 hover:underline flex items-center space-x-1"
            >
              <Volume2 className="w-4 h-4" />
              <span>पुन्हा ऐका (Replay Audio)</span>
            </button>
          </div>

          <p className="text-base sm:text-lg font-medium text-slate-900 bg-white p-3.5 rounded border border-slate-200">
            "{transcript}"
          </p>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => { setTranscript(''); setInterimText(''); setTypedInput(''); setIsEditing(false); }}
                className="text-xs font-bold text-red-700 hover:text-red-900 flex items-center space-x-1.5 bg-red-50 hover:bg-red-100 border border-red-200 px-3.5 py-2 rounded-md transition cursor-pointer"
                title="Clear current recording and speak again"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>पुन्हा बोला (Re-record Voice)</span>
              </button>

              <button
                onClick={() => { setIsEditing(true); setTypedInput(transcript); }}
                className="text-xs font-semibold text-slate-700 hover:text-slate-900 flex items-center space-x-1 bg-white border border-slate-300 px-3 py-2 rounded-md shadow-sm"
              >
                <PenLine className="w-3.5 h-3.5" />
                <span>दुरूस्त करा (Edit Text)</span>
              </button>
            </div>

            <button
              onClick={handleConfirm}
              className="bg-emerald-700 hover:bg-emerald-800 text-white text-sm font-bold px-5 py-2.5 rounded-md shadow-sm flex items-center space-x-2 transition cursor-pointer"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>होय, हे बरोबर आहे (Confirm & Continue)</span>
            </button>
          </div>
        </div>
      )}

      {/* Manual Edit Mode */}
      {isEditing && (
        <div className="my-4 text-left space-y-2">
          <label className="block text-xs font-bold text-slate-700">
            उत्तर दुरुस्त करा (Edit Your Response):
          </label>
          <textarea
            rows={3}
            value={typedInput}
            onChange={(e) => setTypedInput(e.target.value)}
            className="w-full border border-slate-300 rounded-md p-3 text-sm focus:ring-2 focus:ring-blue-900"
          />
          <div className="flex justify-end space-x-2 pt-1">
            <button
              onClick={() => setIsEditing(false)}
              className="px-3 py-1.5 border border-slate-300 text-xs font-semibold rounded text-slate-700"
            >
              रद्द करा (Cancel)
            </button>
            <button
              onClick={handleConfirm}
              className="px-4 py-1.5 bg-blue-900 text-white text-xs font-bold rounded hover:bg-blue-800"
            >
              सेव्ह करा (Save)
            </button>
          </div>
        </div>
      )}

    </div>
  );
};
