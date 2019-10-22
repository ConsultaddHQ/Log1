import os
import logging.config
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = 't=@n6ke#$-zmg*q!vy+mc25b2%sp+n%6tc%j0z#^p+j!e5e%$1'

# Reading env file
project_folder = os.path.expanduser(BASE_DIR)
load_dotenv(os.path.join(project_folder, '.env'))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG')

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

    'explorer',
    'corsheaders',
    'notifications',
    'rest_framework_swagger',

]

PROJECT_APPS = [
    'api_key',
    'utils_app',
    'employee',
    'attachment',
    'consultant',
    'marketing',
    'project',
    'jd_parser',
    # 'reports',
    'activity',
    'ckiller',
    'notification_utils',
]

INSTALLED_APPS = INSTALLED_APPS + THIRD_PARTY_APPS + PROJECT_APPS

AUTH_USER_MODEL = 'employee.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'qinspect.middleware.QueryInspectMiddleware',
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


# Database Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': 'localhost',
        'PORT': '5432',
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

# django-cors-header Configuration
CORS_ORIGIN_ALLOW_ALL = True

# Send Grid Configuration
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', None)

EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'apikey'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_HOST_PASSWORD = SENDGRID_API_KEY
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

DEFAULT_FROM_EMAIL = "Log1@consultadd.com"

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

# Media files (Documents)
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
        },
        'qinspect': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
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

# Query Inspector behaviour

# Whether the Query Inspector should do anything (default: False)
QUERY_INSPECT_ENABLED = True
# Whether to log the stats via Django logging (default: True)
QUERY_INSPECT_LOG_STATS = True
# Whether to add stats headers (default: True)
QUERY_INSPECT_HEADER_STATS = True
# Whether to log duplicate queries (default: False)
QUERY_INSPECT_LOG_QUERIES = True
# Whether to log queries that are above an absolute limit (default: None - disabled)
QUERY_INSPECT_ABSOLUTE_LIMIT = 100  # in milliseconds
# Whether to log queries that are more than X standard deviations above the mean query time (default: None - disabled)
QUERY_INSPECT_STANDARD_DEVIATION_LIMIT = 2
# Whether to include tracebacks in the logs (default: False)
QUERY_INSPECT_LOG_TRACEBACKS = True
# Project root (a list of directories, see below - default empty)
QUERY_INSPECT_TRACEBACK_ROOTS = [BASE_DIR]
# Minimum number of duplicates needed to log the query (default: 2)
QUERY_INSPECT_DUPLICATE_MIN = 1  # to force logging of all queries
# Whether to truncate SQL queries in logs to specified size, for readability purposes
# (default: None - full SQL query is included)
QUERY_INSPECT_SQL_LOG_LIMIT = 120  # limit to 120 chars
