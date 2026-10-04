// i18n string dictionary – EN and HI for all claimant-facing strings
// Note: claimant views NEVER show band/score/risk/heatmap/detector names

const strings = {
  en: {
    // Nav
    myClaimsNav: "My Claims",
    newClaimNav: "New Claim",
    logout: "Logout",
    lang: "हिंदी",

    // Login
    loginTitle: "Lucen AI",
    loginSubtitle: "Insurance Claims Platform",
    loginEmailLabel: "Email",
    loginPasswordLabel: "Password",
    loginBtn: "Sign In",
    loginRoleClaimant: "Claimant",
    loginRoleInvestigator: "Investigator (Staff)",
    loginLoading: "Signing in…",
    loginError: "Invalid email or password.",

    // My Claims list
    myClaimsTitle: "My Claims",
    newClaimBtn: "+ New Claim",
    claimId: "Claim ID",
    policyLabel: "Policy",
    claimType: "Type",
    claimedAmount: "Claimed",
    status: "Status",
    submittedAt: "Submitted",
    viewDetails: "View Details",
    noClaimsYet: "No claims filed yet.",

    // Status page
    claimStatus: "Claim Status",
    incidentDate: "Incident Date",
    peril: "Peril",
    description: "Description",
    evidenceTimeline: "Evidence & Updates",
    resubmitBtn: "Submit Additional Evidence",
    resubmitting: "Submitting…",
    resubmitSuccess: "Evidence submitted. Your claim is under review.",
    actionsLabel: "Actions",

    // Status values
    submitted: "Submitted",
    under_review: "Under Review",
    needs_evidence: "More Evidence Needed",
    approved: "Approved",
    rejected: "Decision Made",
    closed: "Closed",

    // Wizard
    wizardTitle: "File a New Claim",
    step1: "Policy & Type",
    step2: "Incident Details",
    step3: "Evidence",
    step4: "Consent & Submit",
    next: "Next",
    back: "Back",
    submit: "Submit Claim",
    submitting: "Submitting…",
    selectPolicy: "Select Policy",
    selectClaimType: "Claim Type",
    incidentDateLabel: "Incident Date",
    incidentTimeLabel: "Incident Time",
    locationTextLabel: "Location (text description)",
    claimedAmountLabel: "Claimed Amount (₹)",
    perilLabel: "Peril / Cause",
    descriptionLabel: "Description",
    evidenceFilesLabel: "Evidence Files (photos, documents)",
    idPhotoLabel: "ID Proof Photo",
    selfieLabel: "Selfie",
    captureCamera: "Camera",
    captureUpload: "Upload",
    consentText: "I agree that all information provided is accurate. I consent to verification checks for this claim.",
    consentRequired: "You must consent to submit.",
    claimSubmitted: "Claim submitted successfully.",

    // Generic
    loading: "Loading…",
    error: "An error occurred. Please try again.",
    na: "—",
  },

  hi: {
    // Nav
    myClaimsNav: "मेरे दावे",
    newClaimNav: "नया दावा",
    logout: "लॉग आउट",
    lang: "English",

    // Login
    loginTitle: "Lucen AI",
    loginSubtitle: "बीमा दावे पोर्टल",
    loginEmailLabel: "ईमेल",
    loginPasswordLabel: "पासवर्ड",
    loginBtn: "साइन इन करें",
    loginRoleClaimant: "दावेदार",
    loginRoleInvestigator: "अन्वेषक (स्टाफ)",
    loginLoading: "साइन इन हो रहा है…",
    loginError: "गलत ईमेल या पासवर्ड।",

    // My Claims list
    myClaimsTitle: "मेरे दावे",
    newClaimBtn: "+ नया दावा",
    claimId: "दावा ID",
    policyLabel: "पॉलिसी",
    claimType: "प्रकार",
    claimedAmount: "दावा राशि",
    status: "स्थिति",
    submittedAt: "जमा किया",
    viewDetails: "विवरण देखें",
    noClaimsYet: "अभी तक कोई दावा नहीं।",

    // Status page
    claimStatus: "दावे की स्थिति",
    incidentDate: "घटना की तारीख",
    peril: "कारण",
    description: "विवरण",
    evidenceTimeline: "साक्ष्य और अपडेट",
    resubmitBtn: "अतिरिक्त साक्ष्य जमा करें",
    resubmitting: "जमा हो रहा है…",
    resubmitSuccess: "साक्ष्य जमा हो गया। आपका दावा समीक्षा में है।",
    actionsLabel: "कार्रवाई",

    // Status values
    submitted: "जमा किया",
    under_review: "समीक्षाधीन",
    needs_evidence: "अधिक साक्ष्य चाहिए",
    approved: "स्वीकृत",
    rejected: "निर्णय लिया गया",
    closed: "बंद",

    // Wizard
    wizardTitle: "नया दावा दर्ज करें",
    step1: "पॉलिसी और प्रकार",
    step2: "घटना विवरण",
    step3: "साक्ष्य",
    step4: "सहमति और जमा",
    next: "आगे",
    back: "पीछे",
    submit: "दावा जमा करें",
    submitting: "जमा हो रहा है…",
    selectPolicy: "पॉलिसी चुनें",
    selectClaimType: "दावे का प्रकार",
    incidentDateLabel: "घटना की तारीख",
    incidentTimeLabel: "घटना का समय",
    locationTextLabel: "स्थान (विवरण)",
    claimedAmountLabel: "दावा राशि (₹)",
    perilLabel: "कारण / आपदा",
    descriptionLabel: "विवरण",
    evidenceFilesLabel: "साक्ष्य फ़ाइलें (फ़ोटो, दस्तावेज़)",
    idPhotoLabel: "पहचान प्रमाण फ़ोटो",
    selfieLabel: "सेल्फ़ी",
    captureCamera: "कैमरा",
    captureUpload: "अपलोड",
    consentText: "मैं सहमत हूँ कि दी गई सभी जानकारी सटीक है। मैं इस दावे के लिए सत्यापन जाँच की सहमति देता/देती हूँ।",
    consentRequired: "जमा करने के लिए सहमति आवश्यक है।",
    claimSubmitted: "दावा सफलतापूर्वक जमा हो गया।",

    // Generic
    loading: "लोड हो रहा है…",
    error: "एक त्रुटि हुई। कृपया पुनः प्रयास करें।",
    na: "—",
  }
};

export default strings;
