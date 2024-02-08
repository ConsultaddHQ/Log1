import os
import logging.config
from collections import OrderedDict

from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = 't=@n6ke#$-zmg*q!vy+mc25b2%sp+n%6tc%j0z#^p+j!e5e%$1'

env_path = Path(BASE_DIR, '.env')
load_dotenv(dotenv_path=env_path)

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
    'engineering.apps.EngineeringConfig',
    'dashboard.apps.DashboardConfig',
    'tracking.apps.TrackingConfig',
    'finance.apps.FinanceConfig',
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
    'log1.middleware.AddressLogMiddleware',
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
            'libraries': {
                'staticfiles': 'django.templatetags.static',
            }
        },
    },
]

WSGI_APPLICATION = 'log1.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get('DB_NAME', ''),
        'USER': os.environ.get('DB_USER', ''),
        'PORT': os.environ.get('DB_PORT', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication'
    )
}

# django-cors-header Configuration
CORS_ORIGIN_ALLOW_ALL = True

CORS_ALLOW_HEADERS = [
    'uuid',
    'accept',
    'origin',
    'user-agent',
    'x-csrftoken',
    'content-type',
    'authorization',
    'accept-encoding',
    'x-requested-with',
    'X-Id-Token',
]

# Swagger
SWAGGER_SETTINGS = {
    "exclude_namespaces": [],
    "api_version": '2.0',
    "api_path": "/",
    "enabled_methods": [
        'get',
        'post',
        'put',
        'delete'
    ],
    'SECURITY_DEFINITIONS': {
        "apiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "Token Authentication"
        }
    },

    "api_key": '',
    "is_superuser": False,
    'USE_SESSION_AUTH': True,
    "is_authenticated": True,
}

# Send Grid Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_PORT = os.environ.get('EMAIL_PORT', 587)
EMAIL_HOST = os.environ.get('EMAIL_HOST', None)
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', None)
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', None)

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
AWS_REGION_NAME = os.environ.get('AWS_REGION_NAME')
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
AWS_S3_CUSTOM_DOMAIN = f'%s.s3.{AWS_REGION_NAME}.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_LOCATION = 'media'

PUBLIC_MEDIA_LOCATION = 'media'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{PUBLIC_MEDIA_LOCATION}/'
DEFAULT_FILE_STORAGE = 'utils_app.storage.PublicMediaStorage'

# Password Reset Token Expiry Time
RESET_TOKEN_EXPIRY_TIME = 1

# Logger Configuration
LOGGING_CONFIG = None
## ----- logging integrations starts here ----- ##
logging_conf = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'file': {
            'format': '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
        },
        'address_format': {
            'format': '%(asctime)s %(levelname)-5s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'formatter': 'file',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'ERROR',
            'backupCount': 5,
            'encoding': 'utf8',
            'formatter': 'file',
            'maxBytes': 10485760,
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': f"{os.path.join(BASE_DIR, 'logs/error.log')}",
        },
        'access': {
            'level': 'INFO',
            'backupCount': 5,
            'encoding': 'utf8',
            'maxBytes': 10485760,
            'formatter': 'address_format',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/address.log'),
        },
    },
    'loggers': {
        '': {
            'level': 'ERROR',
            'handlers': ['console', 'file']
        },
        'address': {
            'level': 'INFO',
            'handlers': ['access']
        }
    }
}
logging.config.dictConfig(logging_conf)

# Celery settings
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL')
CELERYBEAT_SCHEDULER = os.environ.get('CELERYBEAT_SCHEDULER')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND')
BROKER_TRANSPORT_OPTIONS = os.environ.get('BROKER_TRANSPORT_OPTIONS')

# Notifications settings
NOTIFICATIONS_CHANNELS = {
    'websocket': 'notification_utils.channels.BroadCastWebSocketChannel'
}

# Constance Config
CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'

