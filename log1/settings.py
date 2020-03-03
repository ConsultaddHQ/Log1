import os
import logging.config
from dotenv import load_dotenv
from collections import OrderedDict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = 't=@n6ke#$-zmg*q!vy+mc25b2%sp+n%6tc%j0z#^p+j!e5e%$1'

# Reading env file
project_folder = os.path.expanduser(BASE_DIR)
load_dotenv(os.path.join(project_folder, '.env'))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', False)

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
    'notification',
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
    'report.apps.ReportConfig'
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
if os.environ.get('ENV') == 'prod' or os.environ.get('ENV') == 'dev':
    AWS_DEFAULT_ACL = None
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    AWS_LOCATION = 'media'

    PUBLIC_MEDIA_LOCATION = 'media'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{PUBLIC_MEDIA_LOCATION}/'
    DEFAULT_FILE_STORAGE = 'utils_app.storage.PublicMediaStorage'
else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')

MODELS_PATH = os.path.join(BASE_DIR, 'models')

# Password Reset Token Expiry Time
RESET_TOKEN_EXPIRY_TIME = 1

# Logger Configuration
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
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'file'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'file',
            'maxBytes': 1024 * 1024 * 2,
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
    ('LEGAL', ('legal@consultadd.com', 'Legal team email id')),
    ('FINANCE', ('finance@consultadd.com', 'Finance team email id')),
    ('RELATIONS', ('relations@consultadd.com', 'Relations team email id')),
    ('RECRUITMENT', ('recruitment@consultadd.com', 'recruitment team email id')),
    ('ENGINEERING', ('engineering@consultadd.com', 'Engineering team email id')),
    ('SUPERADMIN', ('sudeep.b@consultadd.com', "Sudeep's email id")),
    ('offer_url', ('https://mm.consultadd.com/hooks/oypapdoozfyf8csu3n88abegfe', "MatterMost")),
    ('offer_failure', ('https://mm.consultadd.com/hooks/n1j5juob5ffnfj93kehbzapeih', "MatterMost")),
    ('announcement_url', ('https://mm.consultadd.com/hooks/696csrwmgifhbmzywr88jch71w', "MatterMost")),
    ('recruitment_url', ('https://mm.consultadd.com/hooks/t8tradc9gffuxngymzhhgyj3pa', "MatterMost")),
    ('pool_channel_url', ('https://mm.consultadd.com/hooks/sfhgeyr9gf8qde9hcq1ba561mh', "MatterMost")),
    ('loud_speakers_url', ('https://mm.consultadd.com/hooks/qsi5qnbznfnabpnk5c8fbjfgph', "MatterMost")),
])

CONSTANCE_CONFIG_FIELDSETS = {
    'Email Ids': ('LEGAL', 'FINANCE', 'RELATIONS', 'RECRUITMENT', 'ENGINEERING', 'SUPERADMIN'),
    'Web Hooks': ('offer_url', 'offer_failure', 'announcement_url', 'recruitment_url', 'pool_channel_url', 'loud_speakers_url'),
}
