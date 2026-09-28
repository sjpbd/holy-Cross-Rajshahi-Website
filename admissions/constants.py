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

STEP_TITLES = {
    **STEP_LABELS,
    STEP_STUDENT: 'Student (According to Birth Certificate)',
    STEP_FAMILY: 'Family (According to NID Card)',
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

NURSERY_CODE = 'nursery'
CLASS_6_REG_CODES = frozenset({'class-7', 'class-8', 'class-9'})
CLASS_8_REG_CODES = frozenset({'class-9'})
STUDY_GROUP_CODES = frozenset({'class-9'})

DECLARATION_INTRO = 'I, the applicant, hereby declare that:'
DECLARATIONS = [
    'I will wear the official school uniform regularly.',
    'I will abide by all the rules and regulations of the school.',
    'All the information provided in this application form is true and correct to the best of my knowledge.',
    'I understand that if any information provided is found to be false, incorrect, or misleading at any '
    'stage, the school authority reserves the right to cancel my application or admission without prior notice.',
    'I understand that the school authority reserves the right to reschedule or change the date and time of '
    'the viva and the admission test, if necessary.',
]
DECLARATION_AGREE = 'I agree to the above declaration.'

SKILL_OTHERS = 'others'
SKILL_CHOICES = [
    ('drawing', 'Drawing, Painting & Craft'),
    ('handwriting', 'Handwriting & Calligraphy'),
    ('music', 'Singing & Music'),
    ('photo_video', 'Photo & Videography'),
    ('dance_drama', 'Dance & Drama'),
    ('recitation', 'Recitation & Storytelling'),
    ('debating', 'Debating & Public Speaking'),
    ('creative_writing', 'Creative Writing'),
    ('sports', 'Sports & Athletics (Football, Cricket, Badminton, Swimming etc.)'),
    ('computer', 'Computer, Coding & Robotics'),
    ('science_quiz', 'Science, Math & Quiz'),
    (SKILL_OTHERS, 'Others'),
]

SIBLING_CLASS_NAMES = [
    'Play',
    'Nursery',
    'KG',
    'Class 1',
    'Class 2',
    'Class 3',
    'Class 4',
    'Class 5',
    'Class 6',
    'Class 7',
    'Class 8',
    'Class 9',
    'Class 10',
    'Class XI',
    'Class XII',
]
