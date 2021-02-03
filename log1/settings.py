import os
import logging.config
from collections import OrderedDict

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = 't=@n6ke#$-zmg*q!vy+mc25b2%sp+n%6tc%j0z#^p+j!e5e%$1'

# Reading env file
PROJECT_FOLDER = os.path.expanduser(BASE_DIR)
load_dotenv(os.path.join(PROJECT_FOLDER, '.env'))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False
if os.environ.get('DEBUG', False) == 'True':
    DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'storages',
    'explorer',
    'constance',
    'corsheaders',
    'import_export',
    'rest_framework_swagger',
    'constance.backends.database',
]

PROJECT_APPS = [
    'api_key.apps.ApiKeyConfig',
    'utils_app.apps.UtilsAppConfig',
    'employee.apps.EmployeeConfig',
    'attachment.apps.AttachmentConfig',
    'consultant.apps.ConsultantConfig',
    'marketing.apps.MarketingConfig',
    'project.apps.ProjectConfig',
    'jd_parser.apps.JdParserConfig',
    'activity.apps.ActivityConfig',
    'ckiller.apps.CkillerConfig',
    'report.apps.ReportConfig',
    'legal.apps.LegalConfig',
    'notification.apps.NotificationConfig',
    'impersonate.apps.ImpersonateConfig',
    'messaging.apps.MessagingConfig',
]

INSTALLED_APPS = INSTALLED_APPS + THIRD_PARTY_APPS + PROJECT_APPS

AUTH_USER_MODEL = 'employee.User'

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'log1.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'log1.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get('DB_NAME', ''),
        'USER': os.environ.get('DB_USER', ''),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'consultadd'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

REST_FRAMEWORK = {'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema'}

# django-cors-header Configuration
CORS_ORIGIN_ALLOW_ALL = True

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'uuid',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Send Grid Configuration

EMAIL_USE_TLS = True
EMAIL_PORT = os.environ.get('EMAIL_PORT', 587)
EMAIL_HOST = os.environ.get('EMAIL_HOST', None)
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', None)
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_API_KEY', None)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'consultadd.com')

# Internationalization
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Django Explorer Setup
EXPLORER_CONNECTIONS = {'Default': 'default'}
EXPLORER_DEFAULT_CONNECTION = 'default'

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')

# Media files Storage location (Documents)
AWS_DEFAULT_ACL = None
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_LOCATION = 'media'

PUBLIC_MEDIA_LOCATION = 'media'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{PUBLIC_MEDIA_LOCATION}/'
DEFAULT_FILE_STORAGE = 'utils_app.storage.PublicMediaStorage'

MODELS_PATH = os.path.join(BASE_DIR, 'models')

# Password Reset Token Expiry Time
RESET_TOKEN_EXPIRY_TIME = 1

# Logger Configuration
LOGGING_CONFIG = None
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'file': {
            'format': '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'file',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'level': 'DEBUG',
'encoding': 'utf8',
'backupCount': 20,
            'maxBytes': 10485760,
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'file',
            'filename': os.path.join(BASE_DIR, 'logs/debug.log')
        }
    },
    'loggers': {
        'file': {
            'level': 'DEBUG',
            'handlers': ['console']
        }
    }
})

# Celery settings
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600}  # 1 hour.
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_TASK_ALWAYS_EAGER = False

# Notifications settings
NOTIFICATIONS_CHANNELS = {
    'websocket': 'notification_utils.channels.BroadCastWebSocketChannel'
}

# Constance Config

CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'

CONSTANCE_CONFIG = OrderedDict([
    ('APP_URL', ('https://app.log1.com/', 'Log1 URL')),
    ('IPHONE_APP_LINK', ('https://apps.apple.com/us/app/consultadd-time-track/id1498377728', 'Iphone App Link')),
    ('ANDROID_APP_LINK', ('https://play.google.com/store/apps/details?id=com.consultadd.consultant_timesheet_app',
                          'Android App Download Link')),

    ('LEGAL', ('legal@consultadd.com', 'Legal team email id')),
    ('SUPERADMIN', ('sudeep.b@consultadd.com', 'Admin email id')),
    ('BOOKING_ADMIN', ('bbookingg@gmail.com', 'Booking Email id')),
    ('FINANCE', ('finance@consultadd.com', 'Finance team email id')),
    ('RELATIONS', ('relations@consultadd.com', 'Relations team email id')),
    ('RECRUITMENT', ('recruitment@consultadd.com', 'recruitment team email id')),
    ('ENGINEERING', ('engineering@consultadd.com', 'Engineering team email id')),
    ('VENDOR_MANAGEMENT', ('vendormanagement@consultadd.com', 'Vendor Management email id')),

    ('general_url', ('URL', 'General Channel')),
    ('test_team_url', ('URL', 'Test Team channel')),
    ('engineering_url', ('URL', 'Engineering channel')),
    ('recruitment_url', ('URL', 'Recruitment Channel')),
    ('pool_channel_url', ('URL', '45dayslimit Channel')),
    ('offer_url', ('URL', 'Offer Announcement Channel')),
    ('loud_speakers_url', ('URL', 'Loudspeaker Channel')),
    ('announcement_url', ('URL', 'Announcement Channel')),
    ('marketing_report_url', ('URL', 'Marketing Report')),
    ('joined_url', ('URL', 'Joining Announcement Channel')),
    ('offer_failure_url', ('URL', 'Offer Failure Channel')),
    ('interview_feedback_url', ('URL', 'Interview Feedback')),
    ('exit_interview_url', ('URL', 'Exit Interview Channel')),
    ('project_termination_url', ('URL', 'Project Terminations')),
])

CONSTANCE_CONFIG_FIELDSETS = {
    'constants': ('APP_URL', 'ANDROID_APP_LINK', 'IPHONE_APP_LINK'),
    'Email Ids': ('LEGAL', 'FINANCE', 'RELATIONS', 'RECRUITMENT', 'ENGINEERING', 'SUPERADMIN', 'BOOKING_ADMIN',
                  'VENDOR_MANAGEMENT'),
    'Web-Hooks': ('engineering_url', 'test_team_url', 'offer_url', 'announcement_url', 'recruitment_url',
                  'pool_channel_url', 'exit_interview_url', 'interview_feedback_url', 'project_termination_url',
                  'loud_speakers_url', 'joined_url', 'marketing_report_url', 'general_url', 'offer_failure_url'),
}
