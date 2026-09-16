# admissions/constants.py

INPUT_CLASS = (
    'adm-control w-full px-4 py-3 border border-slate-200 rounded-xl bg-white text-slate-800 '
    'shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/25 focus:border-primary transition'
)

SELECT_CLASS = INPUT_CLASS + ' appearance-none'
TEXTAREA_CLASS = INPUT_CLASS

RESUME_COOKIE = 'admission_resume'
RESUME_COOKIE_MAX_AGE = 14 * 24 * 60 * 60

STEP_STUDENT = 1
STEP_FAMILY = 2
STEP_OTHERS = 3
STEP_DECLARATIONS = 4
STEP_SLOT = 5
STEP_REVIEW = 6
STEP_LABELS = {
    STEP_STUDENT: 'Student',
    STEP_FAMILY: 'Family',
    STEP_OTHERS: 'Others',
    STEP_DECLARATIONS: 'Declarations',
    STEP_SLOT: 'Viva',
    STEP_REVIEW: 'Review',
}

STEP_HINTS = {
    STEP_STUDENT: 'Student identity, photo, and present address',
    STEP_FAMILY: 'Parents, family income, and previous school',
    STEP_OTHERS: 'School bus and siblings in this school',
    STEP_DECLARATIONS: 'Confirm uniform, rules, and accuracy',
    STEP_SLOT: 'Reserve a viva date and time',
    STEP_REVIEW: 'Check everything, then continue to payment',
}

CACHE_SKIP_PREFIXES = (
    '/admission/',
    '/admin/',
    '/contact/',
    '/editor/',
)