CONSTANCE_CONFIG = OrderedDict([
    ('VERSION', ('R2022.10.2', 'Version')),
    ('APP_VERSION', ('2.0.6', 'APP_Version')),
    ('APP_URL', ('https://app.log1.com/', 'Log1 URL')),
    ('IPHONE_APP_LINK', ('https://apps.apple.com/us/app/consultadd-time-track/id1498377728', 'Iphone App Link')),
    ('ANDROID_APP_LINK', ('https://play.google.com/store/apps/details?id=com.consultadd.consultant_timesheet_app',
                          'Android App Download Link')),
    ('SLACK_TOKEN', ('xoxb-3680421803520-3714045757607-z1nUh9vv8DifWmSOBNlgpMg5',
                          'SLACK TOKEN')),

    ('LEGAL', ('legal@consultadd.com', 'Legal team Email ID')),
    ('SUPERADMIN', ('sudeep.b@consultadd.com', 'Admin Email ID')),
    ('BOOKING_ADMIN', ('bbookingg@gmail.com', 'Booking Email ID')),
    ('FINANCE', ('finance@consultadd.com', 'Finance team Email ID')),
    ('APP_ADMIN', ('sarang.m@consultadd.com', 'Log1 App Admin Email ID')),
    ('RELATIONS', ('relations@consultadd.com', 'Relations team Email ID')),
    ('RECRUITMENT', ('recruitment@consultadd.com', 'recruitment team Email ID')),
    ('ENGINEERING', ('engineering@consultadd.com', 'Engineering team Email ID')),
    ('TIMESHEET_APP_ADMIN', ('aditi.so@consultadd.com', 'Timesheet Admin Email ID')),
    ('VENDOR_MANAGEMENT', ('vendormanagement@consultadd.com', 'Vendor Management Email ID')),

    ('general_url', ('URL', 'General Channel')),
    ('test_team_url', ('URL', 'Test Team channel')),
    ('products_dev', ('URL', 'Products Dev Channel')),
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
    ('candidate_feedback_url', ('URL', 'Candidate Feedback Channel')),
    ('new_recruit_on_bench', ('URL', 'New Recruit On Bench Channel')),
    ('pre_joining_feedback_url', ('URL', 'Pre Joining Feedback Channel')),

    ('slack_general_url', ('URL', 'Slack General Channel')),
    ('slack_test_team_url', ('URL', 'Slack Test Team channel')),
    ('slack_products_dev', ('URL', 'Slack Products Dev Channel')),
    ('slack_engineering_url', ('URL', 'Slack Engineering channel')),
    ('slack_recruitment_url', ('URL', 'Slack Recruitment Channel')),
    ('slack_pool_channel_url', ('URL', 'Slack 45dayslimit Channel')),
    ('slack_offer_url', ('URL', 'Slack Offer Announcement Channel')),
    ('slack_loud_speakers_url', ('URL', 'Slack Loudspeaker Channel')),
    ('slack_announcement_url', ('URL', 'Slack Announcement Channel')),
    ('slack_marketing_report_url', ('URL', 'Slack Marketing Report')),
    ('slack_joined_url', ('URL', 'Slack Joining Announcement Channel')),
    ('slack_offer_failure_url', ('URL', 'Slack Offer Failure Channel')),
    ('slack_interview_feedback_url', ('URL', 'Slack Interview Feedback')),
    ('slack_exit_interview_url', ('URL', 'Slack Exit Interview Channel')),
    ('slack_engineering_private_url', ('URL', 'Slack Engineering Private')),
    ('slack_project_termination_url', ('URL', 'Slack Project Terminations')),
    ('slack_candidate_feedback_url', ('URL', 'Slack Candidate Feedback Channel')),
    ('slack_new_recruit_on_bench', ('URL', 'Slack New Recruit On Bench Channel')),
    ('slack_pre_joining_feedback_url', ('URL', 'Slack Pre Joining Feedback Channel')),
    ('slack_consultadd_compete_url', ('URL', 'Slack Consultadd Compete Channel')),
    ('slack_test_channel_url', ('URL', 'Slack Test Channel')),
    ('OKR_URL', ('https://dlwngz4tmfcbh.cloudfront.net/login', 'OKR URL')),
])

CONSTANCE_CONFIG_FIELDSETS = {
    'constants': (
        'APP_URL', 'ANDROID_APP_LINK', 'IPHONE_APP_LINK', 'VERSION', 'APP_VERSION', 'OKR_URL', 'SLACK_TOKEN'
    ),
    'Email Ids': (
        'APP_ADMIN', 'LEGAL', 'FINANCE', 'RELATIONS', 'RECRUITMENT', 'ENGINEERING', 'SUPERADMIN', 'BOOKING_ADMIN',
        'VENDOR_MANAGEMENT', 'TIMESHEET_APP_ADMIN'
    ),
    'Web-Hooks': (
        'engineering_url', 'test_team_url', 'offer_url', 'announcement_url', 'recruitment_url',
        'pool_channel_url', 'exit_interview_url', 'interview_feedback_url', 'project_termination_url',
        'loud_speakers_url', 'joined_url', 'marketing_report_url', 'general_url', 'offer_failure_url',
        'products_dev', 'new_recruit_on_bench', 'pre_joining_feedback_url', 'candidate_feedback_url',
        'slack_engineering_url', 'slack_test_team_url', 'slack_offer_url', 'slack_announcement_url',
        'slack_interview_feedback_url', 'slack_project_termination_url', 'slack_loud_speakers_url',
        'slack_joined_url', 'slack_marketing_report_url', 'slack_general_url', 'slack_offer_failure_url',
        'slack_products_dev', 'slack_new_recruit_on_bench', 'slack_pre_joining_feedback_url',
        'slack_recruitment_url', 'slack_pool_channel_url', 'slack_exit_interview_url', 'slack_candidate_feedback_url',
        'slack_engineering_private_url', 'slack_consultadd_compete_url', 'slack_test_channel_url'
    ),
}
