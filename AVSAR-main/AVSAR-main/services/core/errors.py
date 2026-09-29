"""Speakable error contract.

ARCHITECTURE.md §5: *every non-2xx carries `{code, human_{lang}, retryable}` so
the client can SPEAK errors*.  RULE 7 requires every error to be speakable in
the active session language.
"""

from __future__ import annotations

from fastapi import HTTPException

LANGS = ("hi", "mr", "te", "en")

# code -> {lang: spoken sentence}
ERROR_MESSAGES: dict[str, dict[str, str]] = {
    "network_error": {
        "hi": "नेटवर्क में दिक्कत है। आप थोड़ी देर बाद फिर कोशिश करें।",
        "mr": "नेटवर्कमध्ये अडचण आहे. कृपया थोड्या वेळाने पुन्हा प्रयत्न करा.",
        "te": "నెట్‌వర్క్‌లో సమస్య ఉంది. దయచేసి కొద్దిసేపటి తర్వాత మళ్లీ ప్రయత్నించండి.",
        "en": "There is a network problem. Please try again in a moment.",
    },
    "db_unavailable": {
        "hi": "हमारी जानकारी अभी उपलब्ध नहीं है। थोड़ी देर में फिर कोशिश कीजिए।",
        "mr": "आमची माहिती सध्या उपलब्ध नाही. कृपया थोड्या वेळाने पुन्हा प्रयत्न करा.",
        "te": "మా సమాచారం ప్రస్తుతం అందుబాటులో లేదు. దయచేసి కొద్దిసేపటి తర్వాత ప్రయత్నించండి.",
        "en": "Our information is not available right now. Please try again shortly.",
    },
    "asr_empty": {
        "hi": "माफ़ कीजिए, आवाज़ साफ़ नहीं आई। आप बटन दबाकर भी बता सकते हैं।",
        "mr": "क्षमस्व, आवाज स्पष्ट आला नाही. तुम्ही बटण दाबूनही सांगू शकता.",
        "te": "క్షమించండి, మీ మాట స్పష్టంగా వినిపించలేదు. మీరు బటన్ నొక్కి కూడా చెప్పవచ్చు.",
        "en": "Sorry, I could not hear that clearly. You can also tap a button to answer.",
    },
    "consent_required": {
        "hi": "आगे बढ़ने के लिए पहले आपकी सहमति ज़रूरी है।",
        "mr": "पुढे जाण्यासाठी आधी तुमची संमती आवश्यक आहे.",
        "te": "ముందుకు వెళ్లడానికి మీ సమ్మతి అవసరం.",
        "en": "Your consent is needed before we continue.",
    },
    "session_not_found": {
        "hi": "यह बातचीत नहीं मिली। कृपया नई शुरुआत करें।",
        "mr": "हे संभाषण सापडले नाही. कृपया नव्याने सुरू करा.",
        "te": "ఈ సంభాషణ దొరకలేదు. దయచేసి కొత్తగా ప్రారంభించండి.",
        "en": "That conversation was not found. Please start again.",
    },
    "unauthorized": {
        "hi": "आपको इसकी अनुमति नहीं है। कृपया फिर से लॉगिन करें।",
        "mr": "तुम्हाला याची परवानगी नाही. कृपया पुन्हा लॉगिन करा.",
        "te": "మీకు దీనికి అనుమతి లేదు. దయచేసి మళ్లీ లాగిన్ చేయండి.",
        "en": "You are not authorised for this. Please sign in again.",
    },
    "forbidden": {
        "hi": "इस जानकारी तक आपकी पहुँच नहीं है।",
        "mr": "या माहितीपर्यंत तुमचा प्रवेश नाही.",
        "te": "ఈ సమాచారానికి మీకు అనుమతి లేదు.",
        "en": "You do not have access to this information.",
    },
    "rate_limited": {
        "hi": "बहुत तेज़ कोशिश हो रही है। एक मिनट रुककर फिर बोलिए।",
        "mr": "खूप वेगाने प्रयत्न होत आहेत. एक मिनिट थांबून पुन्हा बोला.",
        "te": "చాలా వేగంగా ప్రయత్నిస్తున్నారు. ఒక నిమిషం ఆగి మళ్లీ మాట్లాడండి.",
        "en": "That was too fast. Please wait a minute and speak again.",
    },
    "provider_unavailable": {
        "hi": "आवाज़ सेवा अभी उपलब्ध नहीं है, हम लिखकर बता रहे हैं।",
        "mr": "आवाज सेवा सध्या उपलब्ध नाही, आम्ही लिहून सांगत आहोत.",
        "te": "వాయిస్ సేవ ప్రస్తుతం అందుబాటులో లేదు, మేము వ్రాసి చెబుతున్నాము.",
        "en": "The voice service is unavailable, so we are showing this as text.",
    },
    "invalid_otp": {
        "hi": "यह कोड सही नहीं है। कृपया दोबारा डालें।",
        "mr": "हा कोड बरोबर नाही. कृपया पुन्हा टाका.",
        "te": "ఈ కోడ్ సరైనది కాదు. దయచేసి మళ్లీ నమోదు చేయండి.",
        "en": "That code is not correct. Please enter it again.",
    },
    "out_of_scope": {
        "hi": "यह जानकारी मेरे पास नहीं है। मैं आपको अधिकारी से जोड़ सकता हूँ।",
        "mr": "ही माहिती माझ्याकडे नाही. मी तुम्हाला अधिकाऱ्याशी जोडू शकतो.",
        "te": "ఈ సమాచారం నా వద్ద లేదు. నేను మిమ్మల్ని అధికారికి కనెక్ట్ చేయగలను.",
        "en": "I do not have that information. I can connect you to an officer.",
    },
    "bad_request": {
        "hi": "कुछ जानकारी अधूरी है। कृपया फिर से भेजें।",
        "mr": "काही माहिती अपूर्ण आहे. कृपया पुन्हा पाठवा.",
        "te": "కొంత సమాచారం అసంపూర్ణంగా ఉంది. దయచేసి మళ్లీ పంపండి.",
        "en": "Some information is missing. Please send it again.",
    },
}

RETRYABLE = {"network_error", "db_unavailable", "asr_empty", "rate_limited", "provider_unavailable"}


def error_payload(code: str, lang: str = "hi", detail: str | None = None) -> dict:
    """Build the `{code, human_{lang}, retryable}` body for a given code."""
    lang = lang if lang in LANGS else "en"
    messages = ERROR_MESSAGES.get(code, ERROR_MESSAGES["bad_request"])
    body = {
        "code": code,
        "retryable": code in RETRYABLE,
        "lang": lang,
        f"human_{lang}": messages.get(lang, messages["en"]),
        "human": messages.get(lang, messages["en"]),
    }
    if detail:
        body["detail"] = detail
    return body


class AvsarError(HTTPException):
    """HTTPException whose detail is always the speakable error contract."""

    def __init__(self, status_code: int, code: str, lang: str = "hi", detail: str | None = None):
        super().__init__(status_code=status_code, detail=error_payload(code, lang, detail))
        self.code = code
